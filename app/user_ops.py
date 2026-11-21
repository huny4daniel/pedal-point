"""이용자 기능: 로그인·회원가입, 대여소 검색, 대여, 반납·결제, 내역 조회.

대여 상태는 rental_end_time의 NULL 여부로 판단한다 (NULL = 대여 중).
결제 대기 = 반납은 됐지만 payment 행이 없는 대여.
"""
from decimal import Decimal

import rules
from db import BusinessError, DBError, fetch_all, fetch_one, transaction


# ---------------------------------------------------------------- 로그인·회원가입
def authenticate_user(login_id: str, password: str) -> dict:
    """아이디·비밀번호로 이용자 인증. 성공하면 user 행, 실패하면 BusinessError."""
    row = fetch_one(
        "SELECT user_id, user_password, user_status FROM `user` WHERE user_login_id = %s",
        (login_id.strip(),),
    )
    if not row or not rules.check_password(password, row["user_password"]):
        raise BusinessError("아이디 또는 비밀번호가 올바르지 않습니다.")
    if row["user_status"] == "WITHDRAWN":
        raise BusinessError("탈퇴한 회원입니다.")
    return row


def signup(login_id: str, password: str, password2: str, name: str, phone: str) -> int:
    """회원가입. 새 user_id 반환. 마일리지·상태·가입일은 DB 기본값."""
    login_id, name, phone = login_id.strip(), name.strip(), phone.strip()
    if not rules.LOGIN_ID_RE.match(login_id):
        raise BusinessError("아이디는 영문·숫자 4~20자로 입력해 주세요.")
    if len(password) < rules.MIN_PASSWORD:
        raise BusinessError(f"비밀번호는 {rules.MIN_PASSWORD}자 이상이어야 합니다.")
    if password != password2:
        raise BusinessError("비밀번호 확인이 일치하지 않습니다.")
    name, phone = _check_name_phone(name, phone)
    try:
        with transaction() as cur:
            cur.execute(
                "INSERT INTO `user` (user_login_id, user_password, user_name, user_phone) "
                "VALUES (%s, %s, %s, %s)",
                (login_id, rules.hash_password(password), name, phone),
            )
            return cur.lastrowid
    except DBError as e:
        if e.errno == 1062:  # UNIQUE(user_login_id, user_phone) 중복
            raise BusinessError("이미 사용 중인 아이디 또는 연락처입니다.") from e
        raise


def get_user(user_id: int) -> dict | None:
    return fetch_one("SELECT * FROM `user` WHERE user_id = %s", (user_id,))


def _check_name_phone(name: str, phone: str) -> tuple[str, str]:
    name, phone = name.strip(), phone.strip()
    if not 1 <= len(name) <= 50:
        raise BusinessError("이름을 1~50자로 입력해 주세요.")
    if not rules.PHONE_RE.match(phone):
        raise BusinessError("연락처는 010-0000-0000 형식으로 입력해 주세요.")
    return name, phone


def update_profile(user_id: int, name: str, phone: str) -> None:
    """회원정보(이름·연락처) 수정."""
    name, phone = _check_name_phone(name, phone)
    try:
        with transaction() as cur:
            cur.execute("UPDATE `user` SET user_name = %s, user_phone = %s WHERE user_id = %s",
                        (name, phone, user_id))
    except DBError as e:
        if e.errno == 1062:
            raise BusinessError("이미 사용 중인 연락처입니다.") from e
        raise


def change_password(user_id: int, current: str, new: str, new2: str) -> None:
    if len(new) < rules.MIN_PASSWORD:
        raise BusinessError(f"새 비밀번호는 {rules.MIN_PASSWORD}자 이상이어야 합니다.")
    if new != new2:
        raise BusinessError("새 비밀번호 확인이 일치하지 않습니다.")
    with transaction() as cur:
        cur.execute("SELECT user_password FROM `user` WHERE user_id = %s FOR UPDATE", (user_id,))
        row = cur.fetchone()
        if not row or not rules.check_password(current, row["user_password"]):
            raise BusinessError("현재 비밀번호가 올바르지 않습니다.")
        cur.execute("UPDATE `user` SET user_password = %s WHERE user_id = %s",
                    (rules.hash_password(new), user_id))


