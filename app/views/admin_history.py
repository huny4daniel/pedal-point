"""관리자 · 내역 조회: 대여·결제·마일리지 내역 검색 (기간·사용자·대여소별)."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import admin_ops
import rules
import ui


def render() -> None:
    ui.page_header("관리자", "내역 조회", "대여·결제·마일리지 내역을 기간·사용자·대여소별로 검색합니다.")

    users = admin_ops.all_users()
    stations = admin_ops.all_stations()
    u_names = {u["user_id"]: f"{u['user_name']} (ID {u['user_id']})" for u in users}
    s_names = {s["station_id"]: s["station_name"] for s in stations}

    filters = st.container(key="ppcard_filters")
    c1, c2, c3 = filters.columns([2, 1, 1])
    today = date.today()
    period = c1.date_input("기간", (today - timedelta(days=30), today), max_value=today)
    user_id = c2.selectbox("사용자", [None, *u_names],
                           format_func=lambda i: "전체" if i is None else u_names[i])
    station_id = c3.selectbox("대여소 (대여·반납)", [None, *s_names],
                              format_func=lambda i: "전체" if i is None else s_names[i])
    if not isinstance(period, tuple) or len(period) != 2:
        st.info("기간의 시작일과 종료일을 모두 선택해 주세요.")
        return
    start, end = period
    st.write("")

    t1, t2, t3 = st.tabs(["대여 내역", "결제 내역", "마일리지 내역"])

    with t1:
        rows = admin_ops.search_rentals(start, end, user_id, station_id)
        st.caption(f"{len(rows)}건")
        if rows:
            st.dataframe(pd.DataFrame({
                "대여번호": [r["rental_id"] for r in rows],
                "이용자": [f"{r['user_name']} ({r['user_id']})" for r in rows],
                "대여 시각": [ui.dt(r["rental_start_time"]) for r in rows],
                "반납 시각": [ui.dt(r["rental_end_time"]) for r in rows],
                "상태": [ui.label(r["rental_status"]) for r in rows],
                "대여 대여소": [r["start_station"] for r in rows],
                "반납 대여소": [r["return_station"] or "-" for r in rows],
                "자전거": [f"#{r['rental_bicycle_id']}" for r in rows],
                "이동거리": [ui.km(r["rental_distance"]) for r in rows],
            }), hide_index=True, width="stretch")

    with t2:
        rows = admin_ops.search_payments(start, end, user_id, station_id)
        st.caption(f"{len(rows)}건 · 최종금액 합계 {ui.won(sum(r['payment_final_amount'] for r in rows))}")
        if rows:
            cols = ("이용금액(원)", "할인액(원)", "최종금액(원)")
            st.dataframe(pd.DataFrame({
                "결제번호": [r["payment_id"] for r in rows],
                "결제 일시": [ui.dt(r["payment_at"]) for r in rows],
                "대여번호": [r["payment_rental_id"] for r in rows],
                "이용자": [f"{r['user_name']} ({r['user_id']})" for r in rows],
                "대여 → 반납": [f"{r['start_station']} → {r['return_station']}" for r in rows],
                cols[0]: [r["payment_amount"] for r in rows],
                cols[1]: [r["payment_discount"] for r in rows],
                cols[2]: [r["payment_final_amount"] for r in rows],
                "결제수단": [rules.PAYMENT_METHODS[r["payment_method"]] for r in rows],
            }), hide_index=True, width="stretch",
                column_config={k: st.column_config.NumberColumn(k, format="localized") for k in cols})

    with t3:
        rows = admin_ops.search_mileage(start, end, user_id, station_id)
        earned = sum(r["mileage_point"] for r in rows if r["mileage_type"] == "EARN")
        used = sum(r["mileage_point"] for r in rows if r["mileage_type"] == "USE")
        st.caption(f"{len(rows)}건 · 적립 {ui.pt(earned)} · 사용 {ui.pt(used)}")
        if rows:
            st.dataframe(pd.DataFrame({
                "일시": [ui.dt(r["mileage_created_at"]) for r in rows],
                "이용자": [f"{r['user_name']} ({r['user_id']})" for r in rows],
                "구분": [ui.label(r["mileage_type"]) for r in rows],
                "포인트(P)": [r["mileage_point"] if r["mileage_type"] == "EARN" else -r["mileage_point"]
                           for r in rows],
                "관련": [f"대여 {r['mileage_rental_id']}" if r["mileage_rental_id"]
                       else f"결제 {r['mileage_payment_id']}" for r in rows],
                "대여번호": [r["related_rental_id"] for r in rows],
            }), hide_index=True, width="stretch",
                column_config={"포인트(P)": st.column_config.NumberColumn("포인트(P)", format="%+d")})
