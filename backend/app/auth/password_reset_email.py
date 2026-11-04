import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_password_reset_email(recipient: str, reset_token: str) -> bool:
    """Send a password reset link; expose it in logs only in development."""
    smtp_host = os.getenv("SMTP_HOST")
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        logger.error("SMTP_PORT must be a valid integer")
        smtp_port = None
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM_EMAIL")
    frontend_url = os.getenv(
        "FRONTEND_BASE_URL", "http://127.0.0.1:5500"
    ).rstrip("/")
    app_environment = os.getenv("APP_ENV", "production").strip().lower()
    reset_url = f"{frontend_url}/reset-password.html?token={reset_token}"

    if not all([smtp_host, smtp_port, smtp_username, smtp_password, sender]):
        logger.warning("Password reset email is not configured for %s", recipient)
        if app_environment in {"development", "dev", "local"}:
            logger.warning("Development-only password reset link: %s", reset_url)
        return False

    message = EmailMessage()
    message["Subject"] = "EventHub Password Reset"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your EventHub password.\n\n"
        f"Open this link to reset it (valid for 30 minutes):\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        logger.info("Password reset email accepted by SMTP for %s", recipient)
        return True
    except (OSError, smtplib.SMTPException, ValueError):
        logger.exception("Password reset email delivery failed for %s", recipient)
        if app_environment in {"development", "dev", "local"}:
            logger.warning("Development-only password reset link: %s", reset_url)
        return False
