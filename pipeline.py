"""D1 fetch + dbt ビルド + メタデータ生成パイプライン。"""

import json
import os
import sqlite3
import urllib.request
from pathlib import Path

from dbt.cli.main import dbtRunner
from fdl import DIST_DIR


def main():
    _ingest()

    # dbt ビルド (invoke ごとに新しいインスタンスを使い、deps 後のマクロ解決を確実にする)
    result = dbtRunner().invoke(["deps"])
    if not result.success:
        raise SystemExit("dbt deps failed")

    result = dbtRunner().invoke(["run"])
    if not result.success:
        raise SystemExit("dbt run failed")

    result = dbtRunner().invoke(["docs", "generate"])
    if not result.success:
        raise SystemExit("dbt docs generate failed")


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

    db_path = DIST_DIR / "d1.db"
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

