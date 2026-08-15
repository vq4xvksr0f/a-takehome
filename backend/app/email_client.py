"""Email port + console and Resend adapters, selected by EMAIL_PROVIDER."""

import logging
from abc import ABC, abstractmethod

import resend

from .config import Settings

logger = logging.getLogger(__name__)


class EmailClient(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, html: str) -> None: ...


class ConsoleEmailClient(EmailClient):
    """Local fallback: prints the full email to stdout instead of sending it.

    Uses print() rather than the logging framework so the output always shows
    up in `docker compose logs`, regardless of how uvicorn configures logging.
    """

    def send(self, to: str, subject: str, html: str) -> None:
        print(
            f"\n===== OUTBOUND EMAIL (console) =====\n"
            f"To:      {to}\n"
            f"Subject: {subject}\n"
            f"Body:\n{html}\n"
            f"====================================\n",
            flush=True,
        )


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
    return (
        "<html><body>"
        f"<p>Thanks {first_name}, we received your application.</p>"
        "<p>Our team will review it and reach out shortly.</p>"
        "</body></html>"
    )


def attorney_notification_html(first_name: str, last_name: str, email: str) -> str:
    return (
        "<html><body>"
        f"<p>New lead: {first_name} {last_name} &lt;{email}&gt;</p>"
        "<p>Log in to the lead dashboard to review the application.</p>"
        "</body></html>"
    )
