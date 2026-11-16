"""pymysql 연결과 트랜잭션 헬퍼."""
from contextlib import contextmanager

import pymysql
import streamlit as st


class BusinessError(Exception):
    """업무 규칙 위반 (화면에 그대로 보여줄 메시지)."""


def _config() -> dict:
    try:
        cfg = dict(st.secrets["mysql"])
    except Exception:
        cfg = {}
    return {
        "host": cfg.get("host", "localhost"),
        "port": int(cfg.get("port", 3306)),
        "user": cfg.get("user", "root"),
        "password": cfg.get("password", ""),
        "database": cfg.get("database", "padal"),
    }


def connect():
    return pymysql.connect(
        **_config(),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def fetch_all(sql: str, params=None) -> list[dict]:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
    finally:
        conn.close()


def fetch_one(sql: str, params=None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


@contextmanager
def transaction():
    """블록 전체를 한 트랜잭션으로 실행한다. 예외가 나면 rollback."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
