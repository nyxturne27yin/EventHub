import json
import os
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


CHROMEDRIVER = (
    r"L:\SeleniumCache\chromedriver\win64"
    r"\156.0.8078.80\chromedriver.exe"
)

TEMP_DIR = r"L:\Temp\Selenium"


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
            "GET, POST, OPTIONS"
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
            "GET, POST, OPTIONS"
        )
        self.end_headers()

    def do_GET(self):
        if self.path == "/auth/me":
            self.send_json(200, {
                "id": 1,
                "name": "Selenium Test Student",
                "email": "12345678@uap-bd.edu",
                "role": "student"
            })
        else:
            self.send_json(404, {"detail": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")

        if self.path == "/auth/login":
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

        elif self.path == "/auth/register":
            self.send_json(201, {
                "id": 999,
                "full_name": payload.get("full_name"),
                "email": payload.get("email")
            })
        else:
            self.send_json(404, {"detail": "Not found"})

    def log_message(self, format_string, *args):
        pass


@pytest.fixture(scope="session")
def local_servers():
    # Reuse the existing frontend server on port 5500.
    # Start only the mock API server on port 8000.
    api_server = ThreadingHTTPServer(
        ("127.0.0.1", 8000),
        MockAPIHandler
    )

    api_thread = threading.Thread(
        target=api_server.serve_forever,
        daemon=True
    )
    api_thread.start()

    yield

    api_server.shutdown()
    api_server.server_close()


@pytest.fixture
def driver(local_servers):
    os.environ["TEMP"] = TEMP_DIR
    os.environ["TMP"] = TEMP_DIR

    profile_dir = tempfile.mkdtemp(
        prefix="eventhub-chrome-",
        dir=TEMP_DIR
    )

    cache_dir = os.path.join(profile_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1365,900")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument(f"--disk-cache-dir={cache_dir}")
    options.add_argument("--disk-cache-size=104857600")

    service = Service(executable_path=CHROMEDRIVER)
    browser = None

    try:
        browser = webdriver.Chrome(
            service=service,
            options=options
        )
        yield browser
    finally:
        if browser is not None:
            browser.quit()

        shutil.rmtree(profile_dir, ignore_errors=True)
