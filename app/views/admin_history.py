"""관리자 · 내역 조회: 대여·결제·마일리지 내역 (기간·회원·대여소 필터, 대여소 기본값 = 담당 대여소)."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import admin_ops
import ui


def _who(r: dict) -> str:
    return f"{r['user_name']} ({r['user_login_id']})"


def render() -> None:
    ui.page_header("관리자", "내역 조회", "대여·결제·마일리지 내역을 기간·회원·대여소별로 조회합니다.")

    stations = admin_ops.all_stations()
    staff = admin_ops.get_staff(st.session_state["staff_id"])
    s_names = {s["station_id"]: s["station_name"] for s in stations}
    s_options = [None, *s_names]
    home = staff["staff_station_id"] if staff and staff["staff_station_id"] in s_names else None

    filters = st.container(key="ppcard_filters")
    c1, c2, c3 = filters.columns([2, 1, 1])
    today = date.today()
    period = c1.date_input("기간", (today - timedelta(days=30), today), max_value=today)
    member = c2.text_input("회원 (아이디 또는 이름)", placeholder="비우면 전체", icon=":material/search:")
    station_id = c3.selectbox("대여소 (출발·반납)", s_options, index=s_options.index(home),
                              format_func=lambda i: "전체" if i is None else s_names[i]
                              + (" (담당)" if i == home else ""))
    if not isinstance(period, tuple) or len(period) != 2:
        st.info("기간의 시작일과 종료일을 모두 선택해 주세요.")
        return
    start, end = period
    st.write("")

    t1, t2, t3 = st.tabs(["대여", "결제", "마일리지"])

    with t1:
        rows = admin_ops.search_rentals(start, end, member, station_id)
        states = [ui.rental_state(r) for r in rows]
        total_km = sum(r["rental_distance"] for r in rows if r["rental_distance"] is not None)
        st.caption(f"{len(rows)}건 · 반납 완료 {states.count('반납 완료')} · 결제 대기 {states.count('결제 대기')} · "
                   f"대여 중 {states.count('대여 중')} · 총 이동거리 {ui.km(total_km)}")
        if rows:
            st.dataframe(pd.DataFrame({
                "대여번호": [r["rental_id"] for r in rows],
                "회원": [_who(r) for r in rows],
                "대여 시각": [ui.dt(r["rental_start_time"]) for r in rows],
                "반납 시각": [ui.dt(r["rental_end_time"]) for r in rows],
                "상태": states,
                "출발 대여소": [r["start_station"] for r in rows],
                "반납 대여소": [r["return_station"] or "-" for r in rows],
                "자전거": [f"#{r['rental_bicycle_id']}" for r in rows],
                "이동거리": [ui.km(r["rental_distance"]) for r in rows],
            }), hide_index=True, width="stretch")

    with t2:
        rows = admin_ops.search_payments(start, end, member, station_id)
        st.caption(f"{len(rows)}건 · 결제액 합계 {ui.won(sum(r['payment_final_amount'] for r in rows))}")
        if rows:
            cols = ("이용금액(원)", "할인액(원)", "결제액(원)")
            st.dataframe(pd.DataFrame({
                "결제번호": [r["payment_id"] for r in rows],
                "결제 일시": [ui.dt(r["payment_at"]) for r in rows],
                "대여번호": [r["payment_rental_id"] for r in rows],
                "회원": [_who(r) for r in rows],
                "출발 → 반납": [f"{r['start_station']} → {r['return_station']}" for r in rows],
                cols[0]: [r["payment_amount"] for r in rows],
                cols[1]: [r["payment_discount"] for r in rows],
                cols[2]: [r["payment_final_amount"] for r in rows],
                "결제수단": [r["payment_method"] for r in rows],
            }), hide_index=True, width="stretch",
                column_config={k: st.column_config.NumberColumn(k, format="localized") for k in cols})

    with t3:
        rows = admin_ops.search_mileage(start, end, member, station_id)
        earned = sum(int(r["point"]) for r in rows if r["point"] > 0)
        used = -sum(int(r["point"]) for r in rows if r["point"] < 0)
        st.caption(f"{len(rows)}건 · 적립 {ui.pt(earned)} · 사용 {ui.pt(used)}")
        if rows:
            st.dataframe(pd.DataFrame({
                "일시": [ui.dt(r["at"]) for r in rows],
                "회원": [_who(r) for r in rows],
                "구분": [r["kind"] for r in rows],
                "포인트(P)": [int(r["point"]) for r in rows],
                "대여번호": [r["rental_id"] for r in rows],
            }), hide_index=True, width="stretch",
                column_config={"포인트(P)": st.column_config.NumberColumn("포인트(P)", format="%+d")})
