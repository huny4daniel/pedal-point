"""이용자 기능: 대여소 검색, 대여, 반납·결제, 내역 조회."""
from decimal import Decimal

import rules
from db import BusinessError, fetch_all, fetch_one, transaction


# ---------------------------------------------------------------- 로그인
def login_users() -> list[dict]:
    """로그인 가능한 이용자 (탈퇴 회원 제외)."""
    return fetch_all(
        "SELECT user_id, user_name, user_status FROM `user` "
        "WHERE user_status <> 'WITHDRAWN' ORDER BY user_id"
    )


def get_user(user_id: int) -> dict | None:
    return fetch_one("SELECT * FROM `user` WHERE user_id = %s", (user_id,))


# ---------------------------------------------------------------- 검색
def regions() -> list[str]:
    rows = fetch_all(
        "SELECT DISTINCT station_region FROM station "
        "WHERE station_status = 'ACTIVE' ORDER BY station_region"
    )
    return [r["station_region"] for r in rows]


def search_stations(region: str | None, keyword: str) -> list[dict]:
    """운영 중인 대여소를 지역·이름으로 검색하고 대여 가능 자전거 수를 함께 보여준다."""
    sql = """
        SELECT s.station_id, s.station_name, s.station_region, s.station_address,
               s.station_contactnumber, s.station_totaldocks,
               COUNT(b.bicycle_id) AS available_count
        FROM station s
        LEFT JOIN bicycle b
               ON b.bicycle_station_id = s.station_id AND b.bicycle_status = 'AVAILABLE'
        WHERE s.station_status = 'ACTIVE'
    """
    params = []
    if region:
        sql += " AND s.station_region = %s"
        params.append(region)
    if keyword:
        sql += " AND s.station_name LIKE %s"
        params.append(f"%{keyword}%")
    sql += " GROUP BY s.station_id ORDER BY s.station_region, s.station_name"
    return fetch_all(sql, params)


def available_bicycles(station_id: int) -> list[dict]:
    return fetch_all(
        "SELECT bicycle_id, bicycle_registered_at FROM bicycle "
        "WHERE bicycle_station_id = %s AND bicycle_status = 'AVAILABLE' ORDER BY bicycle_id",
        (station_id,),
    )


def active_stations() -> list[dict]:
    return fetch_all(
        "SELECT station_id, station_name, station_region FROM station "
        "WHERE station_status = 'ACTIVE' ORDER BY station_region, station_name"
    )


