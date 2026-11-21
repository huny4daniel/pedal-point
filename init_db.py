"""pedal DB를 sql/GreenRide_DDL.sql + sql/GreenRide_DML.sql로 만든다 (mysql 클라이언트 없이 pymysql로 실행).

    python init_db.py           pedal DB가 없을 때만 생성
    python init_db.py --reset   기존 pedal DB를 지우고 새로 생성

DB 이름(pedal)은 DDL 안에 정해져 있다. 접속 정보는 .streamlit/secrets.toml의 [mysql]을 쓴다.
"""
import sys
import tomllib
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT

ROOT = Path(__file__).resolve().parent
DB_NAME = "pedal"
SQL_FILES = [ROOT / "sql" / "GreenRide_DDL.sql", ROOT / "sql" / "GreenRide_DML.sql"]


def load_config() -> dict:
    secrets = ROOT / ".streamlit" / "secrets.toml"
    cfg = tomllib.loads(secrets.read_text(encoding="utf-8")).get("mysql", {}) if secrets.exists() else {}
    return {
        "host": cfg.get("host", "localhost"),
        "port": int(cfg.get("port", 3306)),
        "user": cfg.get("user", "root"),
        "password": cfg.get("password", ""),
    }


def main() -> int:
    reset = "--reset" in sys.argv
    try:
        conn = pymysql.connect(**load_config(), charset="utf8mb4", client_flag=CLIENT.MULTI_STATEMENTS)
    except pymysql.MySQLError as e:
        print(f"[오류] MySQL 접속 실패: {e}")
        print("  MySQL 서버가 켜져 있는지, .streamlit/secrets.toml의 접속 정보가 맞는지 확인하세요.")
        return 1

    try:
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES LIKE %s", (DB_NAME,))
            if cur.fetchone() and not reset:
                print(f"[확인] {DB_NAME} DB가 이미 있습니다. (초기화하려면 --reset)")
                return 0
            for path in SQL_FILES:
                print(f"[실행] {path.relative_to(ROOT)}")
                cur.execute(path.read_text(encoding="utf-8"))
                while cur.nextset():  # DML 끝의 확인용 SELECT 결과는 버린다
                    pass
        conn.commit()
        print(f"[완료] {DB_NAME} DB를 만들었습니다.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
