"""D1 fetch + dbt build + snapshot pipeline.

Snapshot must run in the SAME Python process as dbt build — see
dataset-shared/README.md for the constraint detail.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

from dbt.cli.main import dbtRunner

CACHE_DIR = Path(".fdl")  # kept as .fdl/ to preserve dbt model references

SHARED_SCRIPTS = Path(__file__).resolve().parent / "shared" / "scripts"
_spec = importlib.util.spec_from_file_location(
    "snapshot_to_r2", SHARED_SCRIPTS / "snapshot-to-r2.py"
)
assert _spec and _spec.loader
snapshot_to_r2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(snapshot_to_r2)


def main() -> None:
    target = os.environ.get("DBT_TARGET", sys.argv[1] if len(sys.argv) > 1 else "default")

    _ingest()

    dbt = dbtRunner()
    for cmd in (
        ["deps"],
        ["run", "--target", target],
        ["docs", "generate", "--target", target],
    ):
        result = dbt.invoke(cmd)
        if not result.success:
            raise SystemExit(f"dbt {' '.join(cmd)} failed")

    snapshot_to_r2.run(target)


def _ingest() -> None:
    """Cloudflare D1 から記事メタデータを取得し SQLite に保存する。"""
    account_id = os.environ["CF_ACCOUNT_ID"]
    api_token = os.environ["CF_API_TOKEN"]
    database_id = os.environ["CF_D1_DATABASE_ID"]

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
    sql = "SELECT slug, title, description, date, datasources, tags FROM articles ORDER BY date DESC"
    payload = json.dumps({"sql": sql}).encode()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())

    if not body.get("success"):
        raise RuntimeError(f"D1 query failed: {body.get('errors', [])}")

    rows = body["result"][0]["results"]

    CACHE_DIR.mkdir(exist_ok=True)
    db_path = CACHE_DIR / "d1.db"
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS articles")
    conn.execute("""
        CREATE TABLE articles (
            slug TEXT, title TEXT, description TEXT,
            date TEXT, datasources TEXT, tags TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?)",
        [(r["slug"], r["title"], r["description"], r["date"], r["datasources"], r["tags"]) for r in rows],
    )
    conn.commit()
    conn.close()
    print(f"  D1 → {db_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
