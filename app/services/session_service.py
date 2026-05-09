"""List, read and delete chat sessions stored by Agno's PostgresDb."""

from typing import Any

from sqlalchemy import update

from app.agno_integration.storage_builder import get_session_db
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.schemas.session import (
    SessionDeleteResponse,
    SessionHistory,
    SessionMessage,
    SessionSummary,
)

logger = get_logger(__name__)

_TITLE_LENGTH = 15


def _kinds() -> list[tuple[str, Any]]:
    """Return the (kind, SessionType) pairs to query."""
    from agno.db.base import SessionType  # type: ignore

    return [("agent", SessionType.AGENT), ("team", SessionType.TEAM)]


def list_sessions(user_id: str) -> list[SessionSummary]:
    """Return every session belonging to ``user_id`` across agents and teams."""
    db = get_session_db()
    summaries: list[SessionSummary] = []
    for kind, session_type in _kinds():
        try:
            sessions = db.get_sessions(session_type=session_type, user_id=user_id) or []
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to list %s sessions for user=%s: %s", kind, user_id, exc)
            continue
        for session in sessions:
            summaries.append(_to_summary(kind, session))
    summaries.sort(key=lambda s: s.updated_at or s.created_at or 0, reverse=True)
    return summaries


def get_history(session_id: str) -> SessionHistory:
    """Return the full message history for ``session_id``."""
    db = get_session_db()
    for kind, session_type in _kinds():
        try:
            session = db.get_session(session_id=session_id, session_type=session_type)
        except Exception:
            session = None
        if session is not None:
            return _to_history(kind, session)
    raise NotFoundError(f"Session {session_id} not found")


def delete_session(session_id: str) -> SessionDeleteResponse:
    """Delete ``session_id`` from the shared session store."""
    db = get_session_db()
    try:
        deleted = bool(db.delete_session(session_id=session_id))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to delete session %s: %s", session_id, exc)
        deleted = False
    if not deleted:
        raise NotFoundError(f"Session {session_id} not found")
    return SessionDeleteResponse(session_id=session_id, deleted=True)


def rename_session(session_id: str, title: str) -> SessionSummary:
    """Persist a custom ``title`` on ``session_id`` without touching ``updated_at``."""
    cleaned = title.strip()
    if not cleaned:
        raise ValueError("Title cannot be empty")

    db = get_session_db()
    table = db._get_table(table_type="sessions")
    if table is None:
        raise NotFoundError(f"Session {session_id} not found")

    for kind, session_type in _kinds():
        try:
            session = db.get_session(session_id=session_id, session_type=session_type)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load %s session %s: %s", kind, session_id, exc)
            session = None
        if session is None:
            continue
        data = getattr(session, "session_data", None)
        data = dict(data) if isinstance(data, dict) else {}
        data["session_name"] = cleaned
        try:
            with db.Session() as sess, sess.begin():
                sess.execute(
                    update(table)
                    .where(table.c.session_id == session_id)
                    .values(session_data=data)
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to rename %s session %s: %s", kind, session_id, exc)
            continue
        session.session_data = data
        return _to_summary(kind, session)
    raise NotFoundError(f"Session {session_id} not found")


def _to_summary(kind: str, session: Any) -> SessionSummary:
    messages = _extract_messages(session)
    return SessionSummary(
        session_id=str(getattr(session, "session_id", "")),
        user_id=_str_or_none(getattr(session, "user_id", None)),
        entity_id=_entity_id(session, kind),
        kind=kind,
        title=_session_name(session) or _build_title(messages),
        created_at=_int_or_none(getattr(session, "created_at", None)),
        updated_at=_int_or_none(getattr(session, "updated_at", None)),
    )


def _to_history(kind: str, session: Any) -> SessionHistory:
    return SessionHistory(
        session_id=str(getattr(session, "session_id", "")),
        user_id=_str_or_none(getattr(session, "user_id", None)),
        entity_id=_entity_id(session, kind),
        kind=kind,
        messages=_extract_messages(session),
        created_at=_int_or_none(getattr(session, "created_at", None)),
        updated_at=_int_or_none(getattr(session, "updated_at", None)),
    )


def _extract_messages(session: Any) -> list[SessionMessage]:
    """Use Agno's ``get_chat_history`` and normalize messages for the API."""
    getter = getattr(session, "get_chat_history", None)
    raw: list[Any] = []
    if callable(getter):
        try:
            raw = list(getter() or [])
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("get_chat_history failed: %s", exc)
            raw = []
    if not raw:
        raw = _fallback_messages_from_runs(session)

    out: list[SessionMessage] = []
    for item in raw:
        msg = _normalize_msg(item)
        if msg is not None:
            out.append(msg)
    return out


def _fallback_messages_from_runs(session: Any) -> list[Any]:
    """Walk ``session.runs`` directly when ``get_chat_history`` is unavailable."""
    runs = getattr(session, "runs", None) or []
    messages: list[Any] = []
    for run in runs:
        run_msgs = getattr(run, "messages", None)
        if isinstance(run_msgs, list):
            messages.extend(run_msgs)
    return messages


def _normalize_msg(item: Any) -> SessionMessage | None:
    role = getattr(item, "role", None)
    content = getattr(item, "content", None)
    if role is None and isinstance(item, dict):
        role = item.get("role")
        content = item.get("content")
    if role is None or content is None:
        return None
    if not isinstance(content, str):
        content = str(content)
    if not content.strip():
        return None
    return SessionMessage(role=str(role), content=content)


def _build_title(messages: list[SessionMessage]) -> str:
    for msg in messages:
        if msg.role == "user":
            text = msg.content.strip().replace("\n", " ")
            if text:
                return text[:_TITLE_LENGTH]
    return "New chat"


def _entity_id(session: Any, kind: str) -> str | None:
    attr = "agent_id" if kind == "agent" else "team_id"
    return _str_or_none(getattr(session, attr, None))


def _session_name(session: Any) -> str | None:
    data = getattr(session, "session_data", None)
    if not isinstance(data, dict):
        return None
    name = data.get("session_name")
    if not isinstance(name, str):
        return None
    cleaned = name.strip()
    return cleaned or None


def _str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
