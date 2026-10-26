
import os
import smtplib
from email.message import EmailMessage


def send_password_reset_email(recipient: str, reset_token: str) -> bool:
    """Send a password reset link using SMTP settings from environment variables."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM_EMAIL")
    frontend_url = os.getenv(
        "FRONTEND_BASE_URL",
        "http://127.0.0.1:5500",
    ).rstrip("/")

    if not all([smtp_host, smtp_username, smtp_password, sender]):
        return False

    reset_url = f"{frontend_url}/reset-password.html?token={reset_token}"

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
        return True
    except (OSError, smtplib.SMTPException, ValueError):
        return False
