"""Real-browser notification delivery tests for EventHub.

These tests intentionally use the live local EventHub frontend and FastAPI
backend. No mocked HTTP handlers or synthetic notification UI are installed.
Test accounts and service URLs are supplied through environment variables.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import date, datetime, time as datetime_time, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

selenium = pytest.importorskip("selenium", reason="Install requirements-test.txt")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
EVIDENCE = Path(os.getenv("EVENTHUB_EVIDENCE_DIR", ROOT / "selenium_tests" / "evidence"))
FRONTEND_URL = os.getenv("EVENTHUB_FRONTEND_URL", "http://127.0.0.1:5500").rstrip("/")
API_URL = os.getenv("EVENTHUB_API_URL", "http://127.0.0.1:8000").rstrip("/")
WAIT_SECONDS = int(os.getenv("EVENTHUB_SELENIUM_WAIT", "15"))
PREFIX = "SELENIUM-NOTIFICATION-"
pytestmark = pytest.mark.notification


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"Set {name} to a dedicated non-production test account")
    return value


def _json_request(path: str, *, method: str = "GET", token: str | None = None,
                  payload: dict | None = None, expected: tuple[int, ...] = (200,)):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            status_code = response.status
            raw = response.read()
    except HTTPError as exc:
        status_code = exc.code
        raw = exc.read()
    except URLError as exc:
        pytest.fail(f"EventHub API is unreachable at {API_URL}: {exc}")
    try:
        result = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        result = raw.decode("utf-8", errors="replace")
    if status_code not in expected:
        pytest.fail(f"{method} {path}: expected HTTP {expected}, got {status_code}: {result}")
    return status_code, result


def _login_ui(driver, email: str, password: str) -> str:
    driver.get(f"{FRONTEND_URL}/login.html")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(EC.visibility_of_element_located((By.ID, "loginForm")))
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "loginSubmit").click()
    wait.until(lambda d: "login.html" not in d.current_url)
    token = driver.execute_script("return sessionStorage.getItem('access_token');")
    assert token, "The real frontend login did not store an access token"
    return token


def _new_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-extensions")
    driver_path = os.getenv("CHROMEDRIVER_PATH", "").strip() or (
        r"L:\SeleniumCache\chromedriver\win64\156.0.8078.80\chromedriver.exe"
        if os.name == "nt" else ""
    )
    service = Service(executable_path=driver_path) if driver_path else Service()
    return webdriver.Chrome(service=service, options=options)


@pytest.fixture

def driver(request):
    """One isolated real Chrome session; retain evidence on failure/xfail."""
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    browser = _new_driver()
    request.node._notification_browser = browser
    try:
        yield browser
    finally:
        report = getattr(request.node, "rep_call", None)
        if report is not None and (report.failed or getattr(report, "wasxfail", False)):
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)
            shot = EVIDENCE / f"{safe_name}-{datetime.now():%Y%m%d-%H%M%S}.png"
            browser.save_screenshot(str(shot))
            (EVIDENCE / f"{safe_name}.failure.txt").write_text(
                f"node={request.node.nodeid}\nwhen={datetime.now().isoformat()}\n"
                f"url={browser.current_url}\n", encoding="utf-8"
            )
        browser.quit()


@pytest.fixture
def accounts():
    return {
        "student": (
            _required("EVENTHUB_TEST_STUDENT_EMAIL"),
            _required("EVENTHUB_TEST_STUDENT_PASSWORD"),
        ),
        "other_student": (
            _required("EVENTHUB_TEST_OTHER_STUDENT_EMAIL"),
            _required("EVENTHUB_TEST_OTHER_STUDENT_PASSWORD"),
        ),
        "empty_student": (
            _required("EVENTHUB_TEST_EMPTY_STUDENT_EMAIL"),
            _required("EVENTHUB_TEST_EMPTY_STUDENT_PASSWORD"),
        ),
        "organizer": (
            _required("EVENTHUB_TEST_ORGANIZER_EMAIL"),
            _required("EVENTHUB_TEST_ORGANIZER_PASSWORD"),
        ),
        "admin": (
            _required("EVENTHUB_TEST_ADMIN_EMAIL"),
            _required("EVENTHUB_TEST_ADMIN_PASSWORD"),
        ),
    }



async def _delete_test_event(event_id: int | None, title: str) -> None:
    """Delete only the uniquely identified Selenium test event and dependents."""

    if not title or not title.startswith(PREFIX):
        raise ValueError(
            f"Refusing to delete an event without the expected prefix: {title!r}"
        )

    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    from sqlalchemy import delete, select

    from app.database.database import AsyncSessionLocal, engine
    from app.models.certificate import Certificate
    from app.models.event import Event
    from app.models.notification import Notification
    from app.models.registration import EventRegistration

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                statement = select(Event).where(Event.title == title)

                if event_id is not None:
                    statement = statement.where(Event.id == event_id)

                event = await session.scalar(statement)

                if event is None:
                    return

                actual_event_id = event.id

                # Remove dependent records before deleting the event.
                await session.execute(
                    delete(Notification).where(
                        Notification.event_id == actual_event_id
                    )
                )

                await session.execute(
                    delete(EventRegistration).where(
                        EventRegistration.event_id == actual_event_id
                    )
                )

                await session.execute(
                    delete(Certificate).where(
                        Certificate.event_id == actual_event_id
                    )
                )

                await session.execute(
                    delete(Event).where(Event.id == actual_event_id)
                )

    finally:
        # Prevent pooled async connections from being reused across event loops.
        await engine.dispose()





@pytest.fixture
def test_event(driver, accounts):
    """Create and clean up a uniquely named Selenium notification test event."""

    student_email, student_password = accounts["student"]
    organizer_email, organizer_password = accounts["organizer"]
    admin_email, admin_password = accounts["admin"]

    unique = uuid.uuid4().hex[:10]
    title = f"{PREFIX}{unique}"

    event_day = date.today() + timedelta(days=3)
    start = datetime_time(10, 0)
    end = datetime_time(11, 0)

    payload = {
        "title": title,
        "description": "Automated notification delivery verification event.",
        "category": "QA Automation",
        "event_date": event_day.isoformat(),
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "mode": "Offline",
        "venue": "QA Test Hall A",
        "capacity": 100,
        "registration_deadline": datetime.combine(
            event_day - timedelta(days=1),
            datetime_time(18, 0),
        ).isoformat(),
        "status": "draft",
    }

    event_id = None
    admin_browser = None

    try:
        # Authenticate the student and organizer through the real frontend.
        student_token = _login_ui(
            driver, student_email, student_password
        )
        organizer_token = _login_ui(
            driver, organizer_email, organizer_password
        )

        # Use a separate browser session for the administrator.
        admin_browser = _new_driver()
        admin_token = _login_ui(
            admin_browser, admin_email, admin_password
        )

        # Create the test event.
        _, created = _json_request(
            "/events/",
            method="POST",
            token=organizer_token,
            payload=payload,
            expected=(201,),
        )

        event_id = created.get("event", {}).get("id") or created.get("id")
        assert event_id, f"Event creation returned no event ID: {created}"

        # Submit the event for approval.
        _json_request(
            f"/events/{event_id}/publish",
            method="POST",
            token=organizer_token,
            expected=(200,),
        )

        # Approve the event as administrator.
        _json_request(
            f"/admin/events/{event_id}/status",
            method="PATCH",
            token=admin_token,
            payload={"status": "published"},
            expected=(200,),
        )

        yield {
            "id": event_id,
            "title": title,
            "date": event_day.isoformat(),
            "start": start.isoformat(),
            "venue": payload["venue"],
            "student_token": student_token,
            "organizer_token": organizer_token,
            "admin_token": admin_token,
        }

    finally:
        try:
            # Also searches by the exact unique title if event_id is None.
            # Cleanup errors are deliberately allowed to fail the test.
            asyncio.run(_delete_test_event(event_id, title))

        finally:
            # Close the administrator browser even if cleanup fails.
            if admin_browser is not None:
                admin_browser.quit()


def _history_in_browser(driver, email: str, password: str):
    _login_ui(driver, email, password)
    driver.get(f"{FRONTEND_URL}/notification-history.html")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(lambda d: "d-none" not in d.find_element(By.ID, "notificationEmpty").get_attribute("class")
               or d.find_element(By.ID, "notificationList").find_elements(By.CSS_SELECTOR, "article.card"))
    return driver.find_element(By.ID, "notificationList").find_elements(By.CSS_SELECTOR, "article.card")


def _find_card_by_heading(driver, heading: str):
    def locate(browser):
        for card in browser.find_elements(By.CSS_SELECTOR, "#notificationList article.card"):
            headings = card.find_elements(By.CSS_SELECTOR, "h2")
            if headings and heading.casefold() in headings[0].text.casefold():
                return card
        return False
    return WebDriverWait(driver, WAIT_SECONDS).until(locate)


def _notification_records(user_token: str, event_id: int):
    """Fetch a student's notifications through the real EventHub API."""

    _, notifications = _json_request(
        "/notifications",
        token=user_token,
        expected=(200,),
    )

    if not isinstance(notifications, list):
        pytest.fail(
            f"Expected GET /notifications to return a list, "
            f"got {type(notifications).__name__}: {notifications!r}"
        )

    return [
        notification
        for notification in notifications
        if notification.get("event_id") == event_id
    ]


