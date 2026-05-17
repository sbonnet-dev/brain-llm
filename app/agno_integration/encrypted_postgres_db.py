"""``PostgresDb`` subclass that transparently encrypts chat message content.

Agno owns every read and write to ``brain.agno_sessions``. To keep messages
encrypted at rest without forking Agno, we override the four entry points
that touch the ``runs`` JSONB column and apply our AES-GCM helpers from
``app.core.crypto`` to the ``content`` field of every message inside each run.

Reads decrypt before returning so Agno keeps seeing plaintext (the LLM needs
real context). The HTTP API re-encrypts at the boundary — see
``session_service.get_history``.
"""

from __future__ import annotations

from typing import Any, Optional

from agno.db.postgres import PostgresDb  # type: ignore

from app.core.crypto import decrypt_text, encrypt_text, is_encrypted
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _encrypt_runs_in_dict(session_dict: dict[str, Any]) -> None:
    runs = session_dict.get("runs")
    if not runs:
        return
    for run in runs:
        _transform_run_messages(run, encrypt_text)


def _decrypt_runs_in_dict(session_dict: dict[str, Any]) -> None:
    runs = session_dict.get("runs")
    if not runs:
        return
    for run in runs:
        _transform_run_messages(run, _safe_decrypt)


def _transform_run_messages(run: Any, fn) -> None:
    """Apply ``fn`` to every message ``content`` inside ``run``.

    ``run`` may be a dict (after ``to_dict``) or a ``RunOutput``-like object
    (in deserialized sessions returned from Agno). We handle both.
    """
    if isinstance(run, dict):
        messages = run.get("messages")
        if isinstance(messages, list):
            for msg in messages:
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str) and content:
                        msg["content"] = fn(content)
        return

    messages = getattr(run, "messages", None)
    if not isinstance(messages, list):
        return
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str) and content:
                msg["content"] = fn(content)
            continue
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content:
            try:
                setattr(msg, "content", fn(content))
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to set message.content: %s", exc)


def _safe_decrypt(value: str) -> str:
    """Decrypt or pass through legacy plaintext records."""
    if not is_encrypted(value):
        return value
    try:
        return decrypt_text(value)
    except Exception as exc:
        logger.warning("Failed to decrypt message content: %s", exc)
        return value


def _decrypt_session_obj(session: Any) -> None:
    runs = getattr(session, "runs", None)
    if not runs:
        return
    for run in runs:
        _transform_run_messages(run, _safe_decrypt)


class EncryptedPostgresDb(PostgresDb):
    """PostgresDb that encrypts message ``content`` in the ``runs`` JSONB."""

    # -- writes -----------------------------------------------------------

    def upsert_session(self, session: Any, deserialize: Optional[bool] = True) -> Any:
        # Monkey-patch ``to_dict`` on the session instance so that super()
        # sees encrypted ``runs`` without us having to clone the whole
        # session object (which can be expensive and may contain non-pickle
        # references).
        original = session.to_dict

        def encrypted_to_dict():
            d = original()
            _encrypt_runs_in_dict(d)
            return d

        session.to_dict = encrypted_to_dict
        try:
            result = super().upsert_session(session, deserialize=deserialize)
        finally:
            try:
                del session.to_dict
            except AttributeError:
                pass

        if result is None:
            return None
        if deserialize:
            _decrypt_session_obj(result)
        elif isinstance(result, dict):
            _decrypt_runs_in_dict(result)
        return result

    def upsert_sessions(
        self,
        sessions: list[Any],
        deserialize: Optional[bool] = True,
        preserve_updated_at: bool = False,
    ) -> Any:
        patched: list[Any] = []
        originals: list[Any] = []
        for s in sessions:
            originals.append(s.to_dict)

            def make_patched(orig):
                def encrypted_to_dict():
                    d = orig()
                    _encrypt_runs_in_dict(d)
                    return d

                return encrypted_to_dict

            s.to_dict = make_patched(originals[-1])
            patched.append(s)
        try:
            results = super().upsert_sessions(
                sessions, deserialize=deserialize, preserve_updated_at=preserve_updated_at
            )
        finally:
            for s in patched:
                try:
                    del s.to_dict
                except AttributeError:
                    pass

        if not results:
            return results
        for item in results:
            if item is None:
                continue
            if deserialize:
                _decrypt_session_obj(item)
            elif isinstance(item, dict):
                _decrypt_runs_in_dict(item)
        return results

    # -- reads ------------------------------------------------------------

    def get_session(
        self,
        session_id: str,
        session_type: Any = None,
        user_id: Optional[str] = None,
        deserialize: Optional[bool] = True,
    ) -> Any:
        result = super().get_session(
            session_id=session_id,
            session_type=session_type,
            user_id=user_id,
            deserialize=deserialize,
        )
        if result is None:
            return None
        if deserialize:
            _decrypt_session_obj(result)
        elif isinstance(result, dict):
            _decrypt_runs_in_dict(result)
        return result

    def get_sessions(self, *args, **kwargs) -> Any:
        deserialize = kwargs.get("deserialize", True)
        result = super().get_sessions(*args, **kwargs)
        if result is None:
            return result
        if deserialize:
            for s in result or []:
                _decrypt_session_obj(s)
            return result
        # deserialize=False returns (list[dict], total_count)
        if isinstance(result, tuple) and len(result) == 2:
            rows, total = result
            for row in rows or []:
                if isinstance(row, dict):
                    _decrypt_runs_in_dict(row)
            return rows, total
        return result