# ---------------------------------------------------------------- 대여
def rent_bicycle(user_id: int, station_id: int, bicycle_id: int) -> int:
    """자전거 대여: rental 생성, 자전거 RENTED·현재 대여소 NULL. 생성된 rental_id 반환."""
    with transaction() as cur:
        cur.execute("SELECT user_status FROM `user` WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        if not user or user["user_status"] != "ACTIVE":
            raise BusinessError("이용정지 또는 탈퇴 상태의 회원은 대여할 수 없습니다.")

        cur.execute("SELECT station_status FROM station WHERE station_id = %s", (station_id,))
        station = cur.fetchone()
        if not station or station["station_status"] != "ACTIVE":
            raise BusinessError("운영 중인 대여소가 아닙니다.")

        # 같은 자전거를 동시에 두 명이 빌리지 못하도록 행 잠금
        cur.execute(
            "SELECT bicycle_status, bicycle_station_id FROM bicycle "
            "WHERE bicycle_id = %s FOR UPDATE",
            (bicycle_id,),
        )
        bike = cur.fetchone()
        if (not bike or bike["bicycle_status"] != "AVAILABLE"
                or bike["bicycle_station_id"] != station_id):
            raise BusinessError("이미 대여되었거나 대여할 수 없는 자전거입니다. 목록을 새로 확인해 주세요.")

        cur.execute(
            "UPDATE bicycle SET bicycle_status = 'RENTED', bicycle_station_id = NULL "
            "WHERE bicycle_id = %s",
            (bicycle_id,),
        )
        cur.execute(
            "INSERT INTO rental (rental_start_time, rental_status, start_station_id, "
            "                    rental_bicycle_id, rental_user_id) "
            "VALUES (NOW(), 'RENTING', %s, %s, %s)",
            (station_id, bicycle_id, user_id),
        )
        return cur.lastrowid


# ---------------------------------------------------------------- 반납·결제
def ongoing_rentals(user_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT r.rental_id, r.rental_start_time, r.rental_bicycle_id,
               s.station_name AS start_station_name, NOW() AS now
        FROM rental r
        JOIN station s ON s.station_id = r.start_station_id
        WHERE r.rental_user_id = %s AND r.rental_status = 'RENTING'
        ORDER BY r.rental_start_time
        """,
        (user_id,),
    )


def mileage_balance(user_id: int) -> int:
    row = fetch_one(
        "SELECT balance FROM v_user_mileage_balance WHERE user_id = %s", (user_id,)
    )
    return int(row["balance"]) if row else 0


def return_and_pay(user_id: int, rental_id: int, return_station_id: int,
                   distance_km: Decimal, use_points: int, method: str) -> dict:
    """반납 → 마일리지 적립 → 결제·할인을 한 트랜잭션으로 처리한다.

    이번 대여로 적립되는 포인트는 다음 결제부터 쓸 수 있으므로,
    할인 한도는 적립 전의 보유 마일리지로 계산한다.
    """
    if method not in rules.PAYMENT_METHODS:
        raise BusinessError("결제수단을 선택해 주세요.")
    if use_points < 0:
        raise BusinessError("사용 포인트가 올바르지 않습니다.")

    with transaction() as cur:
        # 같은 이용자의 마일리지 사용이 동시에 처리되지 않도록 이용자 행 잠금
        cur.execute("SELECT user_id FROM `user` WHERE user_id = %s FOR UPDATE", (user_id,))
        if not cur.fetchone():
            raise BusinessError("이용자를 찾을 수 없습니다.")

        cur.execute(
            "SELECT rental_start_time, rental_status, rental_bicycle_id FROM rental "
            "WHERE rental_id = %s AND rental_user_id = %s FOR UPDATE",
            (rental_id, user_id),
        )
        rental = cur.fetchone()
        if not rental or rental["rental_status"] != "RENTING":
            raise BusinessError("이미 반납된 대여입니다.")

        cur.execute("SELECT station_status FROM station WHERE station_id = %s",
                    (return_station_id,))
        station = cur.fetchone()
        if not station or station["station_status"] != "ACTIVE":
            raise BusinessError("운영 중인 대여소에만 반납할 수 있습니다.")

        cur.execute("SELECT NOW() AS now")
        now = cur.fetchone()["now"]

        amount = rules.usage_fee(rental["rental_start_time"], now)
        earned = rules.earn_points(distance_km)

        cur.execute("SELECT balance FROM v_user_mileage_balance WHERE user_id = %s", (user_id,))
        balance_before = int(cur.fetchone()["balance"])
        limit = rules.discount_limit(amount, balance_before)
        if use_points > limit:
            raise BusinessError(f"사용 가능한 마일리지는 최대 {limit:,}P입니다.")

        # 1) 반납
        cur.execute(
            "UPDATE rental SET rental_end_time = %s, rental_status = 'RETURNED', "
            "       rental_distance = %s, return_station_id = %s "
            "WHERE rental_id = %s",
            (now, distance_km, return_station_id, rental_id),
        )
        cur.execute(
            "UPDATE bicycle SET bicycle_status = 'AVAILABLE', bicycle_station_id = %s "
            "WHERE bicycle_id = %s",
            (return_station_id, rental["rental_bicycle_id"]),
        )

        # 2) 마일리지 적립 (0P면 기록하지 않음)
        if earned > 0:
            cur.execute(
                "INSERT INTO mileage (mileage_type, mileage_point, mileage_created_at, "
                "                     mileage_user_id, mileage_rental_id) "
                "VALUES ('EARN', %s, %s, %s, %s)",
                (earned, now, user_id, rental_id),
            )

        # 3) 결제·할인
        final = amount - use_points
        cur.execute(
            "INSERT INTO payment (payment_amount, payment_discount, payment_final_amount, "
            "                     payment_method, payment_at, payment_rental_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (amount, use_points, final, method, now, rental_id),
        )
        payment_id = cur.lastrowid
        if use_points > 0:
            cur.execute(
                "INSERT INTO mileage (mileage_type, mileage_point, mileage_created_at, "
                "                     mileage_user_id, mileage_payment_id) "
                "VALUES ('USE', %s, %s, %s, %s)",
                (use_points, now, user_id, payment_id),
            )

    return {
        "minutes": rules.usage_minutes(rental["rental_start_time"], now),
        "amount": amount,
        "discount": use_points,
        "final": final,
        "carbon_g": rules.carbon_saved_g(distance_km),
        "earned": earned,
        "balance_after": balance_before + earned - use_points,
    }


# ---------------------------------------------------------------- 마이페이지
def my_rentals(user_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT r.rental_id, r.rental_start_time, r.rental_end_time, r.rental_status,
               r.rental_distance, ss.station_name AS start_station,
               rs.station_name AS return_station, r.rental_bicycle_id
        FROM rental r
        JOIN station ss ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        WHERE r.rental_user_id = %s
        ORDER BY r.rental_start_time DESC
        """,
        (user_id,),
    )


def my_payments(user_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT p.payment_id, p.payment_at, p.payment_rental_id, p.payment_amount,
               p.payment_discount, p.payment_final_amount, p.payment_method
        FROM payment p
        JOIN rental r ON r.rental_id = p.payment_rental_id
        WHERE r.rental_user_id = %s
        ORDER BY p.payment_at DESC
        """,
        (user_id,),
    )


def my_mileage(user_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT mileage_id, mileage_created_at, mileage_type, mileage_point,
               mileage_rental_id, mileage_payment_id
        FROM mileage
        WHERE mileage_user_id = %s
        ORDER BY mileage_created_at DESC, mileage_id DESC
        """,
        (user_id,),
    )


def my_summary(user_id: int) -> dict:
    bal = fetch_one(
        "SELECT total_earned, total_used, balance FROM v_user_mileage_balance WHERE user_id = %s",
        (user_id,),
    ) or {"total_earned": 0, "total_used": 0, "balance": 0}
    dist = fetch_one(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(rental_distance), 0) AS total_km FROM rental "
        "WHERE rental_user_id = %s AND rental_status = 'RETURNED'",
        (user_id,),
    )
    return {
        **bal,
        "rental_count": dist["cnt"],
        "total_km": dist["total_km"],
        "carbon_g": rules.carbon_saved_g(dist["total_km"]),
    }