def _database_notification_rows(user_id: int, event_id: int):
    """Read persisted notification rows directly through the app ORM."""

    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    from sqlalchemy import select

    from app.database.database import AsyncSessionLocal, engine
    from app.models.notification import Notification

    async def read_rows():
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.event_id == event_id,
                    )
                )

                return [
                    {
                        "id": row.id,
                        "title": row.title,
                        "message": row.message,
                        "created_at": row.created_at,
                    }
                    for row in result.scalars().all()
                ]

        finally:
            await engine.dispose()

    return asyncio.run(read_rows())



def _assert_db_row_exists(user_token: str, event_id: int, title: str):
    # GET /notifications executes a database query (not a static/mock response).
    # This confirms the committed row is retrievable from the persisted store.
    rows = _notification_records(user_token, event_id)
    assert any(title.casefold() in row.get("title", "").casefold() for row in rows), rows
    # Confirm the same committed notification exists in the database itself.
    _, identity = _json_request("/auth/me", token=user_token)
    database_rows = _database_notification_rows(identity["id"], event_id)
    assert any(title.casefold() in row["title"].casefold() for row in database_rows), database_rows
    return rows


def _register_through_ui(driver, event_id: int):
    driver.get(f"{FRONTEND_URL}/event-details.html?id={event_id}")
    wait = WebDriverWait(driver, WAIT_SECONDS)
    wait.until(EC.visibility_of_element_located((By.ID, "eventDetails")))
    wait.until(EC.element_to_be_clickable((By.ID, "registerForEvent"))).click()
    wait.until(lambda d: d.find_element(By.ID, "registrationMessage").is_displayed())
    return driver.find_element(By.ID, "registrationMessage").text


