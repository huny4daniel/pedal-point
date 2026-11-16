"""관리자 기능: 대여소·자전거 관리, 내역 검색, 회원 관리, 통계."""
from datetime import date, timedelta

import rules
from db import BusinessError, fetch_all, fetch_one, transaction


# ---------------------------------------------------------------- 로그인
def login_staff() -> list[dict]:
    """로그인 가능한 관리자 (재직 중)."""
    return fetch_all(
        """
        SELECT a.staff_id, a.staff_name, s.station_name
        FROM adminstaff a
        LEFT JOIN station s ON s.station_id = a.staff_station_id
        WHERE a.staff_is_active = 1
        ORDER BY a.staff_id
        """
    )


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
               SUM(b.bicycle_status = 'AVAILABLE')   AS available_count,
               SUM(b.bicycle_status = 'MAINTENANCE') AS maintenance_count,
               COUNT(b.bicycle_id)                   AS docked_count
        FROM station s
        LEFT JOIN bicycle b ON b.bicycle_station_id = s.station_id
        GROUP BY s.station_id
        ORDER BY s.station_region, s.station_name
        """
    )


def _station_params(data: dict) -> tuple:
    if not data["name"].strip() or not data["region"].strip() or not data["address"].strip():
        raise BusinessError("이름, 지역명, 주소는 필수입니다.")
    if data["totaldocks"] < 0:
        raise BusinessError("총 거치대 수는 0 이상이어야 합니다.")
    return (
        data["name"].strip(), data["region"].strip(), data["address"].strip(),
        data["contact"].strip() or None, data["latitude"], data["longitude"],
        data["totaldocks"], data["status"],
    )


def create_station(data: dict) -> int:
    with transaction() as cur:
        cur.execute(
            "INSERT INTO station (station_name, station_region, station_address, "
            "  station_contactnumber, station_latitude, station_longitude, "
            "  station_totaldocks, station_status, station_created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())",
            _station_params(data),
        )
        return cur.lastrowid


def update_station(station_id: int, data: dict) -> None:
    with transaction() as cur:
        cur.execute(
            "UPDATE station SET station_name = %s, station_region = %s, station_address = %s, "
            "  station_contactnumber = %s, station_latitude = %s, station_longitude = %s, "
            "  station_totaldocks = %s, station_status = %s "
            "WHERE station_id = %s",
            (*_station_params(data), station_id),
        )


# ---------------------------------------------------------------- 자전거
def all_bicycles(station_id: int | None = None, status: str | None = None) -> list[dict]:
    sql = """
        SELECT b.bicycle_id, b.bicycle_status, b.bicycle_registered_at,
               b.bicycle_station_id, s.station_name
        FROM bicycle b
        LEFT JOIN station s ON s.station_id = b.bicycle_station_id
        WHERE 1 = 1
    """
    params = []
    if station_id:
        sql += " AND b.bicycle_station_id = %s"
        params.append(station_id)
    if status:
        sql += " AND b.bicycle_status = %s"
        params.append(status)
    sql += " ORDER BY b.bicycle_id"
    return fetch_all(sql, params)


def register_bicycle(station_id: int, status: str) -> int:
    if status not in ("AVAILABLE", "MAINTENANCE"):
        raise BusinessError("등록 상태는 대여가능 또는 정비중만 선택할 수 있습니다.")
    with transaction() as cur:
        cur.execute(
            "INSERT INTO bicycle (bicycle_status, bicycle_registered_at, bicycle_station_id) "
            "VALUES (%s, NOW(), %s)",
            (status, station_id),
        )
        return cur.lastrowid


def change_bicycle_status(bicycle_id: int, new_status: str) -> None:
    """대여가능 ↔ 정비중 전환. 대여 중인 자전거는 바꿀 수 없다."""
    if new_status not in ("AVAILABLE", "MAINTENANCE"):
        raise BusinessError("대여가능 또는 정비중으로만 바꿀 수 있습니다.")
    with transaction() as cur:
        cur.execute(
            "SELECT bicycle_status FROM bicycle WHERE bicycle_id = %s FOR UPDATE", (bicycle_id,)
        )
        bike = cur.fetchone()
        if not bike:
            raise BusinessError("자전거를 찾을 수 없습니다.")
        if bike["bicycle_status"] == "RENTED":
            raise BusinessError("대여 중인 자전거는 상태를 바꿀 수 없습니다.")
        cur.execute(
            "UPDATE bicycle SET bicycle_status = %s WHERE bicycle_id = %s",
            (new_status, bicycle_id),
        )


# ---------------------------------------------------------------- 내역 검색
def _period(start: date, end: date) -> tuple:
    return start, end + timedelta(days=1)


def search_rentals(start: date, end: date, user_id=None, station_id=None) -> list[dict]:
    sql = """
        SELECT r.rental_id, r.rental_start_time, r.rental_end_time, r.rental_status,
               r.rental_distance, u.user_id, u.user_name,
               ss.station_name AS start_station, rs.station_name AS return_station,
               r.rental_bicycle_id
        FROM rental r
        JOIN `user` u    ON u.user_id = r.rental_user_id
        JOIN station ss  ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        WHERE r.rental_start_time >= %s AND r.rental_start_time < %s
    """
    params = list(_period(start, end))
    if user_id:
        sql += " AND r.rental_user_id = %s"
        params.append(user_id)
    if station_id:
        sql += " AND (r.start_station_id = %s OR r.return_station_id = %s)"
        params += [station_id, station_id]
    sql += " ORDER BY r.rental_start_time DESC"
    return fetch_all(sql, params)


def search_payments(start: date, end: date, user_id=None, station_id=None) -> list[dict]:
    sql = """
        SELECT p.payment_id, p.payment_at, p.payment_rental_id, u.user_id, u.user_name,
               ss.station_name AS start_station, rs.station_name AS return_station,
               p.payment_amount, p.payment_discount, p.payment_final_amount, p.payment_method
        FROM payment p
        JOIN rental r    ON r.rental_id = p.payment_rental_id
        JOIN `user` u    ON u.user_id = r.rental_user_id
        JOIN station ss  ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        WHERE p.payment_at >= %s AND p.payment_at < %s
    """
    params = list(_period(start, end))
    if user_id:
        sql += " AND r.rental_user_id = %s"
        params.append(user_id)
    if station_id:
        sql += " AND (r.start_station_id = %s OR r.return_station_id = %s)"
        params += [station_id, station_id]
    sql += " ORDER BY p.payment_at DESC"
    return fetch_all(sql, params)


def search_mileage(start: date, end: date, user_id=None, station_id=None) -> list[dict]:
    # 적립은 rental, 사용은 payment → rental 을 거쳐 대여소를 찾는다
    sql = """
        SELECT m.mileage_id, m.mileage_created_at, m.mileage_type, m.mileage_point,
               u.user_id, u.user_name, m.mileage_rental_id, m.mileage_payment_id,
               COALESCE(r.rental_id, pr.rental_id) AS related_rental_id
        FROM mileage m
        JOIN `user` u ON u.user_id = m.mileage_user_id
        LEFT JOIN rental r   ON r.rental_id = m.mileage_rental_id
        LEFT JOIN payment p  ON p.payment_id = m.mileage_payment_id
        LEFT JOIN rental pr  ON pr.rental_id = p.payment_rental_id
        WHERE m.mileage_created_at >= %s AND m.mileage_created_at < %s
    """
    params = list(_period(start, end))
    if user_id:
        sql += " AND m.mileage_user_id = %s"
        params.append(user_id)
    if station_id:
        sql += (" AND (COALESCE(r.start_station_id, pr.start_station_id) = %s"
                "      OR COALESCE(r.return_station_id, pr.return_station_id) = %s)")
        params += [station_id, station_id]
    sql += " ORDER BY m.mileage_created_at DESC, m.mileage_id DESC"
    return fetch_all(sql, params)


# ---------------------------------------------------------------- 회원
def all_users() -> list[dict]:
    return fetch_all(
        """
        SELECT u.user_id, u.user_name, u.user_birth_date, u.user_phone, u.user_address,
               u.user_status, u.user_created_at, v.balance
        FROM `user` u
        JOIN v_user_mileage_balance v ON v.user_id = u.user_id
        ORDER BY u.user_id
        """
    )


def change_user_status(user_id: int, new_status: str) -> None:
    if new_status not in ("ACTIVE", "SUSPENDED", "WITHDRAWN"):
        raise BusinessError("올바르지 않은 회원 상태입니다.")
    with transaction() as cur:
        cur.execute("UPDATE `user` SET user_status = %s WHERE user_id = %s",
                    (new_status, user_id))
        if cur.rowcount == 0 and not _user_exists(cur, user_id):
            raise BusinessError("회원을 찾을 수 없습니다.")


def _user_exists(cur, user_id: int) -> bool:
    cur.execute("SELECT 1 FROM `user` WHERE user_id = %s", (user_id,))
    return cur.fetchone() is not None


# ---------------------------------------------------------------- 통계
def statistics() -> dict:
    rental = fetch_one(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(rental_distance), 0) AS total_km "
        "FROM rental WHERE rental_status = 'RETURNED'"
    )
    mileage = fetch_one(
        "SELECT COALESCE(SUM(total_earned), 0) AS earned, COALESCE(SUM(total_used), 0) AS used, "
        "       COALESCE(SUM(balance), 0) AS balance FROM v_user_mileage_balance"
    )
    return {
        "rental_count": rental["cnt"],
        "total_km": rental["total_km"],
        "carbon_g": rules.carbon_saved_g(rental["total_km"]),
        "earned": int(mileage["earned"]),
        "used": int(mileage["used"]),
        "balance": int(mileage["balance"]),
    }


def user_statistics() -> list[dict]:
    rows = fetch_all(
        """
        SELECT u.user_id, u.user_name,
               COUNT(r.rental_id) AS rental_count,
               COALESCE(SUM(r.rental_distance), 0) AS total_km,
               v.total_earned, v.total_used, v.balance
        FROM `user` u
        JOIN v_user_mileage_balance v ON v.user_id = u.user_id
        LEFT JOIN rental r ON r.rental_user_id = u.user_id AND r.rental_status = 'RETURNED'
        GROUP BY u.user_id, u.user_name, v.total_earned, v.total_used, v.balance
        ORDER BY total_km DESC
        """
    )
    for r in rows:
        r["carbon_g"] = rules.carbon_saved_g(r["total_km"])
    return rows
