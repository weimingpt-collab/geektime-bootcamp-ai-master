"""Streaming export service for query results (US4).

Provides CSV/JSON streaming generators that consume batches from an
adapter's `stream_query` method and yield UTF-8 encoded bytes suitable
for FastAPI's `StreamingResponse`.

Design notes:
- CSV output begins with a UTF-8 BOM (``\\ufeff``) for Excel compatibility.
- CSV fields are RFC 4180 quoted; fields starting with ``= + - @`` are
  prefixed with a single quote to mitigate Excel formula injection.
- JSON output is a single JSON Array (``[{...}, {...}]``), NOT NDJSON.
- The caller is responsible for SQL validation; this module rewrites the
  AST to inject `LIMIT {max_rows}` so the default LIMIT 1000 from
  `validate_and_transform_sql` is NOT applied.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import AsyncGenerator, Dict, List, Any, Iterable

import sqlglot
from sqlglot import exp

from app.adapters.base import DatabaseAdapter
from app.models.database import DatabaseType


# Hard cap for export row count (also enforced at the API layer).
MAX_EXPORT_ROWS = 100_000


def inject_limit(sql: str, max_rows: int, db_type: DatabaseType) -> str:
    """Rewrite a SELECT statement's AST to enforce a LIMIT clause.

    If the statement already has a LIMIT, the smaller of the existing
    value and `max_rows` is used. Otherwise `LIMIT {max_rows}` is added.
    This avoids the default LIMIT 1000 applied by
    `validate_and_transform_sql`, which is inappropriate for exports.

    Args:
        sql: A SELECT statement (already validated as SELECT-only).
        max_rows: Maximum rows the export should yield.
        db_type: Target database type, used to select the sqlglot dialect.

    Returns:
        SQL string with a LIMIT clause guaranteed to be <= max_rows.
    """
    dialect = "postgres" if db_type == DatabaseType.POSTGRESQL else "mysql"
    parsed = sqlglot.parse_one(sql, dialect=dialect)
    if parsed is None:
        # Should never happen because the caller validates first.
        return sql

    existing = parsed.find(exp.Limit)
    if existing is not None:
        # Try to compare numeric values; if existing > max_rows, replace.
        try:
            existing_val = int(existing.expression.name)  # type: ignore[union-attr]
            if existing_val > max_rows:
                parsed.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
        except (AttributeError, ValueError, TypeError):
            # Non-numeric LIMIT (e.g., parameter placeholder): leave as-is
            # but still cap by adding a wrapper if possible. For safety we
            # just replace with the explicit cap.
            parsed.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
    else:
        parsed.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return parsed.sql(dialect=dialect)


def sanitize_csv_field(value: Any) -> str:
    """Convert a Python value to an RFC 4180-safe CSV field string.

    Rules:
    - ``None`` -> empty string
    - ``bool`` -> ``"true"`` / ``"false"``
    - ``datetime`` / ``date`` -> ISO 8601 string
    - ``Decimal`` -> string representation
    - ``str``: if it contains ``,`` ``"`` or newline, wrap in ``"..."``
      and double any internal quotes. If the resulting field starts with
      ``=``, ``+``, ``-`` or ``@``, prefix with a single quote to guard
      against Excel formula injection.
    - Other types: ``str(value)``, then apply the same quoting rules.

    Args:
        value: The raw cell value from the database.

    Returns:
        A string ready to be written between delimiters in a CSV row.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (datetime, date)):
        text = value.isoformat()
    elif isinstance(value, Decimal):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        text = str(value)

    needs_quote = ("," in text) or ('"' in text) or ("\n" in text) or ("\r" in text)
    if needs_quote:
        text = '"' + text.replace('"', '""') + '"'
    else:
        # Excel formula injection guard: only meaningful for unquoted
        # fields. A quoted field already starting with '"' is safe.
        if text and text[0] in ("=", "+", "-", "@"):
            text = "'" + text
    return text


def _row_to_csv_line(row: Dict[str, Any], column_order: List[str], delimiter: str) -> str:
    """Serialize a single row to a CSV line (without trailing newline)."""
    return delimiter.join(sanitize_csv_field(row.get(col)) for col in column_order)