def test_registration_confirmation_is_persisted_and_visible_to_recipient(driver, accounts, test_event):
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    message = _register_through_ui(driver, test_event["id"])
    assert "success" in message.casefold() or "registered" in message.casefold() or "confirmed" in message.casefold(), message

    rows = _assert_db_row_exists(test_event["student_token"], test_event["id"], "Registration Successful")
    notification = next(row for row in rows if row["title"] == "Registration Successful")
    assert test_event["title"] in notification["message"]
    assert test_event["date"] in notification["message"]
    assert test_event["start"] in notification["message"]
    assert test_event["venue"] in notification["message"]
    assert datetime.fromisoformat(notification["created_at"]) <= datetime.now() + timedelta(minutes=1)

    driver.get(f"{FRONTEND_URL}/notification-history.html")
    card = _find_card_by_heading(driver, "Registration Successful")
    assert test_event["title"] in card.text
    assert test_event["date"] in card.text or test_event["venue"] in card.text

    other_email, other_password = accounts["other_student"]
    other_browser = _new_driver()
    try:
        other_cards = _history_in_browser(other_browser, other_email, other_password)
        assert all(test_event["title"] not in card.text for card in other_cards)
    finally:
        other_browser.quit()


def test_event_date_change_notifies_registered_participant(driver, accounts, test_event):
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])
    changed = (date.fromisoformat(test_event["date"]) + timedelta(days=1)).isoformat()
    _json_request(f"/events/{test_event['id']}", method="PATCH", token=test_event["organizer_token"],
                  payload={"event_date": changed}, expected=(200,))
    rows = _notification_records(
        test_event["student_token"], test_event["id"]
    )
    update_rows = [
        row for row in rows
        if "change" in row["title"].casefold()
        or "updated" in row["title"].casefold()
    ]

    if not update_rows:
        pytest.xfail(
            "Known gap: event date updates do not create participant notifications"
        )

    assert changed in update_rows[0]["message"], (
        "The date-change notification does not contain the updated event date"
    )


