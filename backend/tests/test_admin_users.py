from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.role import Role
from app.models.user import User


class FakeScalars:
    def __init__(self, users):
        self.users = users

    def all(self):
        return self.users


class FakeResult:
    def __init__(self, users):
        self.users = users

    def scalars(self):
        return FakeScalars(self.users)


class FakeDB:
    def __init__(self, users):
        self.users = users

    async def execute(self, statement):
        return FakeResult(self.users)


def make_user(user_id=1, role_name="administrator", active=True):
    user = User(
        id=user_id,
        name=f"Test User {user_id}",
        email=f"{user_id:08d}@uap-bd.edu",
        password_hash="test-secret-hash",
        role_id=3,
        is_active=active,
    )
    user.role = Role(id=3, name=role_name)
    return user


def make_client(users, role_name="administrator"):
    async def override_get_db():
        yield FakeDB(users)

    async def override_get_current_user():
        return make_user(role_name=role_name)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(app)


def test_administrator_can_list_users_without_exposing_password_hash():
    users = [
        make_user(1, "administrator"),
        make_user(2, "student", active=False),
    ]
    client = make_client(users)

    try:
        response = client.get("/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Test User 1"
        assert data[0]["email"] == "00000001@uap-bd.edu"
        assert data[0]["role"] == "administrator"
        assert data[0]["is_active"] is True
        assert "created_at" in data[0]
        assert "password_hash" not in data[0]
        assert "test-secret-hash" not in response.text
        assert data[1]["role"] == "student"
        assert data[1]["is_active"] is False
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_administrator_receives_empty_list_when_no_users_exist():
    client = make_client([])

    try:
        response = client.get("/admin/users")

        assert response.status_code == 200
        assert response.json() == []
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_student_cannot_list_users():
    client = make_client([], role_name="student")

    try:
        response = client.get("/admin/users")

        assert response.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_unauthenticated_user_cannot_list_users():
    async def override_get_db():
        yield FakeDB([])

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        response = client.get("/admin/users")

        assert response.status_code == 401
    finally:
        client.close()
        app.dependency_overrides.clear()


class MutationResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class MutationDB:
    def __init__(self, users, roles):
        self.users = users
        self.roles = roles
        self.commit_count = 0

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        params = statement.compile().params

        if entity is User:
            target_id = next(
                (value for key, value in params.items()
                 if key.startswith("id_")),
                None,
            )
            user = next(
                (item for item in self.users if item.id == target_id),
                None,
            )
            return MutationResult(user)

        if entity is Role:
            role_name = next(
                (value for key, value in params.items()
                 if key.startswith("name_")),
                None,
            )
            role = next(
                (item for item in self.roles if item.name == role_name),
                None,
            )
            return MutationResult(role)

        return MutationResult(None)

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, user):
        pass

def make_mutation_client(
    users,
    role_name="administrator",
):
    roles = [
        Role(id=1, name="student"),
        Role(id=2, name="organizer"),
        Role(id=3, name="administrator"),
    ]
    db = MutationDB(users, roles)

    async def override_get_db():
        yield db

    async def override_get_current_user():
        return make_user(role_name=role_name)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(app), db

def test_administrator_can_deactivate_active_user():
    admin = make_user(user_id=1, role_name="administrator")
    target = make_user(user_id=2, role_name="student", active=True)
    client, db = make_mutation_client([admin, target])

    try:
        response = client.patch(
            "/admin/users/2",
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
        assert target.is_active is False
        assert db.commit_count == 1
    finally:
        client.close()
        app.dependency_overrides.clear()

def test_administrator_can_reactivate_inactive_user():
    admin = make_user(user_id=1, role_name="administrator")
    target = make_user(user_id=2, role_name="student", active=False)
    client, db = make_mutation_client([admin, target])

    try:
        response = client.patch(
            "/admin/users/2",
            json={"is_active": True},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True
        assert target.is_active is True
        assert db.commit_count == 1
    finally:
        client.close()
        app.dependency_overrides.clear()

def test_student_cannot_change_user_activation_status():
    admin = make_user(user_id=1, role_name="administrator")
    target = make_user(user_id=2, role_name="student", active=True)
    client, db = make_mutation_client(
        [admin, target],
        role_name="student",
    )

    try:
        response = client.patch(
            "/admin/users/2",
            json={"is_active": False},
        )

        assert response.status_code == 403
        assert target.is_active is True
        assert db.commit_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()

def test_administrator_cannot_update_nonexistent_user():
    admin = make_user(user_id=1, role_name="administrator")
    client, db = make_mutation_client([admin])

    try:
        response = client.patch(
            "/admin/users/999",
            json={"is_active": False},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"
        assert db.commit_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()

def test_administrator_cannot_deactivate_own_account():
    admin = make_user(user_id=1, role_name="administrator")
    client, db = make_mutation_client([admin])

    try:
        response = client.patch(
            "/admin/users/1",
            json={"is_active": False},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "You cannot deactivate your own account."
        )
        assert admin.is_active is True
        assert db.commit_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_organizer_cannot_list_users():
    client = make_client([], role_name="organizer")

    try:
        response = client.get("/admin/users")

        assert response.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()
