"""
services/email_service.py
──────────────────────────
SMTP email service using smtplib.
Sends welcome emails to newly created users.
"""

from __future__ import annotations
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

logger = logging.getLogger(__name__)


def send_welcome_email(
    to_email: str,
    username: str,
    password: str,
    role: str,
) -> bool:
    """
    Send a welcome email to a newly created user.
    Returns True if sent successfully, False otherwise.
    """
    if not config.EMAIL_HOST_PASSWORD or not config.EMAIL_HOST_USER:
        logger.warning("Email credentials not configured. Skipping welcome email.")
        return False

    subject = "🎓 Welcome to WOCOTM Academy!"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 32px;">
        <div style="max-width: 560px; margin: auto; background: #fff; border-radius: 12px; padding: 40px;">
          <h1 style="color: #4F46E5; margin-bottom: 4px;">Welcome, {username}! 👋</h1>
          <p style="color: #555;">Your account has been created on <strong>WOCOTM Academy</strong>.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
          <h3 style="color: #333;">Your Access Credentials</h3>
          <table style="width:100%; font-size:15px; color:#333;">
            <tr>
              <td style="padding: 6px 0;"><strong>Username:</strong></td>
              <td>{username}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0;"><strong>Email:</strong></td>
              <td>{to_email}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0;"><strong>Password:</strong></td>
              <td style="font-family: monospace; background:#f0f0f0; padding:2px 8px; border-radius:4px;">{password}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0;"><strong>Role:</strong></td>
              <td>{role}</td>
            </tr>
          </table>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
          <p style="text-align:center;">
            <a href="{config.PLATFORM_URL}"
               style="background:#4F46E5; color:#fff; padding:12px 32px; border-radius:8px;
                      text-decoration:none; font-weight:bold; display:inline-block;">
              Access the Platform
            </a>
          </p>
          <p style="color:#aaa; font-size:12px; text-align:center; margin-top:24px;">
            Please change your password after your first login.<br>
            WOCOTM Academy &copy; {__import__('datetime').date.today().year}
          </p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(config.EMAIL_HOST_USER, config.EMAIL_HOST_PASSWORD)
            server.sendmail(config.EMAIL_FROM, to_email, msg.as_string())
        logger.info(f"Welcome email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {to_email}: {e}")
        return False