def withdraw(user_id: int, password: str) -> None:
    """회원 탈퇴: 행은 지우지 않고 상태만 WITHDRAWN (대여·결제 기록 보존).

    대여 중이거나 결제 대기 중인 대여가 있으면 탈퇴할 수 없다.
    """
    with transaction() as cur:
        cur.execute("SELECT user_password FROM `user` WHERE user_id = %s FOR UPDATE", (user_id,))
        row = cur.fetchone()
        if not row or not rules.check_password(password, row["user_password"]):
            raise BusinessError("비밀번호가 올바르지 않습니다.")
        cur.execute("SELECT 1 FROM rental WHERE rental_user_id = %s AND rental_end_time IS NULL", (user_id,))
        if cur.fetchone():
            raise BusinessError("대여 중인 자전거가 있어 탈퇴할 수 없습니다. 반납 후 다시 시도하세요.")
        cur.execute(
            "SELECT 1 FROM rental r LEFT JOIN payment p ON p.payment_rental_id = r.rental_id "
            "WHERE r.rental_user_id = %s AND r.rental_end_time IS NOT NULL AND p.payment_id IS NULL",
            (user_id,),
        )
        if cur.fetchone():
            raise BusinessError("결제하지 않은 대여가 있어 탈퇴할 수 없습니다. 결제 후 다시 시도하세요.")
        cur.execute("UPDATE `user` SET user_status = 'WITHDRAWN' WHERE user_id = %s", (user_id,))


# ---------------------------------------------------------------- 서비스 현황 (로그인 화면)
def service_stats() -> dict:
    return fetch_one(
        """
        SELECT (SELECT COUNT(*) FROM station WHERE station_status = 'ACTIVE') AS stations,
               (SELECT COUNT(*) FROM bicycle b JOIN station s ON s.station_id = b.bicycle_station_id
                 WHERE b.bicycle_status = 'AVAILABLE' AND s.station_status = 'ACTIVE') AS bikes,
               (SELECT COALESCE(SUM(rental_distance), 0) FROM rental WHERE rental_end_time IS NOT NULL) AS total_km
        """
    )


# ---------------------------------------------------------------- 검색
def search_stations(keyword: str) -> list[dict]:
    """운영 중인 대여소를 이름·주소로 검색하고 대여 가능 자전거 수를 함께 보여준다."""
    like = f"%{keyword.strip()}%"
    return fetch_all(
        """
        SELECT s.station_id, s.station_name, s.station_address, s.station_contactnumber,
               s.station_totaldocks, COUNT(b.bicycle_id) AS available_count
        FROM station s
        LEFT JOIN bicycle b
               ON b.bicycle_station_id = s.station_id AND b.bicycle_status = 'AVAILABLE'
        WHERE s.station_status = 'ACTIVE'
          AND (s.station_name LIKE %s OR s.station_address LIKE %s)
        GROUP BY s.station_id
        ORDER BY s.station_name
        """,
        (like, like),
    )


def available_bicycles(station_id: int) -> list[dict]:
    return fetch_all(
        "SELECT bicycle_id, bicycle_registered_at FROM bicycle "
        "WHERE bicycle_station_id = %s AND bicycle_status = 'AVAILABLE' ORDER BY bicycle_id",
        (station_id,),
    )


def return_stations() -> list[dict]:
    """반납 가능한 대여소: 운영 중이고 빈 거치대가 있는 곳."""
    return fetch_all(
        """
        SELECT s.station_id, s.station_name, s.station_address,
               s.station_totaldocks - COUNT(b.bicycle_id) AS free_docks
        FROM station s
        LEFT JOIN bicycle b ON b.bicycle_station_id = s.station_id
        WHERE s.station_status = 'ACTIVE'
        GROUP BY s.station_id
        HAVING free_docks > 0
        ORDER BY s.station_name
        """
    )


# ---------------------------------------------------------------- 대여
def has_ongoing_rental(user_id: int) -> bool:
    return fetch_one(
        "SELECT 1 AS x FROM rental WHERE rental_user_id = %s AND rental_end_time IS NULL", (user_id,)
    ) is not None


