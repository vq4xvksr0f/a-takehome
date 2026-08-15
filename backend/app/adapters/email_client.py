"""Email port + console and Resend adapters, selected by EMAIL_PROVIDER."""

import logging
from abc import ABC, abstractmethod

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
