"""pymysql 연결과 트랜잭션 헬퍼.

업무 규칙 위반은 BusinessError, 그 밖의 DB 오류는 DBError(BusinessError의 하위 클래스)로 바꿔서
화면이 같은 방식(st.error)으로 안내 문구를 보여줄 수 있게 한다. 원래 오류는 서버 콘솔에 남긴다.
"""
import logging
from contextlib import contextmanager

import pymysql
import streamlit as st

log = logging.getLogger("pedalpoint.db")
DB_ERROR_MESSAGE = "처리 중 오류가 발생했습니다. 다시 시도해 주세요."


class BusinessError(Exception):
    """업무 규칙 위반 (화면에 그대로 보여줄 메시지)."""


class DBError(BusinessError):
    """업무 규칙이 아닌 DB 오류. errno는 MySQL 오류 번호(예: 1062 중복)."""

    def __init__(self, cause: pymysql.MySQLError):
        super().__init__(DB_ERROR_MESSAGE)
        self.errno = cause.args[0] if cause.args else None


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
        "database": cfg.get("database", "pedal"),
    }


def connect():
    return pymysql.connect(
        **_config(),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def fetch_all(sql: str, params=None) -> list[dict]:
    try:
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
        finally:
            conn.close()
    except pymysql.MySQLError as e:
        log.exception("DB 조회 오류")
        raise DBError(e) from e


def fetch_one(sql: str, params=None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


@contextmanager
def transaction():
    """블록 전체를 한 트랜잭션으로 실행한다. 예외가 나면 rollback."""
    try:
        conn = connect()
    except pymysql.MySQLError as e:
        log.exception("DB 접속 오류")
        raise DBError(e) from e
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except pymysql.MySQLError as e:
        conn.rollback()
        if e.args and e.args[0] == 1062:  # 중복 키는 화면에서 안내하는 정상 흐름
            log.info("중복 키 (rollback): %s", e)
        else:
            log.exception("DB 처리 오류 (rollback)")
        raise DBError(e) from e
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