def rent_bicycle(user_id: int, station_id: int, bicycle_id: int) -> int:
    """자전거 대여: rental 생성, 자전거 RENTED·현재 대여소 NULL. 생성된 rental_id 반환."""
    with transaction() as cur:
        # 같은 이용자의 대여가 동시에 두 건 생기지 않도록 이용자 행 잠금
        cur.execute("SELECT user_status FROM `user` WHERE user_id = %s FOR UPDATE", (user_id,))
        user = cur.fetchone()
        if not user or user["user_status"] != "ACTIVE":
            raise BusinessError("이용이 정지된 회원입니다.")

        cur.execute(
            "SELECT 1 FROM rental WHERE rental_user_id = %s AND rental_end_time IS NULL", (user_id,)
        )
        if cur.fetchone():
            raise BusinessError("이미 대여 중인 자전거가 있습니다.")

        cur.execute("SELECT station_status FROM station WHERE station_id = %s", (station_id,))
        station = cur.fetchone()
        if not station or station["station_status"] != "ACTIVE":
            raise BusinessError("운영 중인 대여소가 아닙니다.")

        # 같은 자전거를 동시에 두 명이 빌리지 못하도록 행 잠금
        cur.execute(
            "SELECT bicycle_status, bicycle_station_id FROM bicycle WHERE bicycle_id = %s FOR UPDATE",
            (bicycle_id,),
        )
        bike = cur.fetchone()
        if (not bike or bike["bicycle_status"] != "AVAILABLE"
                or bike["bicycle_station_id"] != station_id):
            raise BusinessError("이미 대여되었거나 대여할 수 없는 자전거입니다.")

        cur.execute(
            "UPDATE bicycle SET bicycle_status = 'RENTED', bicycle_station_id = NULL WHERE bicycle_id = %s",
            (bicycle_id,),
        )
        cur.execute(
            "INSERT INTO rental (rental_start_time, rental_user_id, rental_bicycle_id, start_station_id) "
            "VALUES (NOW(), %s, %s, %s)",
            (user_id, bicycle_id, station_id),
        )
        return cur.lastrowid


# ---------------------------------------------------------------- 반납·결제
def ongoing_rentals(user_id: int) -> list[dict]:
    """대여 중 (반납 전). now는 미리보기용 DB 현재 시각."""
    return fetch_all(
        """
        SELECT r.rental_id, r.rental_start_time, r.rental_bicycle_id,
               s.station_name AS start_station, NOW() AS now
        FROM rental r
        JOIN station s ON s.station_id = r.start_station_id
        WHERE r.rental_user_id = %s AND r.rental_end_time IS NULL
        ORDER BY r.rental_start_time
        """,
        (user_id,),
    )


def pending_rentals(user_id: int) -> list[dict]:
    """결제 대기 (반납은 됐지만 결제가 없음)."""
    return fetch_all(
        """
        SELECT r.rental_id, r.rental_start_time, r.rental_end_time, r.rental_distance,
               r.rental_bicycle_id, ss.station_name AS start_station, rs.station_name AS return_station
        FROM rental r
        LEFT JOIN payment p ON p.payment_rental_id = r.rental_id
        JOIN station ss ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        WHERE r.rental_user_id = %s AND r.rental_end_time IS NOT NULL AND p.payment_id IS NULL
        ORDER BY r.rental_start_time
        """,
        (user_id,),
    )


def mileage_balance(user_id: int) -> int:
    row = fetch_one("SELECT user_mileage FROM `user` WHERE user_id = %s", (user_id,))
    return int(row["user_mileage"]) if row else 0


def _check_payment_input(use_points: int, method: str) -> None:
    if method not in rules.PAYMENT_METHODS:
        raise BusinessError("결제수단을 선택해 주세요.")
    if use_points < 0:
        raise BusinessError("사용 포인트가 올바르지 않습니다.")


def _pay(cur, user_id: int, rental_id: int, start, end, distance_km, use_points: int,
         method: str) -> dict:
    """결제 공통 단계: 요금 계산 → 할인 한도 확인 → payment, mileage 기록 → 보유 마일리지 갱신.

    할인 한도는 적립 전 잔액으로 계산하므로 이번 대여로 쌓인 포인트는 다음 결제부터 쓴다.
    """
    amount = rules.usage_fee(start, end)
    cur.execute("SELECT user_mileage FROM `user` WHERE user_id = %s FOR UPDATE", (user_id,))
    balance = int(cur.fetchone()["user_mileage"])
    limit = rules.discount_limit(amount, balance)
    if use_points > limit:
        raise BusinessError(f"사용 가능한 마일리지는 최대 {limit:,}P입니다.")

    final = amount - use_points
    cur.execute(
        "INSERT INTO payment (payment_amount, payment_discount, payment_final_amount, "
        "                     payment_method, payment_at, payment_rental_id) "
        "VALUES (%s, %s, %s, %s, NOW(), %s)",
        (amount, use_points, final, method, rental_id),
    )
    earned = rules.earn_points(distance_km)
    if earned > 0:
        cur.execute(
            "INSERT INTO mileage (mileage_point, mileage_created_at, mileage_rental_id) "
            "VALUES (%s, NOW(), %s)",
            (earned, rental_id),
        )
    cur.execute(
        "UPDATE `user` SET user_mileage = user_mileage - %s + %s WHERE user_id = %s",
        (use_points, earned, user_id),
    )
    return {
        "rental_id": rental_id,
        "minutes": rules.usage_minutes(start, end),
        "amount": amount,
        "discount": use_points,
        "final": final,
        "distance": distance_km,
        "carbon_g": rules.carbon_saved_g(distance_km),
        "earned": earned,
        "balance_after": balance - use_points + earned,
    }