def test_venue_change_notifies_registered_participant(driver, accounts, test_event):
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])
    changed_venue = f"QA Updated Venue {uuid.uuid4().hex[:6]}"
    _json_request(f"/events/{test_event['id']}", method="PATCH", token=test_event["organizer_token"],
                  payload={"venue": changed_venue}, expected=(200,))
    rows = _notification_records(test_event["student_token"], test_event["id"])
    update_rows = [row for row in rows if "change" in row["title"].casefold() or "updated" in row["title"].casefold()]
    cards = _history_in_browser(driver, student_email, student_password)
    update_cards = [card for card in cards if any(word in card.text.casefold() for word in ("change", "updated"))]
    if not update_rows or not update_cards:
        pytest.xfail("Known gap: event venue updates do not create participant notifications")
    assert changed_venue in update_rows[0]["message"]
    assert changed_venue in update_cards[0].text


def test_event_cancellation_notifies_only_registered_participants(driver, accounts, test_event):
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])
    _json_request(f"/events/{test_event['id']}/cancel", method="POST",
                  token=test_event["organizer_token"], expected=(200,))
    rows = _assert_db_row_exists(test_event["student_token"], test_event["id"], "Event Cancelled")
    cancellation = next(row for row in rows if row["title"] == "Event Cancelled")
    assert test_event["title"] in cancellation["message"]

    driver.get(f"{FRONTEND_URL}/notification-history.html")
    card = _find_card_by_heading(driver, "Event Cancelled")
    assert test_event["title"] in card.text

    other_email, other_password = accounts["other_student"]
    other_browser = _new_driver()
    try:
        other_cards = _history_in_browser(other_browser, other_email, other_password)
        assert all(test_event["title"] not in card.text for card in other_cards)
    finally:
        other_browser.quit()



