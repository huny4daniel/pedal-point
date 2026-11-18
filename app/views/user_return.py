"""이용자 · 반납·결제: 반납 대여소·이동거리 입력 → 마일리지 적립 → 마일리지 사용량 선택 후 결제."""
from decimal import Decimal

import streamlit as st

import rules
import ui
import user_ops
from db import BusinessError


def _show_receipt(r: dict) -> None:
    ui.done("반납과 결제가 완료되었습니다",
            f"이번 이동으로 탄소 {ui.carbon(r['carbon_g'])}을 줄이고 {ui.pt(r['earned'])}를 적립했어요.")
    ui.stat_cards([
        ("적립 마일리지", ui.pt(r["earned"]), "", True),
        ("탄소 절감량", ui.carbon(r["carbon_g"]), "", False),
        ("최종 결제금액", ui.won(r["final"]), "", False),
        ("현재 마일리지 잔액", ui.pt(r["balance_after"]), "", False),
    ])
    with st.container(key="ppcard_receipt_done"):
        ui.card_title("결제 영수증")
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
    ui.page_header("이용자", "반납·결제", "반납하면 이동거리만큼 마일리지가 쌓이고, 보유 마일리지로 요금을 할인받습니다.")

    if receipt := st.session_state.pop("return_receipt", None):
        _show_receipt(receipt)
        return

    rentals = user_ops.ongoing_rentals(user_id)
    if not rentals:
        with st.container(key="ppcard_norental"):
            ui.empty("🅿️", "대여 중인 자전거가 없어요", "‘대여소 검색·대여’ 메뉴에서 자전거를 빌릴 수 있습니다.")
        return

    if ui.is_app():  # 스마트폰 앱: 입력 카드 다음에 결제 요약
        left, right = st.container(), st.container()
    else:
        left, right = st.columns([1.35, 1], gap="large")

    with left:
        with st.container(key="ppcard_return"):
            ui.card_title("반납 정보", "반납할 대여와 반납 대여소, 이동거리를 입력하세요.")
            options = {r["rental_id"]: r for r in rentals}
            rental_id = st.selectbox(
                "반납할 대여",
                list(options),
                format_func=lambda i: (
                    f"자전거 #{options[i]['rental_bicycle_id']} · {options[i]['start_station_name']} · "
                    f"{ui.dt(options[i]['rental_start_time'])} 대여 (대여번호 {i})"
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

        with st.container(key="ppcard_earn"):
            ui.card_title("이번 반납으로 적립될 마일리지")
            ui.calc_rows(
                [
                    ("이동거리", ui.km(distance_km)),
                    (f"탄소 절감량 (× {rules.CARBON_G_PER_KM}g/km)", ui.carbon(rules.carbon_saved_g(distance_km))),
                ],
                (f"적립 포인트 ({rules.CARBON_G_PER_POINT}g당 1P)", ui.pt(earned)),
            )
            st.caption("이번에 적립되는 포인트는 다음 결제부터 사용할 수 있습니다."
                       + (" 적립 포인트가 0이면 마일리지 기록을 만들지 않습니다." if 0 < distance_km and earned == 0 else ""))

        with st.container(key="ppcard_pay"):
            ui.card_title("마일리지 사용·결제수단",
                          f"보유 {ui.pt(balance)} · 이번 결제 할인 한도 {ui.pt(limit)} (이용금액의 50%, 보유 마일리지 이내)")
            c3, c4 = st.columns(2)
            use_points = c3.number_input(
                "사용할 마일리지 (P)", min_value=0, max_value=limit, value=0, step=10,
                disabled=limit == 0,
            )
            method = c4.segmented_control(
                "결제수단", list(rules.PAYMENT_METHODS), format_func=rules.PAYMENT_METHODS.get,
                default=next(iter(rules.PAYMENT_METHODS)), width="stretch",
            )

    with right:
        with st.container(key="ppcard_summary"):
            ui.card_title("결제 요약", f"{ui.dt(now)} 기준")
            ui.calc_rows(
                [
                    ("이용시간", ui.minutes(rules.usage_minutes(rental["rental_start_time"], now))),
                    ("이용금액", ui.won(amount)),
                    ("마일리지 할인", f"- {ui.won(use_points)}"),
                ],
                ("최종금액", ui.won(amount - use_points)),
            )
            if st.button("반납하고 결제하기", type="primary", width="stretch",
                         icon=":material/check_circle:", disabled=method is None):
                try:
                    receipt = user_ops.return_and_pay(
                        user_id, rental_id, return_station, distance_km, int(use_points), method
                    )
                except BusinessError as e:
                    st.error(str(e))
                else:
                    st.session_state["return_receipt"] = receipt
                    st.rerun()
            st.caption("금액은 결제 시점의 시각으로 다시 계산됩니다.")
