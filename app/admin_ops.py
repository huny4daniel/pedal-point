"""관리자 기능: 대여소·자전거 관리, 내역 조회, 회원 관리, 통계."""
from datetime import date, timedelta

import rules
from db import BusinessError, fetch_all, fetch_one, transaction


# ---------------------------------------------------------------- 로그인
def authenticate_staff(login_id: str, password: str) -> dict:
    """아이디·비밀번호로 관리자 인증. 성공하면 adminstaff 행, 실패하면 BusinessError."""
    row = fetch_one(
        "SELECT staff_id, staff_password, staff_is_active FROM adminstaff WHERE staff_login_id = %s",
        (login_id.strip(),),
    )
    if not row or not rules.check_password(password, row["staff_password"]):
        raise BusinessError("아이디 또는 비밀번호가 올바르지 않습니다.")
    if not row["staff_is_active"]:
        raise BusinessError("퇴사 처리된 계정입니다.")
    return row


def get_staff(staff_id: int) -> dict | None:
    return fetch_one(
        """
        SELECT a.*, s.station_name
        FROM adminstaff a
        LEFT JOIN station s ON s.station_id = a.staff_station_id
        WHERE a.staff_id = %s
        """,
        (staff_id,),
    )


# ---------------------------------------------------------------- 대여소
def all_stations() -> list[dict]:
    return fetch_all(
        """
        SELECT s.*,
               COALESCE(SUM(b.bicycle_status = 'AVAILABLE'), 0)   AS available_count,
               COALESCE(SUM(b.bicycle_status = 'MAINTENANCE'), 0) AS maintenance_count,
               COUNT(b.bicycle_id)                                AS docked_count
        FROM station s
        LEFT JOIN bicycle b ON b.bicycle_station_id = s.station_id
        GROUP BY s.station_id
        ORDER BY s.station_name
        """
    )


def _station_params(data: dict) -> tuple:
    name, address = data["name"].strip(), data["address"].strip()
    if not name or len(name) > 100:
        raise BusinessError("대여소 이름을 100자 이내로 입력해 주세요.")
    if not address or len(address) > 255:
        raise BusinessError("주소를 255자 이내로 입력해 주세요.")
    if data["totaldocks"] < 1:
        raise BusinessError("거치대 수는 1 이상이어야 합니다.")
    if data["status"] not in ("ACTIVE", "INACTIVE"):
        raise BusinessError("올바르지 않은 운영 상태입니다.")
    return name, address, data["contact"].strip() or None, data["totaldocks"], data["status"]


def create_station(data: dict) -> int:
    params = _station_params(data)
    with transaction() as cur:
        cur.execute(
            "INSERT INTO station (station_name, station_address, station_contactnumber, "
            "                     station_totaldocks, station_status) "
            "VALUES (%s, %s, %s, %s, %s)",
            params,
        )
        return cur.lastrowid


def update_station(station_id: int, data: dict) -> None:
    params = _station_params(data)
    with transaction() as cur:
        cur.execute("SELECT station_id FROM station WHERE station_id = %s FOR UPDATE", (station_id,))
        if not cur.fetchone():
            raise BusinessError("대여소를 찾을 수 없습니다.")
        cur.execute("SELECT COUNT(*) AS cnt FROM bicycle WHERE bicycle_station_id = %s", (station_id,))
        if params[3] < cur.fetchone()["cnt"]:
            raise BusinessError("현재 보관 중인 자전거보다 적게 설정할 수 없습니다.")
        cur.execute(
            "UPDATE station SET station_name = %s, station_address = %s, station_contactnumber = %s, "
            "       station_totaldocks = %s, station_status = %s "
            "WHERE station_id = %s",
            (*params, station_id),
        )


# ---------------------------------------------------------------- 자전거
def all_bicycles(station_id: int | None = None, status: str | None = None) -> list[dict]:
    return fetch_all(
        """
        SELECT b.bicycle_id, b.bicycle_status, b.bicycle_registered_at,
               b.bicycle_station_id, s.station_name
        FROM bicycle b
        LEFT JOIN station s ON s.station_id = b.bicycle_station_id
        WHERE (%s IS NULL OR b.bicycle_station_id = %s)
          AND (%s IS NULL OR b.bicycle_status = %s)
        ORDER BY b.bicycle_id
        """,
        (station_id, station_id, status, status),
    )