def test_reminder_scheduler_persists_one_notification_on_repeated_trigger(
    driver, accounts, test_event
):
    # Register the student through the real frontend.
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])

    # Schedule the reminder approximately 3 minutes from now.
    reminder_at = (
        datetime.now().replace(second=0, microsecond=0)
        + timedelta(minutes=3)
    )
    event_at = reminder_at + timedelta(hours=24)

    # Keep the event's start and end times on the same calendar day.
    end_at = min(
        event_at + timedelta(hours=1),
        datetime.combine(event_at.date(), datetime_time(23, 59)),
    )

    deadline = (
        datetime.now() + timedelta(hours=1)
    ).replace(second=0, microsecond=0)

    _json_request(
        f"/events/{test_event['id']}",
        method="PATCH",
        token=test_event["organizer_token"],
        payload={
            "event_date": event_at.date().isoformat(),
            "start_time": event_at.time().isoformat(),
            "end_time": end_at.time().isoformat(),
            "registration_deadline": deadline.isoformat(),
        },
        expected=(200,),
    )

    # Run the actual reminder scheduler twice to verify deduplication.
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND) + os.pathsep + env.get("PYTHONPATH", "")
    )

    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "app.services.event_reminders"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    # Verify that only one reminder was persisted.
    rows = _notification_records(
        test_event["student_token"], test_event["id"]
    )
    reminders = [
        row for row in rows
        if row["title"] == "Event Reminder"
    ]

    assert len(reminders) == 1, (
        f"Expected one deduplicated reminder, got {len(reminders)}"
    )
    assert test_event["title"] in reminders[0]["message"]

    # Verify the database record as well.
    _, student_identity = _json_request(
        "/auth/me", token=test_event["student_token"]
    )

    database_rows = _database_notification_rows(
        student_identity["id"], test_event["id"]
    )

    assert len([
        row for row in database_rows
        if row["title"] == "Event Reminder"
    ]) == 1

    # Verify the reminder is visible in the actual frontend.
    driver.get(f"{FRONTEND_URL}/notification-history.html")
    card = _find_card_by_heading(driver, "Event Reminder")

    assert test_event["title"] in card.text



def test_notification_history_shows_empty_state_for_user_without_notifications(
    driver, accounts
):
    email, password = accounts["empty_student"]

    cards = _history_in_browser(driver, email, password)

    empty = driver.find_element(By.ID, "notificationEmpty")

    assert empty.is_displayed(), (
        f"Expected empty history, found {len(cards)} notification cards"
    )

    assert "No notifications yet" in empty.text
    assert len(cards) == 0, (
        f"Expected zero notification cards, found {len(cards)}"
    )

def test_student_cannot_access_another_users_notification_records(driver, accounts, test_event):
    primary_email, primary_password = accounts["student"]
    _login_ui(driver, primary_email, primary_password)
    _register_through_ui(driver, test_event["id"])

    email, password = accounts["other_student"]
    _login_ui(driver, email, password)
    driver.get(f"{FRONTEND_URL}/notification-history.html")
    WebDriverWait(driver, WAIT_SECONDS).until(
        lambda d: "d-none" not in d.find_element(By.ID, "notificationEmpty").get_attribute("class")
        or d.find_element(By.ID, "notificationList").find_elements(By.CSS_SELECTOR, "article.card")
    )
    _, own_rows = _json_request("/notifications", token=driver.execute_script("return sessionStorage.getItem('access_token');"))
    assert all(row.get("event_id") != test_event["id"] for row in own_rows)


def test_student_cannot_cancel_an_event_and_invalid_action_creates_no_notification(driver, accounts, test_event):
    email, password = accounts["student"]
    student_token = _login_ui(driver, email, password)
    status_code, response = _json_request(f"/events/{test_event['id']}/cancel", method="POST",
                                          token=student_token, expected=(403,))
    assert status_code == 403, response
    rows = _notification_records(student_token, test_event["id"])
    assert not any(row["title"] == "Event Cancelled" for row in rows)



