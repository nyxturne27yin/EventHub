"""Allowed lifecycle transitions for EventHub events."""

ALLOWED_EVENT_STATUS_TRANSITIONS = {
    "draft": {"published", "cancelled"},
    "published": {"completed", "cancelled"},
    "cancelled": set(),
    "completed": set(),
}


def can_transition_event_status(current_status: str, new_status: str) -> bool:
    """Return whether an event may move from its current status to a new status."""
    current = (current_status or "").strip().lower()
    target = (new_status or "").strip().lower()

    return target in ALLOWED_EVENT_STATUS_TRANSITIONS.get(current, set())
