"""PedalPoint 요금·마일리지 규칙 (개발 계획서 4장의 기준값).

탄소절감계수 등 기준값은 DB에 저장하지 않고 응용프로그램의 고정값으로 관리한다.
"""
import math
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

# 탄소 절감량(g) = 이동거리(km) × 210 g/km
CARBON_G_PER_KM = Decimal("210")
# 적립 포인트(P) = 탄소 절감량(g) ÷ 10 (소수점 이하 버림)
CARBON_G_PER_POINT = Decimal("10")

# 기본 이용요금: 60분 1,000원, 초과 5분마다 200원 (5분 미만도 5분으로 계산)
BASE_MINUTES = 60
BASE_FEE = 1000
EXTRA_UNIT_MINUTES = 5
EXTRA_UNIT_FEE = 200

# 1P = 1원, 한 번 결제에 이용금액의 50%까지 할인
MAX_DISCOUNT_RATE = Decimal("0.5")

PAYMENT_METHODS = {"CARD": "카드", "MOBILE": "모바일", "TRANSFER": "계좌이체"}


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
    return Decimal(str(distance_km)) * CARBON_G_PER_KM


def earn_points(distance_km) -> int:
    """반납 시 적립 포인트(P). 이동거리가 0.05km 미만이면 0."""
    return int((carbon_saved_g(distance_km) / CARBON_G_PER_POINT).to_integral_value(ROUND_FLOOR))


def discount_limit(amount: int, balance: int) -> int:
    """할인 한도: 이용금액의 50%와 보유 마일리지 중 작은 값."""
    rate_limit = int((Decimal(amount) * MAX_DISCOUNT_RATE).to_integral_value(ROUND_FLOOR))
    return max(min(rate_limit, balance), 0)