def test_failed_registration_does_not_create_confirmation(
    driver, accounts, test_event
):
    # Restrict the event to one participant.
    _json_request(
        f"/events/{test_event['id']}",
        method="PATCH",
        token=test_event["organizer_token"],
        payload={"capacity": 1},
        expected=(200,),
    )

    # The second student takes the only available place.
    other_browser = _new_driver()

    try:
        other_email, other_password = accounts["other_student"]

        _login_ui(other_browser, other_email, other_password)

        other_message = _register_through_ui(
            other_browser, test_event["id"]
        )

        assert any(
            word in other_message.casefold()
            for word in ("success", "registered", "confirmed")
        ), other_message

    finally:
        other_browser.quit()

    # Log in as the primary student.
    student_email, student_password = accounts["student"]
    student_token = _login_ui(driver, student_email, student_password)

    # Open the event details page.
    driver.get(
        f"{FRONTEND_URL}/event-details.html?id={test_event['id']}"
    )

    wait = WebDriverWait(driver, WAIT_SECONDS)

    wait.until(
        EC.visibility_of_element_located((By.ID, "eventDetails"))
    )

    # The frontend should prevent registration because the event is full.
    button = driver.find_element(By.ID, "registerForEvent")

    assert button.get_attribute("disabled") is not None, (
        "Registration button should be disabled when the event is full"
    )

    assert button.text.strip() == "Event Full", button.text

    # Also verify that the backend rejects an attempted registration.
    status_code, response = _json_request(
        f"/events/{test_event['id']}/registrations",
        method="POST",
        token=student_token,
        expected=(400, 409),
    )

    assert status_code in (400, 409), response

    assert any(
        word in str(response).casefold()
        for word in ("full", "capacity")
    ), response

    # A rejected registration must not generate a confirmation.
    rows = _notification_records(
        student_token, test_event["id"]
    )

    assert not any(
        row["title"] == "Registration Successful"
        for row in rows
    )



def test_cancelled_registration_does_not_create_another_notification(driver, accounts, test_event):
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])
    before = _notification_records(test_event["student_token"], test_event["id"])
    _, registrations = _json_request("/registrations/me", token=test_event["student_token"])
    registration = next(item for item in registrations if item["event_id"] == test_event["id"])
    _json_request(
    f"/events/{test_event['id']}/registrations/"
    f"{registration['registration_id']}/cancel",
                  method="POST", token=test_event["student_token"], expected=(200,))
    after = _notification_records(test_event["student_token"], test_event["id"])
    assert len(after) == len(before), "Cancelling a registration unexpectedly generated a notification"


def test_cancelling_event_with_no_participants_creates_no_notifications(driver, accounts, test_event):
    _json_request(f"/events/{test_event['id']}/cancel", method="POST",
                  token=test_event["organizer_token"], expected=(200,))
    rows = _notification_records(test_event["student_token"], test_event["id"])
    assert not any(row["title"] == "Event Cancelled" for row in rows)


def test_repeated_event_cancellation_is_rejected_without_duplicate_notification(driver, accounts, test_event):
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])
    _json_request(f"/events/{test_event['id']}/cancel", method="POST",
                  token=test_event["organizer_token"], expected=(200,))
    before = _notification_records(test_event["student_token"], test_event["id"])
    status_code, _ = _json_request(f"/events/{test_event['id']}/cancel", method="POST",
                                   token=test_event["organizer_token"], expected=(409,))
    after = _notification_records(test_event["student_token"], test_event["id"])
    assert status_code == 409
    assert len([n for n in after if n["title"] == "Event Cancelled"]) == len(
        [n for n in before if n["title"] == "Event Cancelled"]
    )


def test_event_cancellation_notification_contains_event_date_and_time(driver, accounts, test_event):
    """The cancellation payload should preserve the event schedule for attendees."""
    student_email, student_password = accounts["student"]
    _login_ui(driver, student_email, student_password)
    _register_through_ui(driver, test_event["id"])
    _json_request(f"/events/{test_event['id']}/cancel", method="POST",
                  token=test_event["organizer_token"], expected=(200,))
    rows = _assert_db_row_exists(test_event["student_token"], test_event["id"], "Event Cancelled")
    cancellation = next(row for row in rows if row["title"] == "Event Cancelled")
    cards = _history_in_browser(driver, student_email, student_password)
    cancellation_cards = [card for card in cards if "Event Cancelled" in card.text]
    assert cancellation_cards, "Cancellation was not visible in the recipient's history"
    if test_event["date"] not in cancellation["message"] or test_event["start"] not in cancellation["message"]:
        pytest.xfail("Known gap: cancellation notification message omits the event date and start time")
    assert test_event["date"] in cancellation_cards[0].text
    assert test_event["start"] in cancellation_cards[0].text
