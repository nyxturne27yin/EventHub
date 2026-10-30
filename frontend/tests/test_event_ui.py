from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


FRONTEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def frontend_server():
    handler = partial(
        SimpleHTTPRequestHandler,
        directory=str(FRONTEND_DIR),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}"

    server.shutdown()
    thread.join()
    server.server_close()


@pytest.fixture
def browser():
    options = Options()
    options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def test_login_page_loads(browser, frontend_server):
    browser.get(f"{frontend_server}/login.html")

    assert browser.find_element(By.ID, "loginForm")
    assert browser.find_element(By.ID, "email")
    assert browser.find_element(By.ID, "password")
    assert browser.find_element(By.ID, "loginSubmit")


def test_create_event_page_loads(browser, frontend_server):
    browser.get(f"{frontend_server}/create-event.html")

    assert browser.find_element(By.ID, "createEventForm")
    assert browser.find_element(By.ID, "title")
    assert browser.find_element(By.ID, "event_date")
    assert browser.find_element(By.ID, "mode")
    assert browser.find_element(By.ID, "capacity")


def test_create_event_form_requires_mandatory_fields(
    browser,
    frontend_server,
):
    browser.get(f"{frontend_server}/create-event.html")

    form = browser.find_element(By.ID, "createEventForm")

    browser.execute_script(
        "arguments[0].classList.remove('d-none')",
        form,
    )

    is_valid = browser.execute_script(
        "return arguments[0].checkValidity()",
        form,
    )

    assert is_valid is False


def test_event_details_page_loads(browser, frontend_server):
    browser.get(f"{frontend_server}/event-details.html?id=101")

    assert browser.find_element(By.ID, "eventDetails")
    assert browser.find_element(By.ID, "registerForEvent")
    assert browser.find_element(By.ID, "registrationMessage")
