"""Lead-related email notifications.

Best-effort by design (design doc §9/§11): the lead record is the source of
truth, so a delivery failure is logged and never propagated to the caller.
"""

import logging
import threading

from ..adapters.email_client import (
    EmailClient,
    attorney_notification_html,
    prospect_confirmation_html,
)
from ..models import Lead

logger = logging.getLogger(__name__)

PROSPECT_SUBJECT = "We received your application"
ATTORNEY_SUBJECT = "New lead submission"


class EmailService:
    def __init__(self, email_client: EmailClient) -> None:
        self._email = email_client

    def send_submission_emails(self, lead: Lead, notify_email: str) -> None:
        """Send the prospect confirmation and attorney notification."""
        try:
            self._email.send(
                to=lead.email,
                subject=PROSPECT_SUBJECT,
                html=prospect_confirmation_html(lead.first_name),
            )
            logger.info("sent prospect confirmation for lead %s", lead.id)
        except Exception:
            logger.exception("Failed to send prospect confirmation for lead %s", lead.id)
        try:
            self._email.send(
                to=notify_email,
                subject=ATTORNEY_SUBJECT,
                html=attorney_notification_html(lead.first_name, lead.last_name, lead.email),
            )
            logger.info("sent attorney notification for lead %s", lead.id)
        except Exception:
            logger.exception("Failed to send attorney notification for lead %s", lead.id)

    def send_submission_emails_async(self, lead: Lead, notify_email: str) -> None:
        """Fire-and-forget wrapper: send on a daemon thread, never block the request.

        Extracts plain values up front so the thread holds no ORM object bound
        to a request-scoped session.
        """
        lead_id = lead.id
        lead_email = lead.email
        first_name = lead.first_name
        last_name = lead.last_name

        def _send() -> None:
            try:
                self._email.send(
                    to=lead_email,
                    subject=PROSPECT_SUBJECT,
                    html=prospect_confirmation_html(first_name),
                )
                logger.info("sent prospect confirmation for lead %s", lead_id)
            except Exception:
                logger.exception("Failed to send prospect confirmation for lead %s", lead_id)
            try:
                self._email.send(
                    to=notify_email,
                    subject=ATTORNEY_SUBJECT,
                    html=attorney_notification_html(first_name, last_name, lead_email),
                )
                logger.info("sent attorney notification for lead %s", lead_id)
            except Exception:
                logger.exception("Failed to send attorney notification for lead %s", lead_id)

        threading.Thread(target=_send, daemon=True).start()
