"""Shared activity logging state helpers for UI guard logic."""

LOG_DECISION_PREFIX = "log_decision::"
LOG_COMMENT_PREFIX = "log_comment::"
LOG_MODIFIED_PREFIX = "log_modified::"
LOG_LAST_ENTRY_PREFIX = "log_last_entry::"

DECISION_LOGGED = "logged"
DECISION_SKIPPED = "skipped"


def _scope_token(participant_id, monitor, phase):
    """Build a stable token for per-phase/per-participant activity state."""
    phase_value = phase if phase else "NoPhase"
    return f"{participant_id}|{monitor}|{phase_value}"


def decision_key(participant_id, monitor, phase):
    return f"{LOG_DECISION_PREFIX}{_scope_token(participant_id, monitor, phase)}"


def comment_key(participant_id, monitor, phase):
    return f"{LOG_COMMENT_PREFIX}{_scope_token(participant_id, monitor, phase)}"


def modified_key(participant_id, monitor, phase):
    return f"{LOG_MODIFIED_PREFIX}{_scope_token(participant_id, monitor, phase)}"


def last_entry_key(participant_id, monitor, phase):
    return f"{LOG_LAST_ENTRY_PREFIX}{_scope_token(participant_id, monitor, phase)}"


def required_phase_labels(session_state):
    """Return phase labels that currently require an explicit log/skip decision."""
    participant_id = session_state.get("participant_id")
    monitor = session_state.get("device")
    if not participant_id or not monitor:
        return []

    if "phase_files" in session_state:
        labels = [pf["phase"] for pf in session_state["phase_files"] if pf.get("csv_file")]
        return labels

    return [session_state.get("phase") or "NoPhase"]


def pending_phase_labels(session_state):
    """Return phase labels that still need an explicit decision."""
    participant_id = session_state.get("participant_id")
    monitor = session_state.get("device")
    if not participant_id or not monitor:
        return []

    pending = []
    for phase in required_phase_labels(session_state):
        key = decision_key(participant_id, monitor, phase)
        if session_state.get(key) not in {DECISION_LOGGED, DECISION_SKIPPED}:
            pending.append(phase)
    return pending


def has_pending_log_decisions(session_state):
    """True if user must still choose log or skip for one or more phases."""
    return len(pending_phase_labels(session_state)) > 0


def all_activity_state_keys(session_state):
    """Return all activity-log keys to clear when leaving a participant context."""
    prefixes = (
        LOG_DECISION_PREFIX,
        LOG_COMMENT_PREFIX,
        LOG_MODIFIED_PREFIX,
        LOG_LAST_ENTRY_PREFIX,
    )
    return [k for k in session_state.keys() if k.startswith(prefixes)]
