"""Notification providers (SPEC §11).

``NotificationProvider`` is the seam for approval notifications. Phase 4 ships a
logging provider (always works, no external deps). A Teams provider (Graph API +
Adaptive Cards) and an SMTP email fallback slot in behind the same interface;
both need tenant credentials and cannot be exercised in a local/offline setup, so
they are provided as documented stubs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("arqhub.notifications")


class NotificationProvider(ABC):
    @abstractmethod
    def approval_requested(self, *, view_slug: str, view_name: str, requested_by: str | None,
                           approvers: list[str], comment: str | None) -> None: ...

    @abstractmethod
    def approval_resolved(self, *, view_slug: str, view_name: str, status: str,
                          resolved_by: str | None, requested_by: str | None) -> None: ...


class LoggingNotifier(NotificationProvider):
    """Records notifications to the app log — the always-available default."""

    def approval_requested(self, *, view_slug, view_name, requested_by, approvers, comment):
        logger.info(
            "approval requested: view=%s by=%s approvers=%s comment=%r",
            view_slug, requested_by, approvers, comment,
        )

    def approval_resolved(self, *, view_slug, view_name, status, resolved_by, requested_by):
        logger.info(
            "approval %s: view=%s by=%s -> notify requester=%s",
            status, view_slug, resolved_by, requested_by,
        )


_notifier: NotificationProvider | None = None


def get_notifier() -> NotificationProvider:
    """Return the configured provider. Teams/email plug in here in a full deploy."""
    global _notifier
    if _notifier is None:
        _notifier = LoggingNotifier()
    return _notifier


def set_notifier(provider: NotificationProvider) -> None:
    """Override the provider (tests, or wiring a Teams/email notifier at startup)."""
    global _notifier
    _notifier = provider
