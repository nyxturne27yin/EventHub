from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


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

def test_invalid_login_shows_error(browser, frontend_server):
    browser.get(f"{frontend_server}/login.html")

    browser.execute_script("""
        window.fetch = async () => ({
            ok: false,
            json: async () => ({ detail: "Invalid email or password" })
        });
""")

    browser.find_element(By.ID, "email").send_keys("student@uap-bd.edu")
    browser.find_element(By.ID, "password").send_keys("wrongpassword")
    browser.execute_script("arguments[0].requestSubmit()", browser.find_element(By.ID, "loginForm"))

    error = browser.find_element(By.ID, "loginError")

    assert error.text == "Invalid email or password"
    assert "d-none" not in error.get_attribute("class")


def test_successful_login_redirects_to_profile(browser, frontend_server):
    browser.get(f"{frontend_server}/login.html")

    browser.execute_script("""
        window.fetch = async () => ({
            ok: true,
            json: async () => ({ access_token: "mock-access-token" })
        });
""")

    browser.find_element(By.ID, "email").send_keys("student@uap-bd.edu")
    browser.find_element(By.ID, "password").send_keys("correctpassword")

    browser.execute_script(
        "arguments[0].requestSubmit()",
        browser.find_element(By.ID, "loginForm"),
    )

    WebDriverWait(browser, 10).until(
        lambda driver: driver.current_url.endswith("/profile.html")
    )

    assert browser.execute_script(
        "return sessionStorage.getItem('access_token')"
    ) == "mock-access-token"


def test_student_cannot_access_create_event_page(browser, frontend_server):
    browser.get(f"{frontend_server}/login.html")
    browser.execute_script(
        "sessionStorage.setItem('access_token', 'mock-token')"
    )

    browser.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                window.fetch = async (url) => {
                    if (String(url).endsWith("/auth/me")) {
                        return {
                            ok: true,
                            json: async () => ({role: "student"})
                        };
                    }
                    return {
                        ok: false,
                        json: async () => ({detail: "Unexpected request"})
                    };
                };
            """
        },
    )

    browser.get(f"{frontend_server}/create-event.html")

    message = WebDriverWait(browser, 10).until(
        lambda driver: driver.find_element(By.ID, "pageMessage")
        if "d-none" not in driver.find_element(
            By.ID, "pageMessage"
        ).get_attribute("class")
        else False
    )

    assert "Access denied" in message.text
    assert "d-none" in browser.find_element(
        By.ID, "createEventForm"
    ).get_attribute("class")


def test_organizer_can_create_event(browser, frontend_server):
    browser.get(f"{frontend_server}/login.html")
    browser.execute_script(
        "sessionStorage.setItem('access_token', 'mock-token')"
    )

    browser.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                window.fetch = async (url, options = {}) => {
                    const requestUrl = String(url);

                    if (requestUrl.endsWith("/auth/me")) {
                        return {
                            ok: true,
                            json: async () => ({role: "organizer"})
                        };
                    }

                    if (
                        requestUrl.endsWith("/events/") &&
                        options.method === "POST"
                    ) {
                        window.createdEventPayload = JSON.parse(options.body);
                        return {
                            ok: true,
                            json: async () => ({event: {id: 123}})
                        };
                    }

                    return {
                        ok: false,
                        json: async () => ({detail: "Unexpected request"})
                    };
                };
            """
        },
    )

    browser.get(f"{frontend_server}/create-event.html")

    WebDriverWait(browser, 10).until(
        lambda driver: "d-none" not in driver.find_element(
            By.ID, "createEventForm"
        ).get_attribute("class")
    )

    browser.find_element(By.ID, "title").send_keys("Selenium Test Event")
    browser.find_element(By.ID, "description").send_keys(
        "Event created during Selenium testing."
    )
    browser.find_element(By.ID, "category").send_keys("Workshop")
    browser.find_element(By.ID, "event_date").send_keys("12312030")
    browser.find_element(By.ID, "start_time").send_keys("1000AM")
    browser.find_element(By.ID, "end_time").send_keys("1100AM")
    browser.find_element(By.ID, "capacity").send_keys("50")
    browser.find_element(By.ID, "venue").send_keys("UAP Campus")
    browser.execute_script("""
        const deadline = document.getElementById('registration_deadline');
        deadline.value = '2030-12-30T10:00';
        deadline.dispatchEvent(new Event('input', {bubbles: true}));
        deadline.dispatchEvent(new Event('change', {bubbles: true}));
    """)

    browser.find_element(By.ID, "createEventForm").submit()


    message = WebDriverWait(browser, 10).until(
        lambda driver: driver.find_element(By.ID, "pageMessage")
        if "Event created successfully" in driver.find_element(
            By.ID, "pageMessage"
        ).text
        else False
    )

    assert "Event created successfully" in message.text
    assert browser.execute_script(
        "return window.createdEventPayload.title"
    ) == "Selenium Test Event"


