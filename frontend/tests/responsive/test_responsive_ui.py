
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

PAGES = [
    "index.html",
    "event-details.html",
    "student-dashboard.html",
    "create-event.html",
    "admin-dashboard.html",
    "participants.html",
    "notification-history.html",
    "profile.html",
    "login.html",
    "register.html",
    "forgot-password.html",
    "reset-password.html",
]

VIEWPORTS = [
    (320, 568),
    (375, 812),
    (425, 900),
    (768, 1024),
    (1024, 768),
    (1366, 768),
    (1920, 1080),
]

NAVIGATION_PAGES = [
    "index.html",
    "event-details.html",
    "student-dashboard.html",
    "create-event.html",
    "notification-history.html",
    "participants.html",
    "profile.html",
    "register.html",
]

PROTECTED_PAGES = {
    "student-dashboard.html",
    "notification-history.html",
}

def open_page(browser, frontend_url, page):
    if page in PROTECTED_PAGES:
        browser.get(f"{frontend_url}/login.html")

        browser.execute_script(
            "sessionStorage.setItem('access_token', 'responsive-test-token');"
        )

        browser.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    const originalFetch = window.fetch.bind(window);

                    window.fetch = async function(input, init) {
                        const url = typeof input === "string"
                            ? input
                            : input.url;

                        const headers = {
                            "Content-Type": "application/json"
                        };

                        if (url.includes("/auth/me")) {
                            return new Response(
                                JSON.stringify({
                                    id: 1,
                                    full_name: "Responsive Test",
                                    email: "test@uap-bd.edu",
                                    role: "student"
                                }),
                                { status: 200, headers }
                            );
                        }

                        if (url.includes("/registrations/me")) {
                            return new Response(
                                "[]",
                                { status: 200, headers }
                            );
                        }

                        if (url.includes("/notifications")) {
                            return new Response(
                                "[]",
                                { status: 200, headers }
                            );
                        }

                        return originalFetch(input, init);
                    };
                """
            },
        )

    browser.get(f"{frontend_url}/{page}")

@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_page_has_no_horizontal_overflow(
    browser, frontend_url, page, width, height
):
    browser.set_window_size(width, height)
    open_page(browser, frontend_url, page)

    WebDriverWait(browser, 10).until(
        lambda driver: driver.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    dimensions = browser.execute_script("""
        return {
            viewport: document.documentElement.clientWidth,
            document: document.documentElement.scrollWidth,
            body: document.body.scrollWidth
        };
    """)

    has_overflow = (
        dimensions["document"] > dimensions["viewport"] + 1
        or dimensions["body"] > dimensions["viewport"] + 1
    )

    if has_overflow:
        screenshot_dir = Path(__file__).parent / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        screenshot_name = f"{Path(page).stem}_{width}x{height}.png"
        browser.save_screenshot(str(screenshot_dir / screenshot_name))

    assert not has_overflow, (
        f"Horizontal overflow on {page} at {width}x{height}. "
        f"Dimensions: {dimensions}"
    )

@pytest.mark.parametrize("page", NAVIGATION_PAGES)
def test_mobile_navigation_markup(browser, frontend_url, page):
    browser.set_window_size(375, 812)
    open_page(browser, frontend_url, page)

    toggler = WebDriverWait(browser, 10).until(
        lambda driver: driver.find_element(
            By.CSS_SELECTOR, "button.navbar-toggler"
        )
    )

    target_selector = toggler.get_attribute("data-bs-target")
    assert target_selector, f"Missing data-bs-target on {page}"

    target = browser.find_element(By.CSS_SELECTOR, target_selector)

    assert target.get_attribute("id")
    assert toggler.get_attribute("data-bs-toggle") == "collapse"
    assert toggler.get_attribute("aria-label")

@pytest.mark.parametrize("page", NAVIGATION_PAGES)
def test_mobile_navigation_toggle(browser, frontend_url, page):
    browser.set_window_size(375, 812)
    open_page(browser, frontend_url, page)

    WebDriverWait(browser, 10).until(
        lambda driver: driver.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    bootstrap_loaded = browser.execute_script("""
        return typeof window.bootstrap !== "undefined"
            && typeof window.bootstrap.Collapse !== "undefined";
    """)

    if not bootstrap_loaded:
        pytest.skip("Bootstrap JavaScript did not load in Chrome.")

    toggler = browser.find_element(
        By.CSS_SELECTOR, "button.navbar-toggler"
    )

    target = browser.find_element(
        By.CSS_SELECTOR, toggler.get_attribute("data-bs-target")
    )

    toggler.click()

    WebDriverWait(browser, 10).until(
        lambda driver: (
            "show" in target.get_attribute("class").split()
            and toggler.get_attribute("aria-expanded") == "true"
        )
    )

    toggler.click()

    WebDriverWait(browser, 10).until(
        lambda driver: (
            "show" not in target.get_attribute("class").split()
            and toggler.get_attribute("aria-expanded") == "false"
        )
    )

@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_responsive_screenshot_evidence(
    browser, frontend_url, page, width, height
):
    browser.set_window_size(width, height)
    open_page(browser, frontend_url, page)

    WebDriverWait(browser, 10).until(
        lambda driver: driver.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    category = (
        "mobile" if width <= 425
        else "tablet" if width <= 1024
        else "desktop"
    )

    evidence_dir = (
        Path(__file__).parents[1]
        / "test_evidence"
        / category
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{Path(page).stem}_{width}x{height}.png"
    browser.save_screenshot(str(evidence_dir / filename))

@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_visible_controls_and_images_fit_viewport(
    browser, frontend_url, page, width, height
):
    browser.set_window_size(width, height)
    open_page(browser, frontend_url, page)

    WebDriverWait(browser, 10).until(
        lambda driver: driver.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    outside = browser.execute_script("""
        const selectors = [
            "button", "a", "input", "select", "textarea", "img"
        ];
        const problems = [];

        document.querySelectorAll(selectors.join(",")).forEach(el => {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();

            if (
                style.display === "none" ||
                style.visibility === "hidden" ||
                rect.width === 0 ||
                rect.height === 0
            ) return;

            if (rect.left < -1 || rect.right > window.innerWidth + 1) {
                problems.push({
                    element: el.tagName,
                    text: (el.innerText || el.alt || "").slice(0, 50),
                    left: Math.round(rect.left),
                    right: Math.round(rect.right)
                });
            }
        });

        return problems;
    """)

    assert not outside, (
        f"Visible controls/images outside viewport on {page} "
        f"at {width}x{height}: {outside}"
    )

@pytest.mark.parametrize("page", PAGES)
def test_visible_form_fields_accept_input(browser, frontend_url, page):
    open_page(browser, frontend_url, page)

    fields = browser.find_elements(
        By.CSS_SELECTOR,
        "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]):not([type=file]):not([type=reset]), textarea"
    )

    tested = 0
    for field in fields:
        if not field.is_displayed() or not field.is_enabled():
            continue
        if field.get_attribute("readonly"):
            continue

        field_type = (field.get_attribute("type") or "text").lower()
        value = "123" if field_type == "number" else "ResponsiveTest"

        field.clear()
        field.send_keys(value)
        assert field.get_attribute("value") == value
        tested += 1

    if tested == 0:
        pytest.skip(f"No editable visible text fields on {page}")

@pytest.mark.parametrize("page", PAGES)
def test_page_scrolling(browser, frontend_url, page):
    open_page(browser, frontend_url, page)

    browser.execute_script(
        "window.scrollTo(0, document.body.scrollHeight);"
    )
    browser.execute_script("window.scrollTo(0, 0);")

    assert abs(browser.execute_script("return window.scrollY")) <= 5

@pytest.mark.parametrize("page", PAGES)
def test_bootstrap_dropdown_and_modal_controls(
    browser, frontend_url, page
):
    open_page(browser, frontend_url, page)

    loaded = browser.execute_script("""
        return typeof bootstrap !== "undefined"
            && !!bootstrap.Dropdown
            && !!bootstrap.Modal;
    """)
    if not loaded:
        pytest.skip("Bootstrap JavaScript is unavailable")

    dropdowns = browser.find_elements(
        By.CSS_SELECTOR, '[data-bs-toggle="dropdown"]'
    )
    modals = browser.find_elements(
        By.CSS_SELECTOR, '[data-bs-toggle="modal"]'
    )

    tested = 0

    for dropdown in dropdowns:
        if not dropdown.is_displayed() or not dropdown.is_enabled():
            continue

        dropdown.click()
        menu = browser.find_element(
            By.CSS_SELECTOR,
            dropdown.get_attribute("aria-expanded") == "true"
            and ".dropdown-menu.show"
            or ".dropdown-menu"
        )
        assert menu.is_displayed()
        dropdown.click()
        tested += 1

    for trigger in modals:
        if not trigger.is_displayed() or not trigger.is_enabled():
            continue

        target = trigger.get_attribute("data-bs-target")
        if not target:
            continue

        trigger.click()
        modal = browser.find_element(By.CSS_SELECTOR, target)

        WebDriverWait(browser, 5).until(
            lambda driver: "show" in modal.get_attribute("class").split()
        )

        browser.execute_script("""
            const instance = bootstrap.Modal.getInstance(arguments[0]);
            if (instance) instance.hide();
        """, modal)

        WebDriverWait(browser, 5).until(
            lambda driver: "show" not in modal.get_attribute("class").split()
        )
        tested += 1

    if tested == 0:
        pytest.skip(f"No visible Bootstrap dropdown/modal controls on {page}")