def register_bicycle(station_id: int, status: str) -> int:
    if status not in ("AVAILABLE", "MAINTENANCE"):
        raise BusinessError("등록 상태는 대여가능 또는 정비중만 선택할 수 있습니다.")
    with transaction() as cur:
        cur.execute("SELECT station_totaldocks FROM station WHERE station_id = %s FOR UPDATE",
                    (station_id,))
        station = cur.fetchone()
        if not station:
            raise BusinessError("대여소를 찾을 수 없습니다.")
        cur.execute("SELECT COUNT(*) AS cnt FROM bicycle WHERE bicycle_station_id = %s", (station_id,))
        if station["station_totaldocks"] - cur.fetchone()["cnt"] <= 0:
            raise BusinessError("빈 거치대가 없습니다. 다른 대여소를 선택하세요.")
        cur.execute(
            "INSERT INTO bicycle (bicycle_status, bicycle_station_id) VALUES (%s, %s)",
            (status, station_id),
        )
        return cur.lastrowid


def change_bicycle_status(bicycle_id: int, new_status: str) -> None:
    """대여가능 ↔ 정비중 전환. 대여 중인 자전거는 바꿀 수 없다."""
    if new_status not in ("AVAILABLE", "MAINTENANCE"):
        raise BusinessError("대여가능 또는 정비중으로만 바꿀 수 있습니다.")
    with transaction() as cur:
        cur.execute("SELECT bicycle_status FROM bicycle WHERE bicycle_id = %s FOR UPDATE", (bicycle_id,))
        bike = cur.fetchone()
        if not bike:
            raise BusinessError("자전거를 찾을 수 없습니다.")
        if bike["bicycle_status"] == "RENTED":
            raise BusinessError("대여 중인 자전거는 상태를 바꿀 수 없습니다.")
        cur.execute("UPDATE bicycle SET bicycle_status = %s WHERE bicycle_id = %s",
                    (new_status, bicycle_id))


# ---------------------------------------------------------------- 내역 조회
def _filters(time_col: str, start: date, end: date, member: str, station_id) -> tuple[str, list]:
    """기간(>= 시작일, < 종료일+1일)과 입력·선택한 필터만 WHERE에 붙인다.

    member: 회원 아이디 또는 이름 일부 (빈 문자열이면 전체)
    """
    sql = f" WHERE {time_col} >= %s AND {time_col} < %s"
    params: list = [start, end + timedelta(days=1)]
    if member:
        sql += " AND (u.user_login_id LIKE %s OR u.user_name LIKE %s)"
        params += [f"%{member}%", f"%{member}%"]
    if station_id:
        sql += " AND (r.start_station_id = %s OR r.return_station_id = %s)"
        params += [station_id, station_id]
    return sql, params


def search_rentals(start: date, end: date, member: str = "", station_id=None) -> list[dict]:
    where, params = _filters("r.rental_start_time", start, end, member.strip(), station_id)
    return fetch_all(
        """
        SELECT r.rental_id, r.rental_start_time, r.rental_end_time, r.rental_distance,
               r.rental_bicycle_id, u.user_login_id, u.user_name, p.payment_id,
               ss.station_name AS start_station, rs.station_name AS return_station
        FROM rental r
        JOIN `user` u ON u.user_id = r.rental_user_id
        JOIN station ss ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        LEFT JOIN payment p ON p.payment_rental_id = r.rental_id
        """ + where + " ORDER BY r.rental_start_time DESC",
        params,
    )


def search_payments(start: date, end: date, member: str = "", station_id=None) -> list[dict]:
    where, params = _filters("p.payment_at", start, end, member.strip(), station_id)
    return fetch_all(
        """
        SELECT p.payment_id, p.payment_at, p.payment_rental_id, u.user_login_id, u.user_name,
               ss.station_name AS start_station, rs.station_name AS return_station,
               p.payment_amount, p.payment_discount, p.payment_final_amount, p.payment_method
        FROM payment p
        JOIN rental r ON r.rental_id = p.payment_rental_id
        JOIN `user` u ON u.user_id = r.rental_user_id
        JOIN station ss ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        """ + where + " ORDER BY p.payment_at DESC",
        params,
    )


def search_mileage(start: date, end: date, member: str = "", station_id=None) -> list[dict]:
    """적립(mileage) + 사용(payment_discount > 0). point는 사용이면 음수."""
    w1, p1 = _filters("m.mileage_created_at", start, end, member.strip(), station_id)
    w2, p2 = _filters("p.payment_at", start, end, member.strip(), station_id)
    return fetch_all(
        """
        SELECT m.mileage_created_at AS at, '적립' AS kind, m.mileage_point AS point,
               r.rental_id, u.user_login_id, u.user_name
        FROM mileage m
        JOIN rental r ON r.rental_id = m.mileage_rental_id
        JOIN `user` u ON u.user_id = r.rental_user_id
        """ + w1 + """
        UNION ALL
        SELECT p.payment_at, '사용', -p.payment_discount, r.rental_id, u.user_login_id, u.user_name
        FROM payment p
        JOIN rental r ON r.rental_id = p.payment_rental_id
        JOIN `user` u ON u.user_id = r.rental_user_id
        """ + w2 + """ AND p.payment_discount > 0
        ORDER BY at DESC, rental_id DESC
        """,
        p1 + p2,
    )