def test_student_cannot_access_admin_dashboard(browser, frontend_server):
    browser.get(f"{frontend_server}/login.html")
    browser.execute_script(
        "sessionStorage.setItem('access_token', 'mock-token')"
    )

    browser.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                window.fetch = async () => ({
                    ok: true,
                    json: async () => ({role: "student"})
                });
            """
        },
    )

    browser.get(f"{frontend_server}/admin-dashboard.html")

    message = WebDriverWait(browser, 10).until(
        lambda driver: driver.find_element(By.ID, "pageMessage")
        if "d-none" not in driver.find_element(
            By.ID, "pageMessage"
        ).get_attribute("class")
        else False
    )

    assert "Access denied" in message.text
    assert "d-none" in browser.find_element(
        By.ID, "dashboardContent"
    ).get_attribute("class")


def test_auth_form_fields_have_associated_labels(browser, frontend_server):
    for page in ["login.html", "register.html"]:
        browser.get(f"{frontend_server}/{page}")

        unlabeled_fields = browser.execute_script("""
            return Array.from(document.querySelectorAll(
                "form input:not([type='hidden']), form select, form textarea"
            )).filter(field => {
                return !field.labels || field.labels.length === 0;
            }).map(field => field.id || field.name);
        """)

        assert unlabeled_fields == [], (
            f"Unlabeled fields on {page}: {unlabeled_fields}"
        )


def test_auth_buttons_have_accessible_names(browser, frontend_server):
    for page in ["login.html", "register.html"]:
        browser.get(f"{frontend_server}/{page}")

        unnamed_buttons = browser.execute_script("""
            return Array.from(document.querySelectorAll("button"))
                .filter(button =>
                    !button.innerText.trim() &&
                    !button.getAttribute("aria-label") &&
                    !button.getAttribute("aria-labelledby")
                ).length;
        """)

        assert unnamed_buttons == 0


def test_auth_navigation_has_accessible_name(browser, frontend_server):
    for page in ["login.html", "register.html"]:
        browser.get(f"{frontend_server}/{page}")

        navigation = browser.find_element(By.TAG_NAME, "nav")

        assert (
            navigation.get_attribute("aria-label")
            or navigation.get_attribute("aria-labelledby")
        )


def test_auth_error_messages_are_announced(browser, frontend_server):
    for page, error_id in [
        ("login.html", "loginError"),
        ("register.html", "registrationError"),
    ]:
        browser.get(f"{frontend_server}/{page}")

        error = browser.find_element(By.ID, error_id)

        assert error.get_attribute("role") == "alert"
        assert error.get_attribute("aria-live") == "polite"


def test_registration_password_toggle_supports_keyboard(
    browser, frontend_server
):
    from selenium.webdriver.common.keys import Keys

    browser.get(f"{frontend_server}/register.html")

    password = browser.find_element(By.ID, "password")
    toggle = browser.find_element(
        By.CSS_SELECTOR, '[data-toggle-password="password"]'
    )

    toggle.send_keys(Keys.SPACE)

    assert password.get_attribute("type") == "text"
    assert toggle.get_attribute("aria-pressed") == "true"
    assert toggle.get_attribute("aria-label") == "Hide password"


def test_auth_pages_have_one_main_heading(browser, frontend_server):
    for page in ["login.html", "register.html"]:
        browser.get(f"{frontend_server}/{page}")

        assert len(browser.find_elements(By.TAG_NAME, "h1")) == 1


def test_auth_pages_fit_mobile_viewport(browser, frontend_server):
    browser.set_window_size(375, 812)

    for page in ["login.html", "register.html"]:
        browser.get(f"{frontend_server}/{page}")

        has_horizontal_overflow = browser.execute_script("""
            return document.documentElement.scrollWidth >
                   document.documentElement.clientWidth;
        """)

        assert has_horizontal_overflow is False, (
            f"Horizontal overflow found on {page}"
        )
