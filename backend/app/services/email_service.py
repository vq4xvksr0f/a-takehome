"""Lead-related email notifications.

Best-effort by design (design doc §9/§11): the lead record is the source of
truth, so a delivery failure is logged and never propagated to the caller.
Transient failures are retried with exponential backoff; a permanently failing
send is logged and dropped. Durable at-least-once delivery would move these
onto the email_outbox table with a background worker (§9) — schema exists, no
worker is built.
"""

import logging
import threading
import time
from collections.abc import Callable

from ..adapters.email_client import (
    EmailClient,
    attorney_notification_html,
    prospect_confirmation_html,
)
from ..models import Lead

logger = logging.getLogger(__name__)

PROSPECT_SUBJECT = "We received your application"
ATTORNEY_SUBJECT = "New lead submission"

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 1.0


class EmailService:
    def __init__(self, email_client: EmailClient) -> None:
        self._email = email_client

    def _send_with_retry(self, send: Callable[[], None], description: str) -> None:
        """Run a send, retrying transient failures with exponential backoff.

        Never raises: after the final attempt the failure is logged and dropped
        (best-effort contract). Sleeps between attempts, so call this off the
        request path (the async wrapper does).
        """
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                send()
                logger.info("sent %s", description)
                return
            except Exception:
                if attempt == _MAX_ATTEMPTS:
                    logger.exception(
                        "Failed to send %s after %d attempts; giving up",
                        description,
                        _MAX_ATTEMPTS,
                    )
                    return
                delay = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Failed to send %s (attempt %d/%d); retrying in %.1fs",
                    description,
                    attempt,
                    _MAX_ATTEMPTS,
                    delay,
                )
                time.sleep(delay)

    def send_submission_emails(self, lead: Lead, notify_email: str) -> None:
        """Send the prospect confirmation and attorney notification (with retry)."""
        self._send_with_retry(
            lambda: self._email.send(
                to=lead.email,
                subject=PROSPECT_SUBJECT,
                html=prospect_confirmation_html(lead.first_name),
            ),
            f"prospect confirmation for lead {lead.id}",
        )
        self._send_with_retry(
            lambda: self._email.send(
                to=notify_email,
                subject=ATTORNEY_SUBJECT,
                html=attorney_notification_html(lead.first_name, lead.last_name, lead.email),
            ),
            f"attorney notification for lead {lead.id}",
        )

    def send_submission_emails_async(self, lead: Lead, notify_email: str) -> None:
        """Fire-and-forget wrapper: send on a daemon thread, never block the request.

        Extracts plain values up front so the thread holds no ORM object bound
        to a request-scoped session. Retries happen on the background thread.
        """
        lead_id = lead.id
        lead_email = lead.email
        first_name = lead.first_name
        last_name = lead.last_name

        def _send() -> None:
            self._send_with_retry(
                lambda: self._email.send(
                    to=lead_email,
                    subject=PROSPECT_SUBJECT,
                    html=prospect_confirmation_html(first_name),
                ),
                f"prospect confirmation for lead {lead_id}",
            )
            self._send_with_retry(
                lambda: self._email.send(
                    to=notify_email,
                    subject=ATTORNEY_SUBJECT,
                    html=attorney_notification_html(first_name, last_name, lead_email),
                ),
                f"attorney notification for lead {lead_id}",
            )

        threading.Thread(target=_send, daemon=True).start()
