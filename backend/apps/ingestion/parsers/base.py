"""Source parser protocol and shared raw row types.

Parsers are pure with respect to infrastructure: they receive a binary stream
and an optional secret, and must not import Django models or touch HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import BinaryIO, Protocol


class StatementParseError(Exception):
    """Base parser error. Messages must never include the password or PDF bytes."""


class StatementPasswordError(StatementParseError):
    """The supplied password could not decrypt the statement."""


class StatementFormatError(StatementParseError):
    """The file is not a readable statement PDF."""


@dataclass(frozen=True)
class RawTransactionRow:
    receipt: str
    completion_time: str
    details: str
    status: str = ""
    paid_in: Decimal | None = None
    withdrawn: Decimal | None = None
    balance: Decimal | None = None


@dataclass(frozen=True)
class SkippedRow:
    page: int
    reason: str
    excerpt: str = ""


@dataclass
class ParseResult:
    rows: list[RawTransactionRow] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pages: int = 0
    layout_variant: str = "unknown"


class StatementParser(Protocol):
    def parse(self, file: BinaryIO, secret: str | None) -> ParseResult: ...
