"""이용자 · 홈 대시보드.

- 머리말 배너: 인사와 보유 마일리지
- 행동 카드: 이용 중이면 현재 이용 정보 + 반납하기, 결제 대기가 있으면 결제하기, 그 밖에는 이용하기
- 이번 달 정보 패널: 이용 횟수·이동거리·줄인 탄소·적립/사용 마일리지·결제액
- 이번 달 일별 이동거리, 최근 이용·마일리지 내역
"""
from datetime import date

import pandas as pd
import streamlit as st

import rules
import ui
import user_ops
from views import user_return


def _action_card(user_id: int) -> None:
    ongoing = user_ops.ongoing_rentals(user_id)
    pending = user_ops.pending_rentals(user_id)
    if ongoing:
        r = ongoing[0]
        minutes = rules.usage_minutes(r["rental_start_time"], r["now"])
        fee = rules.usage_fee(r["rental_start_time"], r["now"])
        st.markdown(
            f'<div class="pp-action riding"><div class="pp-action-tag">● 이용 중</div>'
            f'<div class="pp-action-title">자전거 #{r["rental_bicycle_id"]}</div>'
            f'<div class="pp-action-sub">{ui.esc(r["start_station"])}에서 {ui.dt(r["rental_start_time"])} 출발</div>'
            f'<div class="pp-action-nums"><div><b>{ui.minutes(minutes)}</b><span>이용 시간</span></div>'
            f'<div><b>{ui.won(fee)}</b><span>현재 요금</span></div>'
            f'<div><b>대여 {r["rental_id"]}</b><span>대여번호</span></div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("반납하기", type="primary", width="stretch", icon=":material/keyboard_return:", key="home_return"):
            ui.go("ride")
    elif pending:
        r = pending[0]
        st.markdown(
            f'<div class="pp-action pending"><div class="pp-action-tag">● 결제 대기 {len(pending)}건</div>'
            f'<div class="pp-action-title">결제하지 않은 대여가 있어요</div>'
            f'<div class="pp-action-sub">자전거 #{r["rental_bicycle_id"]} · {ui.esc(r["start_station"])} → '
            f'{ui.esc(r["return_station"])} · {ui.dt(r["rental_end_time"])} 반납</div>'
            f'<div class="pp-action-nums"><div><b>{ui.won(rules.usage_fee(r["rental_start_time"], r["rental_end_time"]))}</b>'
            f'<span>결제할 요금</span></div><div><b>{ui.km(r["rental_distance"])}</b><span>이동거리</span></div>'
            f'<div><b>+{ui.pt(rules.earn_points(r["rental_distance"]))}</b><span>적립 예정</span></div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("결제하기", type="primary", width="stretch", icon=":material/payments:", key="home_pay"):
            st.session_state[user_return.PAY_KEY] = r["rental_id"]
            ui.go("ride")
    else:
        s = user_ops.service_stats()
        st.markdown(
            f'<div class="pp-action"><div class="pp-action-tag">● 지금 바로</div>'
            f'<div class="pp-action-title">자전거 이용하기</div>'
            f'<div class="pp-action-sub">가까운 대여소에서 빌리고, 탄 만큼 마일리지를 모으세요.</div>'
            f'<div class="pp-action-nums"><div><b>{s["bikes"]}대</b><span>대여 가능</span></div>'
            f'<div><b>{s["stations"]}곳</b><span>운영 대여소</span></div>'
            f'<div><b>{ui.won(rules.BASE_FEE)}</b><span>기본 {rules.BASE_MINUTES}분</span></div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("이용하기", type="primary", width="stretch", icon=":material/pedal_bike:", key="home_ride"):
            ui.go("ride")


def _month_panel(m: dict) -> None:
    tiles = [
        ("이용 횟수", f"{int(m['rides'])}회", "🚲"),
        ("이동거리", ui.km(m["km"]), "📍"),
        ("줄인 탄소", ui.carbon(rules.carbon_saved_g(m["km"])), "🌱"),
        ("적립 마일리지", f"+{ui.pt(m['earned'])}", "⬆️"),
        ("사용 마일리지", f"−{ui.pt(m['used'])}", "⬇️"),
        ("결제액", ui.won(m["paid"]), "💳"),
    ]
    with st.container(key="ppcard_month"):
        ui.card_title(f"{m['y']}년 {m['mo']}월 이용 현황", "이번 달 1일부터 지금까지")
        st.markdown(
            '<div class="pp-tiles">'
            + "".join(f'<div class="pp-tile"><i>{icon}</i><b>{v}</b><span>{k}</span></div>' for k, v, icon in tiles)
            + "</div>",
            unsafe_allow_html=True,
        )


def _daily_chart(user_id: int, m: dict) -> None:
    rows = user_ops.month_daily_km(user_id)
    with st.container(key="ppcard_daily"):
        ui.card_title("이번 달 일별 이동거리", "반납 완료된 이용 기준 (km)")
        if not rows:
            ui.empty("📈", "이번 달 이용 기록이 아직 없어요", "자전거를 타면 여기에 쌓여요.")
            return
        first = date(int(m["y"]), int(m["mo"]), 1)
        last = max(date.today(), max(r["day"] for r in rows))
        days = pd.date_range(first, last, freq="D")
        km = {r["day"]: float(r["km"]) for r in rows}
        st.bar_chart(
            pd.DataFrame({"날짜": days.strftime("%m/%d"), "이동거리(km)": [km.get(d.date(), 0.0) for d in days]}),
            x="날짜", y="이동거리(km)", height=210, color="#12B76A",
        )


def _recent(user_id: int) -> None:
    rentals = user_ops.my_rentals(user_id)[:5]
    mileage = user_ops.my_mileage(user_id)[:5]
    c1, c2 = (st.container(), st.container()) if ui.is_mobile() else st.columns(2, gap="medium")
    with c1, st.container(key="ppcard_recent_rides"):
        ui.card_title("최근 이용")
        if rentals:
            ui.list_items([
                (f"{ui.esc(r['start_station'])} → {ui.esc(r['return_station'] or '이용 중')}",
                 ui.badge(ui.rental_state(r)),
                 f"{ui.dt(r['rental_start_time'])} · 자전거 #{r['rental_bicycle_id']}"
                 + (f" · {ui.km(r['rental_distance'])}" if r["rental_distance"] is not None else ""), False)
                for r in rentals
            ])
        else:
            ui.empty("🚲", "아직 이용 기록이 없어요")
    with c2, st.container(key="ppcard_recent_mileage"):
        ui.card_title("최근 마일리지")
        if mileage:
            ui.list_items([
                (f"{r['kind']} · 대여 {r['rental_id']}",
                 ("+" if r["point"] > 0 else "−") + ui.pt(abs(r["point"])), ui.dt(r["at"]), r["point"] > 0)
                for r in mileage
            ])
        else:
            ui.empty("🌱", "아직 마일리지 내역이 없어요")
    if st.button("전체 내역 보기", icon=":material/receipt_long:", key="home_history"):
        ui.go("mypage")


def _impact(user_id: int, m: dict) -> None:
    total = user_ops.my_summary(user_id)["carbon_g"]
    community = rules.carbon_saved_g(user_ops.service_stats()["total_km"])
    ui.carbon_impact(total, rules.carbon_saved_g(m["km"]), user_ops.carbon_rank(user_id), community)


def render() -> None:
    user_id = st.session_state["user_id"]
    me = user_ops.get_user(user_id)
    m = user_ops.month_summary(user_id)
    ui.page_header(
        "홈", f"{ui.esc(me['user_name'])}님, 안녕하세요",
        "" if ui.is_mobile() else "오늘도 자전거로 탄소를 줄이고 마일리지를 모아 보세요.",
        stats=[("보유 마일리지", ui.pt(me["user_mileage"])), ("이번 달 이용", f"{int(m['rides'])}회"),
               ("이번 달 줄인 탄소", ui.carbon(rules.carbon_saved_g(m["km"])))],
    )
    if me["user_status"] != "ACTIVE":
        st.warning("이용이 정지된 회원입니다. 관리자에게 문의해 주세요.", icon=":material/block:")

    if ui.is_mobile():
        _action_card(user_id)
        _impact(user_id, m)
        _month_panel(m)
        _daily_chart(user_id, m)
        _recent(user_id)
        return
    left, right = st.columns([1, 1.35], gap="medium")
    with left:
        _action_card(user_id)
    with right:
        _month_panel(m)
    _impact(user_id, m)
    _daily_chart(user_id, m)
    _recent(user_id)
