
# EventHub Notification Delivery Tests (Selenium)

These tests use real Chrome WebDriver sessions against the running EventHub frontend and FastAPI backend. They do not use the mock API handler in the existing authentication Selenium fixture.

The test module provides its own isolated `driver` fixture and uses API calls for controlled test setup, organizer/admin actions that do not have a frontend edit control, and supplementary persisted-data checks.

## Requirements

- Python virtual environment with `requirements-test.txt` installed.
- Chrome/Chromium and a compatible ChromeDriver.
- PostgreSQL running with the EventHub schema migrated.
- EventHub frontend and backend running locally.
- Five dedicated, non-production test accounts:
  - One student.
  - One additional student.
  - One organizer.
  - One administrator.
  - One student with zero notifications for the empty-history test.

The tests do not create accounts or alter role assignments. Do not point them at production.

The organizer account must own newly created test events, and the administrator account must be able to approve them.

Test events use a unique `SELENIUM-NOTIFICATION-` prefix and are deleted with their registrations and notifications during fixture cleanup.

## PowerShell Setup

Run from the repository root.

### 1. Start the backend

In the first terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --app-dir backend --reload
```

### 2. Start the frontend

In the second terminal:

```powershell
python -m http.server 5500 --directory frontend
```

### 3. Configure Selenium

In a third terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt

New-Item -ItemType Directory -Force .\selenium_tests\evidence | Out-Null

$env:EVENTHUB_FRONTEND_URL = "http://127.0.0.1:5500"
$env:EVENTHUB_API_URL = "http://127.0.0.1:8000"

$env:EVENTHUB_TEST_STUDENT_EMAIL = "<dedicated-student-email>"
$env:EVENTHUB_TEST_STUDENT_PASSWORD = "<dedicated-student-password>"

$env:EVENTHUB_TEST_OTHER_STUDENT_EMAIL = "<additional-student-email>"
$env:EVENTHUB_TEST_OTHER_STUDENT_PASSWORD = "<additional-student-password>"

$env:EVENTHUB_TEST_EMPTY_STUDENT_EMAIL = "<empty-history-student-email>"
$env:EVENTHUB_TEST_EMPTY_STUDENT_PASSWORD = "<empty-history-student-password>"

$env:EVENTHUB_TEST_ORGANIZER_EMAIL = "<dedicated-organizer-email>"
$env:EVENTHUB_TEST_ORGANIZER_PASSWORD = "<dedicated-organizer-password>"

$env:EVENTHUB_TEST_ADMIN_EMAIL = "<dedicated-admin-email>"
$env:EVENTHUB_TEST_ADMIN_PASSWORD = "<dedicated-admin-password>"

$env:CHROMEDRIVER_PATH = "L:\SeleniumCache\chromedriver\win64\156.0.8078.80\chromedriver.exe"
```

Use actual dedicated test-account credentials in your local terminal. Never put real or production credentials in source files.

The empty-history student must have zero notifications before the test runs.

`CHROMEDRIVER_PATH` is optional when Selenium Manager can locate or download a compatible driver. On machines without network access, point it to the local ChromeDriver executable compatible with the installed Chrome version.

### 4. Run the notification tests

```powershell
python -m pytest selenium_tests/test_notification_delivery.py -v -ra `
  --junitxml=selenium_tests/evidence/notification-results.xml
```

## Coverage

- Student registration through `event-details.html`, confirmation notification, event/date/venue content, notification history, and recipient isolation.
- Date and venue updates for registered participants. These are expected to report **XFAIL** until the backend emits update notifications.
- Cancellation notification content. This is expected to report **XFAIL** until the message includes the cancelled event's date and start time.
- Event cancellation notification delivery and unrelated-user isolation.
- Actual reminder scheduler invocation twice, with a near-due event, checking that only one reminder is stored and rendered in the browser.
- Full-capacity registration failure, cancelled-registration behavior, no-participant cancellation, repeated cancellation, empty history, and unauthorized cancellation attempts.
- Direct ORM readback for registration and cancellation notifications, in addition to browser-visible history/API readback.

## Evidence and Results

Screenshots and a small failure-context file are written to `selenium_tests/evidence/` for failed and expected-failure browser tests.

The JUnit XML report records test names, outcomes, and assertion/failure messages. The terminal `-ra` summary reports passed, failed, skipped, and expected-failure tests.

The evidence directory is excluded from Git through `.gitignore`.

## Current Known Product Gaps

The existing `PATCH /events/{event_id}` endpoint updates event data but does not create notifications for registered participants when `event_date`, `start_time`, or `venue` changes.

The date and venue delivery tests therefore report **XFAIL** until this separate application feature is implemented.

The cancellation notification currently omits the event date and start time. Its content test also reports **XFAIL** until that behavior is implemented.

This QA change does not modify application notification behavior.
