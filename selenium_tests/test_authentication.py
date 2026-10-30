from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FRONTEND_URL = "http://127.0.0.1:5500"

VALID_EMAIL = "12345678@uap-bd.edu"
VALID_PASSWORD = "StrongPass123!"


def open_login(driver):
    driver.get(f"{FRONTEND_URL}/login.html")


def open_registration(driver):
    driver.get(f"{FRONTEND_URL}/register.html")


def enter_text(driver, element_id, value):
    field = driver.find_element(By.ID, element_id)
    field.clear()
    field.send_keys(value)


def submit_registration(driver, name, email, password, confirmation):
    open_registration(driver)

    enter_text(driver, "fullName", name)
    enter_text(driver, "email", email)
    enter_text(driver, "password", password)
    enter_text(driver, "confirmPassword", confirmation)

    driver.find_element(By.ID, "registerSubmit").click()


def test_login_page_loads(driver):
    open_login(driver)

    assert driver.find_element(By.ID, "loginForm").is_displayed()
    assert driver.find_element(By.ID, "email").is_displayed()
    assert driver.find_element(By.ID, "password").is_displayed()


def test_login_password_visibility_toggle(driver):
    open_login(driver)

    password = driver.find_element(By.ID, "password")
    toggle = driver.find_element(By.ID, "togglePassword")

    assert password.get_attribute("type") == "password"

    toggle.click()

    assert password.get_attribute("type") == "text"
    assert toggle.get_attribute("aria-pressed") == "true"

    toggle.click()

    assert password.get_attribute("type") == "password"
    assert toggle.get_attribute("aria-pressed") == "false"


def test_login_with_invalid_credentials(driver):
    open_login(driver)

    enter_text(driver, "email", VALID_EMAIL)
    enter_text(driver, "password", "WrongPassword123!")

    driver.find_element(By.ID, "loginSubmit").click()

    error = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "loginError"))
    )

    assert "Invalid email or password" in error.text
    assert "login.html" in driver.current_url


def test_login_with_valid_credentials(driver):
    open_login(driver)

    enter_text(driver, "email", VALID_EMAIL)
    enter_text(driver, "password", VALID_PASSWORD)

    driver.find_element(By.ID, "loginSubmit").click()

    WebDriverWait(driver, 10).until(
        EC.url_contains("profile.html")
    )

    token = driver.execute_script(
        "return sessionStorage.getItem('access_token');"
    )

    assert token == "selenium-test-token"


def test_registration_rejects_invalid_uap_email(driver):
    submit_registration(
        driver,
        "Selenium Test Student",
        "invalid-email@example.com",
        VALID_PASSWORD,
        VALID_PASSWORD
    )

    error = driver.find_element(By.ID, "registrationError")

    assert error.is_displayed()
    assert "valid UAP email" in error.text


def test_registration_rejects_weak_password(driver):
    submit_registration(
        driver,
        "Selenium Test Student",
        VALID_EMAIL,
        "weakpass",
        "weakpass"
    )

    error = driver.find_element(By.ID, "registrationError")

    assert error.is_displayed()
    assert "8 characters, a letter, a number and a symbol" in error.text


def test_registration_rejects_mismatched_passwords(driver):
    submit_registration(
        driver,
        "Selenium Test Student",
        VALID_EMAIL,
        VALID_PASSWORD,
        "DifferentPass123!"
    )

    error = driver.find_element(By.ID, "registrationError")

    assert error.is_displayed()
    assert "Passwords do not match." in error.text


def test_registration_success_shows_login_link(driver):
    submit_registration(
        driver,
        "Selenium Test Student",
        "12345679@uap-bd.edu",
        VALID_PASSWORD,
        VALID_PASSWORD
    )

    success = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.ID, "registrationSuccess")
        )
    )

    assert "Registration successful!" in success.text

    login_link = success.find_element(By.TAG_NAME, "a")

    assert login_link.text == "Continue to log in"
    assert login_link.get_attribute("href").endswith("login.html")