# ---------------------------------------------------------------- 회원
def all_users() -> list[dict]:
    return fetch_all(
        """
        SELECT u.user_id, u.user_login_id, u.user_name, u.user_phone, u.user_mileage,
               u.user_status, u.user_created_at,
               EXISTS (SELECT 1 FROM rental r
                        WHERE r.rental_user_id = u.user_id AND r.rental_end_time IS NULL) AS renting
        FROM `user` u
        ORDER BY u.user_id
        """
    )


def update_users(changes: list[dict]) -> int:
    """표에서 고친 회원 정보(이름·연락처·상태)를 한 트랜잭션으로 저장한다. 바뀐 회원 수 반환.

    changes: [{"user_id", "user_login_id", "user_name", "user_phone", "user_status"}]
    한 명이라도 규칙에 어긋나면 전체를 저장하지 않는다(rollback).
    """
    phone_re = rules.PHONE_RE
    with transaction() as cur:
        for c in changes:
            who = c["user_login_id"]
            name, phone, status = str(c["user_name"] or "").strip(), str(c["user_phone"] or "").strip(), c["user_status"]
            if not 1 <= len(name) <= 50:
                raise BusinessError(f"{who}: 이름을 1~50자로 입력해 주세요.")
            if not phone_re.match(phone):
                raise BusinessError(f"{who}: 연락처는 010-0000-0000 형식이어야 합니다.")
            if status not in ("ACTIVE", "SUSPENDED", "WITHDRAWN"):
                raise BusinessError(f"{who}: 올바르지 않은 회원 상태입니다.")
            cur.execute("SELECT user_status FROM `user` WHERE user_id = %s FOR UPDATE", (c["user_id"],))
            row = cur.fetchone()
            if not row:
                raise BusinessError(f"{who}: 회원을 찾을 수 없습니다.")
            if status != "ACTIVE" and status != row["user_status"]:
                cur.execute("SELECT 1 FROM rental WHERE rental_user_id = %s AND rental_end_time IS NULL",
                            (c["user_id"],))
                if cur.fetchone():
                    raise BusinessError(f"{who}: 대여 중인 회원입니다. 반납 후 변경하세요.")
            cur.execute(
                "SELECT user_login_id FROM `user` WHERE user_phone = %s AND user_id <> %s", (phone, c["user_id"])
            )
            if dup := cur.fetchone():
                raise BusinessError(f"{who}: 연락처 {phone}는 {dup['user_login_id']} 회원이 이미 쓰고 있습니다.")
            cur.execute(
                "UPDATE `user` SET user_name = %s, user_phone = %s, user_status = %s WHERE user_id = %s",
                (name, phone, status, c["user_id"]),
            )
    return len(changes)


# ---------------------------------------------------------------- 통계
def statistics() -> dict:
    row = fetch_one(
        """
        SELECT
          (SELECT COUNT(*) FROM rental WHERE rental_end_time IS NOT NULL)                         AS rental_count,
          (SELECT COALESCE(SUM(rental_distance), 0) FROM rental WHERE rental_end_time IS NOT NULL) AS total_km,
          (SELECT COALESCE(SUM(mileage_point), 0) FROM mileage)                                    AS total_earned,
          (SELECT COALESCE(SUM(payment_discount), 0) FROM payment)                                 AS total_used,
          (SELECT COALESCE(SUM(user_mileage), 0) FROM `user`)                                      AS total_balance,
          (SELECT COALESCE(SUM(payment_final_amount), 0) FROM payment)                             AS total_paid
        """
    )
    return {**row, "carbon_g": rules.carbon_saved_g(row["total_km"])}


def user_statistics() -> list[dict]:
    rows = fetch_all(
        """
        SELECT u.user_id, u.user_login_id, u.user_name, u.user_mileage,
               COUNT(r.rental_id) AS rental_count, COALESCE(SUM(r.rental_distance), 0) AS total_km
        FROM `user` u
        LEFT JOIN rental r ON r.rental_user_id = u.user_id AND r.rental_end_time IS NOT NULL
        GROUP BY u.user_id
        ORDER BY total_km DESC
        """
    )
    for r in rows:
        r["carbon_g"] = rules.carbon_saved_g(r["total_km"])
    return rows
