
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FRONTEND_URL = "http://127.0.0.1:5500"
EVENT_TITLE = "Selenium Test Event"


def open_homepage(driver):
    driver.get(f"{FRONTEND_URL}/index.html")


def search_event(driver, search_text):
    search_input = driver.find_element(By.ID, "eventSearchInput")
    search_input.clear()
    search_input.send_keys(search_text)
    driver.find_element(By.ID, "eventSearchSubmit").click()


def login_as_test_student(driver):
    driver.get(FRONTEND_URL)
    driver.execute_script(
        "sessionStorage.setItem('access_token', 'selenium-test-token');"
    )


def test_homepage_displays_upcoming_event(driver):
    open_homepage(driver)

    event_title = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, ".event-card-title")
        )
    )

    assert event_title.text == EVENT_TITLE


def test_event_search_returns_matching_event(driver):
    open_homepage(driver)
    search_event(driver, "Selenium")

    summary = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.ID, "eventSearchSummary")
        )
    )

    assert "1 upcoming event" in summary.text

    event_title = driver.find_element(
        By.CSS_SELECTOR, ".event-card-title"
    )

    assert event_title.text == EVENT_TITLE


def test_event_search_shows_empty_state(driver):
    open_homepage(driver)
    search_event(driver, "NoMatchingEvent")

    empty_message = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.ID, "eventSearchEmpty")
        )
    )

    assert empty_message.is_displayed()

    assert len(
        driver.find_elements(By.CSS_SELECTOR, ".event-card")
    ) == 0


def test_event_details_page_loads(driver):
    login_as_test_student(driver)

    driver.get(f"{FRONTEND_URL}/event-details.html?id=1")

    event_title = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.ID, "detailTitle")
        )
    )

    assert event_title.text == EVENT_TITLE

    assert driver.find_element(
        By.ID, "eventDetails"
    ).is_displayed()


def test_student_can_register_for_event(driver):
    login_as_test_student(driver)

    driver.get(f"{FRONTEND_URL}/event-details.html?id=1")

    register_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.ID, "registerForEvent")
        )
    )

    register_button.click()

    registration_message = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.ID, "registrationMessage")
        )
    )

    assert "Registered" in registration_message.text
