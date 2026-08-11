"""Database connection service for managing MySQL connections."""

import aiomysql
from typing import Dict
from datetime import datetime
from urllib.parse import urlparse, unquote
from app.models.database import DatabaseConnection, ConnectionStatus


# Global connection pool cache
_connection_pools: Dict[str, aiomysql.Pool] = {}


def _parse_url(url: str) -> dict:
    """Parse MySQL URL and percent-decode user/password.

    Percent-decoding is required because passwords containing special
    characters (@, :, /, #, space) must be percent-encoded in the URL
    (e.g. p@ss -> p%40ss). Without unquote, aiomysql receives the raw
    encoded string and authentication fails with "Access denied ...
    using password: YES".
    """
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username) if parsed.username else "root",
        "password": unquote(parsed.password) if parsed.password else "",
        "db": parsed.path.lstrip("/") if parsed.path else None,
    }


async def test_connection(url: str) -> tuple[bool, str | None]:
    """
    Test MySQL database connection.

    Args:
        url: MySQL connection URL (mysql://user:password@host:port/database)

    Returns:
        Tuple of (success, error_message)
    """
    try:
        params = _parse_url(url)
        conn = await aiomysql.connect(**params)
        await conn.ensure_closed()
        return True, None
    except Exception as e:
        return False, str(e)


async def get_connection_pool(
    name: str, url: str, min_size: int = 1, max_size: int = 5
) -> aiomysql.Pool:
    """
    Get or create aiomysql connection pool for a database.

    Args:
        name: Database connection name
        url: MySQL connection URL
        min_size: Minimum pool size
        max_size: Maximum pool size

    Returns:
        aiomysql connection pool
    """
    # Re-create the pool if the URL changed so updated credentials are used.
    existing = _connection_pools.get(name)
    if existing is not None and getattr(existing, "_source_url", None) == url:
        return existing

    if existing is not None:
        # URL changed - close the old pool before creating a new one.
        existing.close()
        try:
            await existing.wait_closed()
        except Exception:
            pass

    params = _parse_url(url)
    pool = await aiomysql.create_pool(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        db=params["db"],
        minsize=min_size,
        maxsize=max_size,
        autocommit=True,
    )
    # Remember the URL so we can detect credential changes on subsequent calls.
    pool._source_url = url  # type: ignore[attr-defined]
    _connection_pools[name] = pool
    return pool


async def close_connection_pool(name: str) -> None:
    """
    Close connection pool for a database.

    Args:
        name: Database connection name
    """
    if name in _connection_pools:
        pool = _connection_pools.pop(name)
        pool.close()
        await pool.wait_closed()


async def close_all_connection_pools() -> None:
    """Close all connection pools."""
    for name in list(_connection_pools.keys()):
        await close_connection_pool(name)
