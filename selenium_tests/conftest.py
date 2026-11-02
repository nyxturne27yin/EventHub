
import json
import os
import tempfile
import threading
from datetime import date, datetime, time, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class MockAPIHandler(BaseHTTPRequestHandler):

    def send_json(self, status_code, data):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization"
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization"
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        self.end_headers()

    def get_test_event(self, detailed=False):
        event = {
            "id": 1,
            "title": "Selenium Test Event",
            "description": "A test event for EventHub UI testing.",
            "category": "Technology",
            "event_date": (date.today() + timedelta(days=30)).isoformat(),
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "mode": "Offline",
            "venue": "UAP Campus",
            "capacity": 100,
            "registered_count": 10,
            "status": "published",
            "organization_name": "CSE Department",
            "department": "Computer Science"
        }

        if detailed:
            event["registration_deadline"] = (
                datetime.combine(
                    date.today() + timedelta(days=20),
                    time.min
                ).isoformat()
            )

        return event

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/auth/me":
            self.send_json(200, {
                "id": 1,
                "name": "Selenium Test Student",
                "email": "12345678@uap-bd.edu",
                "role": "student"
            })

        elif path == "/events/":
            event = self.get_test_event()
            search = parse_qs(
                urlparse(self.path).query
            ).get("search", [""])[0]

            if search and search.lower() not in event["title"].lower():
                self.send_json(200, [])
            else:
                self.send_json(200, [event])

        elif path == "/events/1":
            self.send_json(200, self.get_test_event(detailed=True))

        elif path == "/registrations/me":
            self.send_json(200, [])

        else:
            self.send_json(404, {"detail": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        path = urlparse(self.path).path

        if path == "/auth/login":
            valid_login = (
                payload.get("email") == "12345678@uap-bd.edu"
                and payload.get("password") == "StrongPass123!"
            )

            if valid_login:
                self.send_json(200, {
                    "access_token": "selenium-test-token",
                    "token_type": "bearer"
                })
            else:
                self.send_json(401, {
                    "detail": "Invalid email or password"
                })

        elif path == "/auth/register":
            self.send_json(201, {
                "id": 999,
                "full_name": payload.get("full_name"),
                "email": payload.get("email")
            })

        elif path == "/events/1/registrations":
            self.send_json(201, {
                "id": 1001,
                "event_id": 1,
                "student_id": 1,
                "status": "Registered"
            })

        else:
            self.send_json(404, {"detail": "Not found"})

    def log_message(self, format_string, *args):
        pass


@pytest.fixture(scope="session")
def local_servers():
    try:
        api_server = ThreadingHTTPServer(
            ("127.0.0.1", 8000),
            MockAPIHandler
        )
    except OSError as exc:
        raise RuntimeError(
            "Port 8000 is already in use. Stop the FastAPI backend "
            "before running Selenium tests."
        ) from exc

    api_thread = threading.Thread(
        target=api_server.serve_forever,
        daemon=True
    )
    api_thread.start()

    yield

    api_server.shutdown()
    api_server.server_close()
    api_thread.join(timeout=5)


@pytest.fixture
def driver(local_servers):
    chrome_path = (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )

    if not os.path.exists(chrome_path):
        raise RuntimeError("Google Chrome was not found.")

    with tempfile.TemporaryDirectory(
        prefix="eventhub-chrome-"
    ) as profile_dir:

        options = Options()
        options.binary_location = chrome_path

        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1365,900")
        options.add_argument(f"--user-data-dir={profile_dir}")

        browser = webdriver.Chrome(options=options)

        try:
            yield browser
        finally:
            browser.quit()
