#!/usr/bin/env python3
"""Run the named queries in queries.sql against Rfam's public MySQL database.

Usage:
    python run_queries.py                       # run all queries
    python run_queries.py q1_acacia_types       # run selected queries
"""

from __future__ import annotations

import re
import socket
import sys
import time
from pathlib import Path

import pymysql

RFAM = {
    "host": "mysql-rfam-public.ebi.ac.uk",
    "port": 4497,
    "user": "rfamro",       # public read-only account, no password
    "database": "Rfam",
    "connect_timeout": 15,
    "read_timeout": 900,    # q3 aggregates the large full_region table
}
KEEPALIVE_SECONDS = 30      # probe interval while a long query is running
SQL_FILE = Path(__file__).with_name("queries.sql")
NAME_RE = re.compile(r"^--\s*name:\s*(\w+)\s*$", re.MULTILINE)


def load_queries(path: Path) -> dict[str, str]:
    """Split the file on '-- name: <id>' markers -> {id: sql}."""
    parts = NAME_RE.split(path.read_text(encoding="utf-8"))
    # parts = [header, name1, body1, name2, body2, ...]
    return {name: body.strip().rstrip(";") for name, body in zip(parts[1::2], parts[2::2])}


def print_table(columns: list[str], rows: tuple) -> None:
    cells = [columns] + [["NULL" if v is None else str(v) for v in row] for row in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(columns))]
    for i, row in enumerate(cells):
        print(" | ".join(v.ljust(w) for v, w in zip(row, widths)))
        if i == 0:
            print("-+-".join("-" * w for w in widths))


def enable_keepalive(conn: pymysql.connections.Connection) -> None:
    """Send TCP keepalive probes while the server is busy computing a result.

    The connection is silent during a long query, and firewalls/NAT on the
    path may drop idle connections ("Connection reset by peer").
    PyMySQL has no public option for this, so set it on its socket.
    """
    sock = getattr(conn, "_sock", None)
    if sock is None:
        return
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    for option, value in (("TCP_KEEPIDLE", KEEPALIVE_SECONDS),
                          ("TCP_KEEPINTVL", KEEPALIVE_SECONDS),
                          ("TCP_KEEPCNT", 5)):
        if hasattr(socket, option):          # Linux; macOS/Windows differ
            sock.setsockopt(socket.IPPROTO_TCP, getattr(socket, option), value)


def run_query(name: str, sql: str) -> bool:
    """Run one query on its own connection; return True on success."""
    print(f"\n== {name} ==", flush=True)
    start = time.perf_counter()
    try:
        conn = pymysql.connect(**RFAM)
    except pymysql.MySQLError as exc:
        print(f"error: cannot connect to Rfam ({exc}). Is outbound TCP port 4497 allowed?",
              file=sys.stderr)
        return False

    try:
        enable_keepalive(conn)
        with conn.cursor() as cur:
            cur.execute(sql)
            print_table([d[0] for d in cur.description], cur.fetchall())
            print(f"({cur.rowcount} row(s), {time.perf_counter() - start:.1f}s)")
        return True
    except pymysql.MySQLError as exc:
        print(f"error: {name} failed after {time.perf_counter() - start:.0f}s: {exc}",
              file=sys.stderr)
        return False
    finally:
        if conn.open:            # a dropped connection is already closed
            conn.close()


def main(selected: list[str]) -> int:
    queries = load_queries(SQL_FILE)
    unknown = set(selected) - queries.keys()
    if unknown:
        print(f"unknown query: {', '.join(sorted(unknown))}; choose from {', '.join(queries)}",
              file=sys.stderr)
        return 2

    # Each query gets its own connection, so one failure doesn't stop the rest.
    results = [run_query(name, queries[name]) for name in selected or queries]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
