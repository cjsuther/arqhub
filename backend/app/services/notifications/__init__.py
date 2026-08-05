"""Notification providers (SPEC §11).

The seam for outbound notifications. Two providers ship:

* ``LoggingNotifier`` — records to the app log; the always-available default.
* ``TeamsNotifier`` — posts a MessageCard to a Microsoft Teams *Incoming Webhook*
  (just a URL — no M365 app registration). Any corporate chat that accepts an
  incoming webhook (Slack, Google Chat, Mattermost…) can reuse this seam by
  swapping the payload; select it with ``ARQHUB_NOTIFY_PROVIDER=teams`` and set
  ``ARQHUB_TEAMS_WEBHOOK_URL``.

Delivery is best-effort: a webhook failure is logged and never breaks the request.
"""

from __future__ import annotations

import logging

import httpx

from ...core.config import settings

logger = logging.getLogger("arqhub.notifications")


class NotificationProvider:
    """Base provider. Methods default to no-op so partial providers stay valid."""

    def approval_requested(self, *, view_slug: str, view_name: str, requested_by: str | None,
                           approvers: list[str], comment: str | None) -> None: ...

    def approval_resolved(self, *, view_slug: str, view_name: str, status: str,
                          resolved_by: str | None, requested_by: str | None) -> None: ...

    def comment_mention(self, *, view_slug: str, view_name: str, comment_by: str,
                        mentioned: list[str], body: str) -> None: ...

    def draft_shared(self, *, view_slug: str, view_name: str, shared_by: str,
                     users: list[str]) -> None: ...


def _view_link(slug: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/views/{slug}/edit"


class LoggingNotifier(NotificationProvider):
    """Records notifications to the app log — the always-available default."""

    def approval_requested(self, *, view_slug, view_name, requested_by, approvers, comment):
        logger.info("approval requested: view=%s by=%s approvers=%s comment=%r",
                    view_slug, requested_by, approvers, comment)

    def approval_resolved(self, *, view_slug, view_name, status, resolved_by, requested_by):
        logger.info("approval %s: view=%s by=%s -> notify requester=%s",
                    status, view_slug, resolved_by, requested_by)

    def comment_mention(self, *, view_slug, view_name, comment_by, mentioned, body):
        logger.info("comment mention: view=%s by=%s -> %s: %r", view_slug, comment_by, mentioned, body)

    def draft_shared(self, *, view_slug, view_name, shared_by, users):
        logger.info("draft shared: view=%s by=%s -> %s", view_slug, shared_by, users)


class TeamsNotifier(NotificationProvider):
    """Posts a MessageCard to a Teams (or compatible) Incoming Webhook."""

    THEME = {"approved": "2ecc71", "rejected": "e74c3c"}

    def __init__(self, webhook_url: str) -> None:
        self.url = webhook_url

    def _post(self, *, title: str, text: str, slug: str, color: str = "5b6bf0") -> None:
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "title": title,
            "text": text,
            "potentialAction": [{
                "@type": "OpenUri", "name": "Abrir en ArqHub",
                "targets": [{"os": "default", "uri": _view_link(slug)}],
            }],
        }
        try:
            httpx.post(self.url, json=card, timeout=5.0)
        except Exception as exc:  # best-effort: never break the caller
            logger.warning("Teams notification failed for view=%s: %s", slug, exc)

    def approval_requested(self, *, view_slug, view_name, requested_by, approvers, comment):
        self._post(
            title=f"Solicitud de aprobación: {view_name}",
            text=f"**{requested_by or 'Alguien'}** pidió revisar **{view_name}**."
                 + (f"<br>Aprobadores: {', '.join(approvers)}" if approvers else "")
                 + (f"<br>💬 {comment}" if comment else ""),
            slug=view_slug,
        )

    def approval_resolved(self, *, view_slug, view_name, status, resolved_by, requested_by):
        label = {"approved": "aprobada ✅", "rejected": "rechazada ❌"}.get(status, status)
        self._post(
            title=f"Revisión {label}: {view_name}",
            text=f"**{resolved_by or 'Alguien'}** dejó la vista **{view_name}** como {label}.",
            slug=view_slug, color=self.THEME.get(status, "5b6bf0"),
        )

    def comment_mention(self, *, view_slug, view_name, comment_by, mentioned, body):
        self._post(
            title=f"Te mencionaron en {view_name}",
            text=f"**{comment_by}** mencionó a {', '.join(mentioned)}:<br>💬 {body}",
            slug=view_slug,
        )

    def draft_shared(self, *, view_slug, view_name, shared_by, users):
        self._post(
            title=f"Compartieron un borrador: {view_name}",
            text=f"**{shared_by}** compartió el borrador **{view_name}** con {', '.join(users)}.",
            slug=view_slug,
        )


_notifier: NotificationProvider | None = None


def get_notifier() -> NotificationProvider:
    """Return the configured provider (built from settings on first use)."""
    global _notifier
    if _notifier is None:
        if settings.notify_provider == "teams" and settings.teams_webhook_url:
            _notifier = TeamsNotifier(settings.teams_webhook_url)
        else:
            _notifier = LoggingNotifier()
    return _notifier


def set_notifier(provider: NotificationProvider) -> None:
    """Override the provider (tests, or wiring another notifier at startup)."""
    global _notifier
    _notifier = provider