def _value_for_json(value: Any) -> Any:
    """Normalize a DB value for JSON serialization."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        # Preserve precision as string; callers expecting numbers can
        # coerce if needed. JSON spec has no Decimal type.
        return str(value)
    return value


async def stream_csv(
    adapter: DatabaseAdapter,
    sql: str,
    max_rows: int = MAX_EXPORT_ROWS,
    delimiter: str = ",",
) -> AsyncGenerator[bytes, None]:
    """Stream a SELECT query's result as UTF-8 CSV bytes.

    The first chunk contains the UTF-8 BOM plus the header row and the
    first batch of data rows. Subsequent chunks contain only data rows.
    Each chunk is a ``bytes`` object; chunk boundaries are opaque to
    the caller (the browser reassembles the file).

    Args:
        adapter: Database adapter with `stream_query` implemented.
        sql: Validated SELECT statement (without LIMIT injected yet).
        max_rows: Maximum rows to emit. Caller should also inject LIMIT.
        delimiter: CSV field delimiter (default ``,``).

    Yields:
        bytes: UTF-8 encoded CSV chunks.
    """
    # Yield BOM first so Excel detects UTF-8 even if the first data
    # batch is empty.
    bom = "\ufeff".encode("utf-8")

    column_order: List[str] = []
    header_emitted = False
    rows_emitted = 0

    async for batch in adapter.stream_query(sql, batch_size=1000, max_rows=max_rows):
        if not column_order:
            if not batch:
                # No rows yet; we still need a header. We can't know
                # column names without executing, so emit BOM only and
                # let downstream be empty.
                yield bom
                return
            # Derive column order from the first row's keys.
            column_order = list(batch[0].keys())
            header_line = delimiter.join(column_order)
            yield bom + header_line.encode("utf-8") + b"\n"
            header_emitted = True
        elif not header_emitted:
            # Should not happen, but guard defensively.
            yield bom
            header_emitted = True

        out_parts: List[bytes] = []
        for row in batch:
            line = _row_to_csv_line(row, column_order, delimiter)
            out_parts.append(line.encode("utf-8") + b"\n")
            rows_emitted += 1
        if out_parts:
            yield b"".join(out_parts)

    if not header_emitted:
        # Query returned zero rows: emit BOM only (empty file body).
        yield bom


async def stream_json(
    adapter: DatabaseAdapter,
    sql: str,
    max_rows: int = MAX_EXPORT_ROWS,
) -> AsyncGenerator[bytes, None]:
    """Stream a SELECT query's result as a UTF-8 JSON Array.

    Output shape: ``[{...}, {...}]``. The opening ``[`` is yielded
    first; each row object is yielded with a leading ``,`` separator
    (except the first); the closing ``]`` is yielded last. No BOM.

    Args:
        adapter: Database adapter with `stream_query` implemented.
        sql: Validated SELECT statement.
        max_rows: Maximum rows to emit.

    Yields:
        bytes: UTF-8 encoded JSON chunks.
    """
    first = True
    yielded_any = False

    yield b"["

    async for batch in adapter.stream_query(sql, batch_size=1000, max_rows=max_rows):
        out_parts: List[bytes] = []
        for row in batch:
            normalized = {k: _value_for_json(v) for k, v in row.items()}
            line = json.dumps(normalized, ensure_ascii=False)
            if first:
                out_parts.append(line.encode("utf-8"))
                first = False
            else:
                out_parts.append(b"," + line.encode("utf-8"))
            yielded_any = True
        if out_parts:
            yield b"".join(out_parts)

    yield b"]"


def build_filename(database_name: str, fmt: str) -> str:
    """Build a download filename for an export.

    Args:
        database_name: The connection name (sanitized).
        fmt: ``"csv"`` or ``"json"``.

    Returns:
        Filename like ``mydb_20260807-120000.csv``.
    """
    # Sanitize: keep alphanumerics, dash, underscore; replace others.
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in database_name)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    ext = "csv" if fmt == "csv" else "json"
    return f"{safe_name}_{timestamp}.{ext}"