def return_and_pay(user_id: int, rental_id: int, return_station_id: int,
                   distance_km: Decimal, use_points: int, method: str) -> dict:
    """반납 → 결제 → 마일리지 적립을 한 트랜잭션으로 처리한다."""
    _check_payment_input(use_points, method)
    if not Decimal(0) <= distance_km <= rules.MAX_DISTANCE_KM:
        raise BusinessError(f"이동 거리는 0 ~ {rules.MAX_DISTANCE_KM}km로 입력해 주세요.")

    with transaction() as cur:
        cur.execute(
            "SELECT rental_start_time, rental_end_time, rental_bicycle_id FROM rental "
            "WHERE rental_id = %s AND rental_user_id = %s FOR UPDATE",
            (rental_id, user_id),
        )
        rental = cur.fetchone()
        if not rental:
            raise BusinessError("대여 내역을 찾을 수 없습니다.")
        if rental["rental_end_time"] is not None:
            raise BusinessError("이미 반납된 대여입니다.")

        # 반납 대여소: 운영 중 + 빈 거치대
        cur.execute(
            "SELECT station_status, station_totaldocks FROM station WHERE station_id = %s FOR UPDATE",
            (return_station_id,),
        )
        station = cur.fetchone()
        if not station or station["station_status"] != "ACTIVE":
            raise BusinessError("운영 중인 대여소가 아닙니다.")
        cur.execute("SELECT COUNT(*) AS cnt FROM bicycle WHERE bicycle_station_id = %s",
                    (return_station_id,))
        if station["station_totaldocks"] - cur.fetchone()["cnt"] <= 0:
            raise BusinessError("빈 거치대가 없습니다. 다른 대여소를 선택하세요.")

        cur.execute("SELECT NOW() AS now")
        now = cur.fetchone()["now"]

        # 반납 시각·거리·반납 대여소는 CHECK 때문에 반드시 함께 채운다
        cur.execute(
            "UPDATE rental SET rental_end_time = %s, rental_distance = %s, return_station_id = %s "
            "WHERE rental_id = %s",
            (now, distance_km, return_station_id, rental_id),
        )
        cur.execute(
            "UPDATE bicycle SET bicycle_status = 'AVAILABLE', bicycle_station_id = %s WHERE bicycle_id = %s",
            (return_station_id, rental["rental_bicycle_id"]),
        )
        return _pay(cur, user_id, rental_id, rental["rental_start_time"], now,
                    distance_km, use_points, method)


def pay_pending(user_id: int, rental_id: int, use_points: int, method: str) -> dict:
    """결제 대기 대여의 결제·적립만 처리한다."""
    _check_payment_input(use_points, method)
    with transaction() as cur:
        cur.execute(
            "SELECT r.rental_start_time, r.rental_end_time, r.rental_distance, p.payment_id "
            "FROM rental r LEFT JOIN payment p ON p.payment_rental_id = r.rental_id "
            "WHERE r.rental_id = %s AND r.rental_user_id = %s FOR UPDATE",
            (rental_id, user_id),
        )
        rental = cur.fetchone()
        if not rental:
            raise BusinessError("대여 내역을 찾을 수 없습니다.")
        if rental["rental_end_time"] is None:
            raise BusinessError("아직 반납하지 않은 대여입니다.")
        if rental["payment_id"] is not None:
            raise BusinessError("이미 결제된 대여입니다.")
        return _pay(cur, user_id, rental_id, rental["rental_start_time"], rental["rental_end_time"],
                    rental["rental_distance"], use_points, method)


# ---------------------------------------------------------------- 홈 대시보드
_MONTH_START = "DATE_FORMAT(NOW(), '%%Y-%%m-01')"  # 이번 달 1일 (DB 현재 시각 기준)


