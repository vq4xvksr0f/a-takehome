"""Email port + console and Resend adapters, selected by EMAIL_PROVIDER."""

import logging
from abc import ABC, abstractmethod
from html import escape

import resend

from ..core.config import Settings

logger = logging.getLogger(__name__)


class EmailClient(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, html: str) -> None: ...


class ConsoleEmailClient(EmailClient):
    """Local fallback: logs the full email instead of sending it."""

    def send(self, to: str, subject: str, html: str) -> None:
        logger.info("OUTBOUND EMAIL\nto: %s\nsubject: %s\n%s", to, subject, html)


class ResendEmailClient(EmailClient):
    def __init__(self, settings: Settings) -> None:
        resend.api_key = settings.RESEND_API_KEY
        self._from = settings.EMAIL_FROM

    def send(self, to: str, subject: str, html: str) -> None:
        resend.Emails.send(
            {"from": self._from, "to": [to], "subject": subject, "html": html}
        )


def build_email_client(settings: Settings) -> EmailClient:
    if settings.EMAIL_PROVIDER == "resend":
        return ResendEmailClient(settings)
    return ConsoleEmailClient()


# ── Templates (plain transactional HTML) ─────────────────────────────────


def prospect_confirmation_html(first_name: str) -> str:
    name = escape(first_name)
    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#f4f5f7;color:#1c2330;font-family:Arial,sans-serif;">
    <div style="max-width:560px;margin:96px auto;padding:0 16px;">
      <div style="background:#16324f;color:#ffffff;padding:32px 24px;border-radius:8px 8px 0 0;">
        <strong style="font-size:18px;">Application received</strong>
      </div>
      <div style="background:#ffffff;padding:48px 24px;border-radius:0 0 8px 8px;">
        <p style="margin:0 0 24px;font-size:17px;">Thanks, {name}.</p>
        <p style="margin:0 0 24px;line-height:1.6;">We received your application and our team will review it shortly.</p>
        <p style="margin:0;color:#5c6572;line-height:1.6;">We will be in touch soon with the next steps.</p>
      </div>
      <p style="margin:40px 0;text-align:center;color:#5c6572;font-size:12px;">Thank you for reaching out.</p>
    </div>
  </body>
</html>"""


def attorney_notification_html(first_name: str, last_name: str, email: str) -> str:
    name = escape(f"{first_name} {last_name}")
    address = escape(email)
    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#f4f5f7;color:#1c2330;font-family:Arial,sans-serif;">
    <div style="max-width:560px;margin:96px auto;padding:0 16px;">
      <div style="background:#16324f;color:#ffffff;padding:32px 24px;border-radius:8px 8px 0 0;">
        <strong style="font-size:18px;">New lead submission</strong>
      </div>
      <div style="background:#ffffff;padding:48px 24px;border-radius:0 0 8px 8px;">
        <p style="margin:0 0 32px;line-height:1.6;">A new application is ready for review.</p>
        <div style="background:#f4f5f7;padding:24px 16px;border-radius:8px;line-height:1.7;">
          <strong>{name}</strong><br>
          <a href="mailto:{address}" style="color:#16324f;">{address}</a>
        </div>
        <p style="margin:32px 0 0;line-height:1.6;">Log in to the lead dashboard to review the application.</p>
      </div>
    </div>
  </body>
</html>"""
