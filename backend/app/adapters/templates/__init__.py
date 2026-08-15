"""Email templates as external HTML files, loaded once at import time.

Keeping the markup out of Python makes the templates easier to preview and
edit. Placeholders use str.format syntax ({name}, {address}); values are
HTML-escaped before substitution.
"""

from html import escape
from pathlib import Path

_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_DIR / name).read_text(encoding="utf-8")


_PROSPECT_CONFIRMATION = _load("prospect_confirmation.html")
_ATTORNEY_NOTIFICATION = _load("attorney_notification.html")


def prospect_confirmation_html(first_name: str) -> str:
    return _PROSPECT_CONFIRMATION.format(name=escape(first_name))


def attorney_notification_html(first_name: str, last_name: str, email: str) -> str:
    return _ATTORNEY_NOTIFICATION.format(
        name=escape(f"{first_name} {last_name}"), address=escape(email)
    )
