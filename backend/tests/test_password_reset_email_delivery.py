from app.auth.password_reset_email import send_password_reset_email


def clear_smtp_settings(monkeypatch):
    for key in (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_development_fallback_logs_reset_link(monkeypatch, caplog):
    clear_smtp_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:5500")

    result = send_password_reset_email("student@example.edu", "dev-only-token")

    assert result is False
    assert "reset-password.html?token=dev-only-token" in caplog.text


def test_production_fallback_never_logs_reset_token(monkeypatch, caplog):
    clear_smtp_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")

    result = send_password_reset_email("student@example.edu", "production-secret-token")

    assert result is False
    assert "production-secret-token" not in caplog.text


def test_invalid_smtp_port_does_not_crash_and_uses_dev_fallback(monkeypatch, caplog):
    clear_smtp_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SMTP_PORT", "not-a-port")

    result = send_password_reset_email("student@example.edu", "safe-dev-token")

    assert result is False
    assert "safe-dev-token" in caplog.text
