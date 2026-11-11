"""Helpers for the Postgres RLS backstop.

Django connects to Postgres with one role, so tenant isolation is enforced in
two layers. This module owns layer 1: a transaction-local session setting that
RLS policies read. The setting is always scoped to the current transaction so
it is safe with connection pooling (`set_config(..., true)` == SET LOCAL).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import connection


def set_current_user_id(user_id: uuid.UUID | str | None) -> None:
    """Set the RLS tenant for the current transaction.

    Passing None/empty clears the setting. Policies fail closed: if the value
    is missing, empty, or not a UUID, no merchant rows are visible or writable.
    """
    value = "" if user_id is None else str(user_id)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_user_id', %s, true)", [value])


def clear_current_user_id() -> None:
    set_current_user_id(None)


def current_user_id() -> str | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_user_id', true)")
        row: tuple[Any, ...] = cursor.fetchone()
    value = row[0] if row else None
    return value or None
