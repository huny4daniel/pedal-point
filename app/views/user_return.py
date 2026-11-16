"""이용자 · 반납·결제: 반납 대여소·이동거리 입력 → 마일리지 적립 → 마일리지 사용량 선택 후 결제."""
from decimal import Decimal

import streamlit as st

import rules
import ui
import user_ops
from db import BusinessError


def _show_receipt(r: dict) -> None:
    st.success("반납과 결제가 완료되었습니다.")
    ui.stat_cards([
        ("탄소 절감량", ui.carbon(r["carbon_g"]), "", False),
        ("적립 마일리지", ui.pt(r["earned"]), "", True),
        ("최종 결제금액", ui.won(r["final"]), "", False),
        ("현재 마일리지 잔액", ui.pt(r["balance_after"]), "", False),
    ])
    ui.calc_rows(
        [
            ("이용시간", ui.minutes(r["minutes"])),
            ("이용금액", ui.won(r["amount"])),
            ("마일리지 할인", f"- {ui.won(r['discount'])}"),
        ],
        ("최종금액", ui.won(r["final"])),
    )


def render() -> None:
    user_id = st.session_state["user_id"]
    ui.page_header("RETURN", "반납·결제", "반납하면 이동거리만큼 마일리지가 쌓이고, 보유 마일리지로 요금을 할인받습니다.")

    if receipt := st.session_state.pop("return_receipt", None):
        _show_receipt(receipt)

    rentals = user_ops.ongoing_rentals(user_id)
    if not rentals:
        st.info("현재 대여 중인 자전거가 없습니다.")
        return

    options = {r["rental_id"]: r for r in rentals}
    rental_id = st.selectbox(
        "반납할 대여",
        list(options),
        format_func=lambda i: (
            f"대여번호 {i} · 자전거 #{options[i]['rental_bicycle_id']} · "
            f"{options[i]['start_station_name']}에서 {ui.dt(options[i]['rental_start_time'])} 대여"
        ),
    )
    rental = options[rental_id]

    stations = user_ops.active_stations()
    st_opts = {s["station_id"]: f"{s['station_name']} ({s['station_region']})" for s in stations}

    c1, c2 = st.columns(2)
    return_station = c1.selectbox("반납 대여소", list(st_opts), format_func=st_opts.get)
    distance = c2.number_input(
        "이동거리 (km)", min_value=0.0, max_value=9999.99, value=0.0, step=0.1, format="%.2f"
    )
    distance_km = Decimal(f"{distance:.2f}")

    # 현재 시각 기준 미리보기 (실제 금액은 결제 시점에 다시 계산)
    now = rental["now"]
    amount = rules.usage_fee(rental["rental_start_time"], now)
    earned = rules.earn_points(distance_km)
    balance = user_ops.mileage_balance(user_id)
    limit = rules.discount_limit(amount, balance)

    st.markdown("#### 마일리지 적립")
    ui.calc_rows(
        [
            ("이동거리", ui.km(distance_km)),
            ("탄소 절감량 (× 210g/km)", ui.carbon(rules.carbon_saved_g(distance_km))),
        ],
        ("적립 포인트 (10g당 1P)", ui.pt(earned)),
    )
    if 0 < distance_km and earned == 0:
        st.caption("이동거리가 0.05km 미만이면 적립 포인트가 0이라 마일리지 기록을 만들지 않습니다.")

    st.markdown("#### 결제")
    ui.calc_rows(
        [
            ("이용시간 (현재 기준)", ui.minutes(rules.usage_minutes(rental["rental_start_time"], now))),
            ("이용금액", ui.won(amount)),
            ("보유 마일리지", ui.pt(balance)),
            ("할인 한도 (이용금액 50%, 보유 마일리지 이내)", ui.pt(limit)),
        ]
    )
    st.caption("이번 반납으로 적립되는 포인트는 다음 결제부터 사용할 수 있습니다.")

    c3, c4 = st.columns(2)
    use_points = c3.number_input(
        "사용할 마일리지 (P)", min_value=0, max_value=limit, value=0, step=10,
        disabled=limit == 0,
    )
    method = c4.selectbox(
        "결제수단", list(rules.PAYMENT_METHODS), format_func=rules.PAYMENT_METHODS.get
    )

    ui.calc_rows(
        [("이용금액", ui.won(amount)), ("마일리지 할인", f"- {ui.won(use_points)}")],
        ("최종금액", ui.won(amount - use_points)),
    )

    if st.button("반납하고 결제하기", type="primary"):
        try:
            receipt = user_ops.return_and_pay(
                user_id, rental_id, return_station, distance_km, int(use_points), method
            )
        except BusinessError as e:
            st.error(str(e))
        else:
            st.session_state["return_receipt"] = receipt
            st.rerun()
