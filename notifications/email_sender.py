"""
Email notification sender — uses stdlib smtplib (no extra dependencies).
Called after a successful remediation to notify the admin.
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST         = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME     = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD     = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL   = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME)
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")


def send_remediation_email(
    resource_id: str,
    resource_name: str,
    resource_type: str,
    region: str,
    action: str,
    savings_per_month: float,
    remediated_by: str,
    timestamp: datetime | None = None,
) -> tuple[bool, str]:
    """
    Send a remediation notification email.
    Returns (success: bool, error_message: str).
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD or not NOTIFICATION_EMAIL:
        return False, "SMTP credentials not configured in .env"

    ts = (timestamp or datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S UTC")

    subject = "Cloud Cost Optimizer — Resource Remediated"

    body = f"""\
Cloud Cost Optimizer — Remediation Report
==========================================

A resource has been successfully remediated.

  Resource ID   : {resource_id}
  Name          : {resource_name}
  Type          : {resource_type}
  Region        : {region}
  Action Taken  : {action}
  Savings/Month : ${savings_per_month:.2f}
  Remediated By : {remediated_by}
  Timestamp     : {ts}

--
This is an automated notification from Cloud Cost Optimizer.
"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_FROM_EMAIL
        msg["To"]      = NOTIFICATION_EMAIL
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, NOTIFICATION_EMAIL, msg.as_string())

        return True, ""

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — check App Password in .env"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Email error: {e}"
