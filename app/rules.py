"""PedalPoint 요금·마일리지 규칙 (시연 데이터 sql/GreenRide_DML.sql과 같은 기준).

기준값은 DB에 저장하지 않고 응용프로그램의 고정값으로 관리한다.
"""
import math
import re
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

import bcrypt

# 기본 이용요금: 60분 1,000원, 초과 30분마다 500원 (30분 미만도 30분으로 계산)
BASE_MINUTES = 60
BASE_FEE = 1000
EXTRA_UNIT_MINUTES = 30
EXTRA_UNIT_FEE = 500

# 적립 포인트(P) = 이동거리(km) × 100 (소수점 이하 버림), 1P = 1원
POINTS_PER_KM = Decimal("100")
# 화면에 보여주는 탄소 절감량(g) = 이동거리(km) × 210 g/km
CARBON_G_PER_KM = Decimal("210")

# DB의 payment_method ENUM 값과 같다
PAYMENT_METHODS = ["카드", "간편결제", "계좌이체"]

# 이동거리 입력 범위 (km)
MAX_DISTANCE_KM = Decimal("99.99")


def usage_minutes(start: datetime, end: datetime) -> float:
    return max((end - start).total_seconds(), 0) / 60


def usage_fee(start: datetime, end: datetime) -> int:
    """이용시간에 따른 이용금액(원)."""
    over_seconds = (end - start).total_seconds() - BASE_MINUTES * 60
    if over_seconds <= 0:
        return BASE_FEE
    units = math.ceil(over_seconds / (EXTRA_UNIT_MINUTES * 60))
    return BASE_FEE + units * EXTRA_UNIT_FEE


def carbon_saved_g(distance_km) -> Decimal:
    """탄소 절감량(g)."""
    return Decimal(str(distance_km or 0)) * CARBON_G_PER_KM


def earn_points(distance_km) -> int:
    """반납 시 적립 포인트(P)."""
    return int((Decimal(str(distance_km or 0)) * POINTS_PER_KM).to_integral_value(ROUND_FLOOR))


def discount_limit(amount: int, balance: int) -> int:
    """할인 한도: 이용금액과 보유 마일리지 중 작은 값."""
    return max(min(amount, balance), 0)


# ---------------------------------------------------------------- 탄소 절감 체감
# 줄인 탄소를 생활 속 수치로 바꿔 보여준다.
#  - 승용차: 1km 주행 시 약 210g 배출 (위 CARBON_G_PER_KM과 같은 기준: 자전거가 승용차 이동을 대신했다고 본다)
#  - 소나무: 한 그루가 1년에 약 6.6kg 흡수 (산림청 기준) → 하루 약 18g
PINE_G_PER_YEAR = Decimal("6600")
PINE_G_PER_DAY = PINE_G_PER_YEAR / 365

# 나의 숲 단계: 누적 절감량(g) 기준
CARBON_LEVELS = [
    (0, "새싹", "🌱"),
    (1_000, "묘목", "🌿"),
    (5_000, "어린 나무", "🌳"),
    (15_000, "큰 나무", "🌲"),
    (40_000, "숲", "🏞️"),
]
MONTH_GOAL_G = Decimal("3000")  # 이번 달 목표 3kg (약 14km)


def carbon_equivalents(carbon_g) -> dict:
    """줄인 탄소(g) → 승용차 대체 거리(km), 소나무 하루 흡수량(그루), 소나무 1년 흡수량(그루)."""
    g = Decimal(str(carbon_g or 0))
    return {
        "car_km": g / CARBON_G_PER_KM,
        "pine_days": g / PINE_G_PER_DAY,
        "pine_years": g / PINE_G_PER_YEAR,
    }


def carbon_level(carbon_g) -> dict:
    """누적 절감량으로 현재 단계와 다음 단계까지의 진행률."""
    g = Decimal(str(carbon_g or 0))
    idx = max(i for i, (th, _, _) in enumerate(CARBON_LEVELS) if g >= th)
    th, name, icon = CARBON_LEVELS[idx]
    if idx + 1 < len(CARBON_LEVELS):
        nxt_th, nxt_name, nxt_icon = CARBON_LEVELS[idx + 1]
        progress = float((g - th) / (nxt_th - th))
        remain = Decimal(nxt_th) - g
    else:
        nxt_name, nxt_icon, progress, remain = None, None, 1.0, Decimal(0)
    return {"step": idx + 1, "steps": len(CARBON_LEVELS), "name": name, "icon": icon,
            "next_name": nxt_name, "next_icon": nxt_icon, "progress": min(max(progress, 0.0), 1.0),
            "remain_g": remain}


# ---------------------------------------------------------------- 계정
LOGIN_ID_RE = re.compile(r"^[A-Za-z0-9]{4,20}$")
PHONE_RE = re.compile(r"^010-\d{4}-\d{4}$")
MIN_PASSWORD = 4


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:  # 해시 형식이 아닌 값
        return False
