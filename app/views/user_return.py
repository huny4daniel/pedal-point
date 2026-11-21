"""이용자 · 반납·결제 (대여·반납 화면 안에서 상황에 따라 보여준다).

- 대여 중: 이용 중 카드 → ① 지도에서 반납 대여소 → ② 이동거리 → ③ 마일리지·결제수단 → 반납하고 결제 (return_and_pay)
- 결제 대기(반납은 됐지만 결제 없음): 마일리지·결제수단 → 결제 (pay_pending)
"""
from decimal import Decimal

import streamlit as st

import rules
import ui
import user_ops
from db import BusinessError
from station_map import markers_for, station_map

RET_KEY = "return_station"
PAY_KEY = "pay_rental"  # 결제 대기 건을 결제하는 중이면 그 rental_id


def show_receipt(r: dict) -> None:
    ui.done("결제가 완료되었습니다",
            f"이번 이동으로 탄소 {ui.carbon(r['carbon_g'])}을 줄이고 {ui.pt(r['earned'])}를 적립했어요.")
    if r["carbon_g"]:
        total = user_ops.my_summary(st.session_state["user_id"])["carbon_g"]
        before, after = rules.carbon_level(total - r["carbon_g"]), rules.carbon_level(total)
        grew = after["step"] > before["step"]
        st.markdown(
            f'<div class="pp-eco"><div class="pp-eco-head"><b>'
            + (f"🎉 나의 숲이 {after['icon']} {after['name']}(으)로 자랐어요!" if grew
               else f"{after['icon']} 이번 이동으로 줄인 탄소 {ui.carbon(r['carbon_g'])}")
            + f"</b><span>누적 {ui.carbon(total)}</span></div>"
            + ui.carbon_equiv_chips(r["carbon_g"])
            + f'<div class="pp-eco-bar"><i style="width:{after["progress"] * 100:.0f}%"></i></div>'
            + '<div class="pp-eco-note">'
            + (f"다음 단계 {after['next_icon']} {after['next_name']}까지 {ui.carbon(after['remain_g'])}"
               if after["next_name"] else "가장 높은 단계에 도착했어요!")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    ui.stat_cards([
        ("적립 마일리지", ui.pt(r["earned"]), "", True),
        ("탄소 절감량", ui.carbon(r["carbon_g"]), "", False),
        ("최종 결제금액", ui.won(r["final"]), "", False),
        ("결제 후 보유 마일리지", ui.pt(r["balance_after"]), "", False),
    ])
    with st.container(key="ppcard_receipt_done"):
        ui.card_title("결제 영수증", f"대여번호 {r['rental_id']}")
        ui.calc_rows(
            [
                ("이용시간", ui.minutes(r["minutes"])),
                ("이동거리", ui.km(r["distance"])),
                ("이용금액", ui.won(r["amount"])),
                ("마일리지 할인", f"- {ui.won(r['discount'])}"),
            ],
            ("최종금액", ui.won(r["final"])),
        )
    c1, c2 = st.columns(2)
    if c1.button("확인", type="primary", icon=":material/check:", width="stretch"):
        st.rerun()
    if c2.button("이용 내역 보기", icon=":material/receipt_long:", width="stretch"):
        ui.go("mypage")


def _ride_card(r: dict) -> None:
    minutes = rules.usage_minutes(r["rental_start_time"], r["now"])
    st.markdown(
        f'<div class="pp-ride"><div class="pp-ride-dot">🚲</div><div class="pp-ride-main">'
        f'<div class="pp-ride-tag">이용 중</div>'
        f'<div class="pp-ride-title">자전거 #{r["rental_bicycle_id"]}</div>'
        f'<div class="pp-ride-sub">{ui.esc(r["start_station"])}에서 {ui.dt(r["rental_start_time"])} 출발</div></div>'
        f'<div class="pp-ride-num"><b>{ui.minutes(minutes)}</b>'
        f'<span>현재 요금 {ui.won(rules.usage_fee(r["rental_start_time"], r["now"]))}</span></div></div>',
        unsafe_allow_html=True,
    )


def _steps(active: int, labels: list[str]) -> None:
    st.markdown(
        '<div class="pp-steps">'
        + "".join(f'<div class="pp-step{" on" if i <= active else ""}">{i + 1}. {t}</div>'
                  for i, t in enumerate(labels))
        + "</div>",
        unsafe_allow_html=True,
    )


def _pay_panel(user_id: int, rental: dict, is_ongoing: bool, start, end, distance_km,
               return_station: int | None, pay_box, summary_box) -> None:
    """마일리지·결제수단 입력(pay_box)과 결제 요약·버튼(summary_box)."""
    amount = rules.usage_fee(start, end)
    earned = rules.earn_points(distance_km)
    balance = user_ops.mileage_balance(user_id)
    limit = rules.discount_limit(amount, balance)

    with pay_box, st.container(key="ppcard_pay"):
        ui.card_title("마일리지 사용·결제수단", f"보유 {ui.pt(balance)} · 이번 결제에 최대 {ui.pt(limit)} 사용 가능")
        pkey = f"use_points_{rental['rental_id']}"
        c3, c4 = st.columns([3, 1], vertical_alignment="bottom")
        use_points = c3.number_input("사용할 마일리지 (P)", min_value=0, max_value=max(limit, 0), step=10,
                                     disabled=limit == 0, key=pkey)
        c4.button("전액", disabled=limit == 0, width="stretch", key=f"all_{pkey}",
                  on_click=lambda: st.session_state.update({pkey: limit}))
        method = st.segmented_control("결제수단", rules.PAYMENT_METHODS, default=rules.PAYMENT_METHODS[0],
                                      width="stretch", key="pay_method")

    with summary_box, st.container(key="ppcard_summary"):
        ui.card_title("결제 요약", f"{ui.dt(end)} 기준" if is_ongoing else f"대여번호 {rental['rental_id']}")
        ui.calc_rows(
            [
                ("이용시간", ui.minutes(rules.usage_minutes(start, end))),
                ("이용금액", ui.won(amount)),
                ("마일리지 할인", f"- {ui.won(use_points)}"),
            ],
            ("최종금액", ui.won(amount - use_points)),
        )
        st.markdown(f'<div class="pp-fee"><span>🌱 적립 예정 {ui.pt(earned)}</span>'
                    f'<span>탄소 {ui.carbon(rules.carbon_saved_g(distance_km))} 절감</span></div>'
                    + ui.carbon_equiv_chips(rules.carbon_saved_g(distance_km)),
                    unsafe_allow_html=True)
        need_station = is_ongoing and return_station is None
        label = "반납 대여소를 먼저 고르세요" if need_station else ("반납하고 결제하기" if is_ongoing else "결제하기")
        if st.button(label, type="primary", width="stretch", icon=":material/check_circle:",
                     disabled=method is None or need_station, key="pay_go"):
            try:
                if is_ongoing:
                    receipt = user_ops.return_and_pay(
                        user_id, rental["rental_id"], return_station, distance_km, int(use_points), method
                    )
                else:
                    receipt = user_ops.pay_pending(user_id, rental["rental_id"], int(use_points), method)
            except BusinessError as e:
                st.error(str(e))
            else:
                st.session_state.pop(RET_KEY, None)
                st.session_state.pop(PAY_KEY, None)
                st.session_state["return_receipt"] = receipt
                st.rerun()
        st.caption(f"기본 {rules.BASE_MINUTES}분 {ui.won(rules.BASE_FEE)}, 초과 {rules.EXTRA_UNIT_MINUTES}분마다 "
                   f"{ui.won(rules.EXTRA_UNIT_FEE)}" + (" · 결제 시점 시각으로 다시 계산돼요." if is_ongoing else ""))


def render_return(user_id: int, rental: dict, notice: str | None = None) -> None:
    """대여 중일 때: 반납 대여소·이동거리 입력과 결제. notice는 방금 대여한 경우의 안내."""
    mobile = ui.is_mobile()
    ui.page_header("이용 중", "반납하기", "도착한 대여소를 지도에서 고르고, 마일리지로 할인받아 결제하세요.")
    if notice:
        ui.done(notice, "도착하면 이 화면에서 반납 대여소를 고르고 결제하세요.")
    _ride_card(rental)

    left, right = (st.container(), st.container()) if mobile else st.columns([1.5, 1], gap="large")
    with left:
        stations = user_ops.return_stations()
        by_id = {s["station_id"]: s for s in stations}
        if st.session_state.get(RET_KEY) not in by_id:
            st.session_state.pop(RET_KEY, None)
        return_station = st.session_state.get(RET_KEY)
        _steps(0 if return_station is None else 1, ["반납 대여소", "이동거리", "결제"])

        with st.container(key="ppcard_return_map"):
            ui.card_title("반납할 대여소를 지도에서 눌러 주세요",
                          "핀 안의 숫자는 빈 거치대 수예요. 빈 거치대가 있는 운영 중 대여소만 보여요.")
            markers, missing = markers_for(stations, "free_docks", lambda s, c: "blue")
            ev = station_map("return_map", markers, return_station, height=320 if mobile else 380)
            if "select" in ev and ev["select"] != return_station:
                st.session_state[RET_KEY] = ev["select"]
                st.rerun()
            for s in missing:
                if st.button(s["station_name"], key=f"ret_nomap_{s['station_id']}", icon=":material/location_off:"):
                    st.session_state[RET_KEY] = s["station_id"]
                    st.rerun()
            if return_station:
                s = by_id[return_station]
                st.success(f"반납 대여소: **{s['station_name']}** · 빈 거치대 {int(s['free_docks'])}",
                           icon=":material/where_to_vote:")

        with st.container(key="ppcard_distance"):
            ui.card_title("이동거리 (km)", "자전거 GPS 기록 대신 직접 입력해요. 단위는 킬로미터(km)예요.")
            c1, c2 = st.columns([4, 1], vertical_alignment="center")
            distance = c1.number_input("이동거리 (km)", min_value=0.0, max_value=float(rules.MAX_DISTANCE_KM),
                                       value=0.0, step=0.1, format="%.2f", label_visibility="collapsed")
            c2.markdown('<div class="pp-unit">km</div>', unsafe_allow_html=True)
            st.caption(f"예: 3.25 = 3.25km (3,250m) · 0 ~ {rules.MAX_DISTANCE_KM}km, 소수점 둘째 자리까지 · "
                       f"1km당 {rules.POINTS_PER_KM}P 적립")
        pay_box = st.container()
    _pay_panel(user_id, rental, True, rental["rental_start_time"], rental["now"], Decimal(f"{distance:.2f}"),
               return_station, pay_box, right)


def render_pending(user_id: int, rental: dict) -> None:
    """결제 대기 건 결제."""
    mobile = ui.is_mobile()
    ui.page_header("결제 대기", "결제하기", "반납은 끝났어요. 결제하면 마일리지가 적립돼요.")
    if st.button("대여 화면으로", icon=":material/arrow_back:"):
        st.session_state.pop(PAY_KEY, None)
        st.rerun()
    left, right = (st.container(), st.container()) if mobile else st.columns([1.5, 1], gap="large")
    with left:
        with st.container(key="ppcard_return_done"):
            ui.card_title(f"자전거 #{rental['rental_bicycle_id']} · 대여번호 {rental['rental_id']}")
            ui.calc_rows([
                ("출발", f"{rental['start_station']} · {ui.dt(rental['rental_start_time'])}"),
                ("반납", f"{rental['return_station']} · {ui.dt(rental['rental_end_time'])}"),
                ("이동거리", ui.km(rental["rental_distance"])),
            ])
        pay_box = st.container()
    _pay_panel(user_id, rental, False, rental["rental_start_time"], rental["rental_end_time"],
               rental["rental_distance"], None, pay_box, right)


def pending_banner(pending: list[dict]) -> None:
    """대여 화면 위: 결제하지 않은 대여 안내와 바로 결제 버튼."""
    with st.container(key="ppcard_pending"):
        st.markdown(f"**결제하지 않은 대여가 {len(pending)}건 있어요**")
        for r in pending:
            c1, c2 = st.columns([3, 1], vertical_alignment="center")
            c1.caption(f"자전거 #{r['rental_bicycle_id']} · {r['start_station']} → {r['return_station']} · "
                       f"{ui.dt(r['rental_end_time'])} 반납")
            if c2.button("결제하기", key=f"pay_{r['rental_id']}", width="stretch", type="primary"):
                st.session_state[PAY_KEY] = r["rental_id"]
                st.rerun()
