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


# Back-compat re-exports: the template functions now live in ./templates.
from .templates import attorney_notification_html, prospect_confirmation_html  # noqa: E402,F401