def month_summary(user_id: int) -> dict:
    """이번 달 이용 요약: 이용 횟수·이동거리·적립·사용 마일리지·결제액."""
    m = _MONTH_START
    return fetch_one(
        f"""
        SELECT
          (SELECT COUNT(*) FROM rental r
            WHERE r.rental_user_id = %s AND r.rental_start_time >= {m}) AS rides,
          (SELECT COALESCE(SUM(r.rental_distance), 0) FROM rental r
            WHERE r.rental_user_id = %s AND r.rental_end_time >= {m}) AS km,
          (SELECT COALESCE(SUM(mi.mileage_point), 0) FROM mileage mi
             JOIN rental r ON r.rental_id = mi.mileage_rental_id
            WHERE r.rental_user_id = %s AND mi.mileage_created_at >= {m}) AS earned,
          (SELECT COALESCE(SUM(p.payment_discount), 0) FROM payment p
             JOIN rental r ON r.rental_id = p.payment_rental_id
            WHERE r.rental_user_id = %s AND p.payment_at >= {m}) AS used,
          (SELECT COALESCE(SUM(p.payment_final_amount), 0) FROM payment p
             JOIN rental r ON r.rental_id = p.payment_rental_id
            WHERE r.rental_user_id = %s AND p.payment_at >= {m}) AS paid,
          YEAR(NOW()) AS y, MONTH(NOW()) AS mo
        """,
        (user_id,) * 5,
    )


def month_daily_km(user_id: int) -> list[dict]:
    """이번 달 일별 이동거리 (반납 완료 기준)."""
    return fetch_all(
        f"""
        SELECT DATE(r.rental_end_time) AS day, SUM(r.rental_distance) AS km
        FROM rental r
        WHERE r.rental_user_id = %s AND r.rental_end_time >= {_MONTH_START}
        GROUP BY DATE(r.rental_end_time)
        ORDER BY day
        """,
        (user_id,),
    )


def carbon_rank(user_id: int) -> dict:
    """누적 이동거리(= 줄인 탄소) 기준 내 순위. 한 번이라도 반납한 이용자 중에서 센다."""
    rows = fetch_all(
        """
        SELECT r.rental_user_id AS uid, SUM(r.rental_distance) AS km
        FROM rental r
        WHERE r.rental_end_time IS NOT NULL
        GROUP BY r.rental_user_id
        ORDER BY km DESC
        """
    )
    total = len(rows)
    mine = next((i for i, r in enumerate(rows) if r["uid"] == user_id), None)
    if mine is None:
        return {"rank": None, "riders": total, "top_pct": None}
    return {"rank": mine + 1, "riders": total, "top_pct": max(1, round((mine + 1) / total * 100))}


# ---------------------------------------------------------------- 마이페이지
def my_summary(user_id: int) -> dict:
    row = fetch_one(
        """
        SELECT u.user_mileage,
          (SELECT COALESCE(SUM(m.mileage_point), 0) FROM mileage m
             JOIN rental r ON r.rental_id = m.mileage_rental_id
            WHERE r.rental_user_id = u.user_id) AS total_earned,
          (SELECT COALESCE(SUM(p.payment_discount), 0) FROM payment p
             JOIN rental r ON r.rental_id = p.payment_rental_id
            WHERE r.rental_user_id = u.user_id) AS total_used,
          (SELECT COALESCE(SUM(r.rental_distance), 0) FROM rental r
            WHERE r.rental_user_id = u.user_id AND r.rental_end_time IS NOT NULL) AS total_km,
          (SELECT COUNT(*) FROM rental r
            WHERE r.rental_user_id = u.user_id AND r.rental_end_time IS NOT NULL) AS rental_count
        FROM `user` u
        WHERE u.user_id = %s
        """,
        (user_id,),
    )
    return {**row, "carbon_g": rules.carbon_saved_g(row["total_km"])}


def my_rentals(user_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT r.rental_id, r.rental_start_time, r.rental_end_time, r.rental_distance,
               r.rental_bicycle_id, p.payment_id,
               ss.station_name AS start_station, rs.station_name AS return_station
        FROM rental r
        JOIN station ss ON ss.station_id = r.start_station_id
        LEFT JOIN station rs ON rs.station_id = r.return_station_id
        LEFT JOIN payment p ON p.payment_rental_id = r.rental_id
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
    """마일리지 내역: 적립(mileage) + 사용(payment_discount > 0). point는 사용이면 음수."""
    return fetch_all(
        """
        SELECT m.mileage_created_at AS at, '적립' AS kind, m.mileage_point AS point,
               m.mileage_rental_id AS rental_id
        FROM mileage m
        JOIN rental r ON r.rental_id = m.mileage_rental_id
        WHERE r.rental_user_id = %s
        UNION ALL
        SELECT p.payment_at, '사용', -p.payment_discount, p.payment_rental_id
        FROM payment p
        JOIN rental r ON r.rental_id = p.payment_rental_id
        WHERE r.rental_user_id = %s AND p.payment_discount > 0
        ORDER BY at DESC, rental_id DESC
        """,
        (user_id, user_id),
    )
