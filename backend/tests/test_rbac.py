from asyncio import run

import pytest
from fastapi import HTTPException

from app.dependencies.auth import require_role
from app.models.role import Role
from app.models.user import User


def make_user(role_name="student", active=True):
    user = User(
        id=1,
        name="Test User",
        email="12345678@uap-bd.edu",
        password_hash="test-hash",
        role_id=1,
        is_active=active,
    )

    if role_name is not None:
        user.role = Role(id=1, name=role_name)

    return user


def test_organizer_role_is_allowed():
    user = make_user("organizer")
    result = run(require_role("organizer")(current_user=user))
    assert result is user


def test_administrator_role_is_allowed():
    user = make_user("administrator")
    result = run(require_role("administrator")(current_user=user))
    assert result is user


def test_student_is_forbidden_from_organizer_access():
    with pytest.raises(HTTPException) as error:
        run(require_role("organizer")(current_user=make_user("student")))

    assert error.value.status_code == 403


def test_user_without_role_is_forbidden():
    with pytest.raises(HTTPException) as error:
        run(require_role("organizer")(current_user=make_user(None)))

    assert error.value.status_code == 403


def test_inactive_user_is_forbidden():
    with pytest.raises(HTTPException) as error:
        run(require_role("organizer")(current_user=make_user("organizer", active=False)))

    assert error.value.status_code == 403
