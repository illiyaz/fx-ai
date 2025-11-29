from __future__ import annotations
import os
from typing import Any, Iterable
from urllib.parse import urlparse
import pandas as pd
import clickhouse_connect

CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "fxai")

def _host_port_from_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    # default ClickHouse HTTP port
    port = parsed.port or (443 if parsed.scheme == "https" else 8123)
    return host, port

def get_client():
    host, port = _host_port_from_url(CLICKHOUSE_URL)
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB,
    )

def exec_sql(sql: str) -> None:
    cli = get_client()
    cli.command(sql)

def query_df(sql: str) -> pd.DataFrame:
    cli = get_client()
    return cli.query_df(sql)

def insert_rows(table: str, rows: Iterable[tuple[Any, ...]], columns: list[str]) -> None:
    cli = get_client()
    cli.insert(table, rows, column_names=columns)

def insert_df(table: str, df: pd.DataFrame) -> None:
    cli = get_client()
    cli.insert_df(table, df)