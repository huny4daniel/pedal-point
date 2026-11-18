"""이용자 · 마이페이지: 대여·결제 내역, 마일리지 잔액·내역, 누적 탄소 절감량."""
import pandas as pd
import streamlit as st

import rules
import ui
import user_ops


def _rentals(rows: list[dict]) -> None:
    if ui.is_app():
        ui.list_items([
            (
                f"{r['start_station']} → {r['return_station'] or '반납 전'}",
                ui.badge(r["rental_status"]),
                f"{ui.dt(r['rental_start_time'])} · 자전거 #{r['rental_bicycle_id']}"
                + (f" · {ui.km(r['rental_distance'])}" if r["rental_distance"] is not None else ""),
                False,
            )
            for r in rows
        ])
        return
    st.dataframe(pd.DataFrame({
        "대여번호": [r["rental_id"] for r in rows],
        "상태": [ui.label(r["rental_status"]) for r in rows],
        "대여 시각": [ui.dt(r["rental_start_time"]) for r in rows],
        "반납 시각": [ui.dt(r["rental_end_time"]) for r in rows],
        "대여소": [r["start_station"] for r in rows],
        "반납 대여소": [r["return_station"] or "-" for r in rows],
        "자전거": [f"#{r['rental_bicycle_id']}" for r in rows],
        "이동거리": [ui.km(r["rental_distance"]) for r in rows],
    }), hide_index=True, width="stretch")


def _payments(rows: list[dict]) -> None:
    if ui.is_app():
        ui.list_items([
            (
                f"대여 {r['payment_rental_id']} 이용요금",
                ui.won(r["payment_final_amount"]),
                f"{ui.dt(r['payment_at'])} · {rules.PAYMENT_METHODS[r['payment_method']]}"
                + (f" · 마일리지 할인 {ui.won(r['payment_discount'])}" if r["payment_discount"] else ""),
                False,
            )
            for r in rows
        ])
        return
    st.dataframe(pd.DataFrame({
        "결제번호": [r["payment_id"] for r in rows],
        "결제 일시": [ui.dt(r["payment_at"]) for r in rows],
        "대여번호": [r["payment_rental_id"] for r in rows],
        "이용금액(원)": [r["payment_amount"] for r in rows],
        "할인액(원)": [r["payment_discount"] for r in rows],
        "최종금액(원)": [r["payment_final_amount"] for r in rows],
        "결제수단": [rules.PAYMENT_METHODS[r["payment_method"]] for r in rows],
    }), hide_index=True, width="stretch",
        column_config={k: st.column_config.NumberColumn(k, format="localized")
                       for k in ("이용금액(원)", "할인액(원)", "최종금액(원)")})


def _mileage(rows: list[dict]) -> None:
    def related(r: dict) -> str:
        return f"대여 {r['mileage_rental_id']}" if r["mileage_rental_id"] else f"결제 {r['mileage_payment_id']}"

    if ui.is_app():
        ui.list_items([
            (
                f"{ui.label(r['mileage_type'])} · {related(r)}",
                ("+" if r["mileage_type"] == "EARN" else "−") + ui.pt(r["mileage_point"]),
                ui.dt(r["mileage_created_at"]),
                r["mileage_type"] == "EARN",
            )
            for r in rows
        ])
        return
    st.dataframe(pd.DataFrame({
        "일시": [ui.dt(r["mileage_created_at"]) for r in rows],
        "구분": [ui.label(r["mileage_type"]) for r in rows],
        "포인트(P)": [r["mileage_point"] if r["mileage_type"] == "EARN" else -r["mileage_point"]
                 for r in rows],
        "관련": [related(r) for r in rows],
    }), hide_index=True, width="stretch",
        column_config={"포인트(P)": st.column_config.NumberColumn("포인트(P)", format="%+d")})


def render() -> None:
    user_id = st.session_state["user_id"]
    ui.page_header("이용자", "마이페이지", "내 이용 기록과 마일리지, 지금까지 줄인 탄소량을 확인합니다.")

    s = user_ops.my_summary(user_id)
    ui.stat_cards([
        ("사용 가능한 마일리지", ui.pt(s["balance"]), "", True),
        ("누적 탄소 절감량", ui.carbon(s["carbon_g"]), "", False),
        ("누적 이동거리", ui.km(s["total_km"]), "", False),
        ("총 적립 / 총 사용", f"{int(s['total_earned']):,} / {int(s['total_used']):,}", "P", False),
    ])

    t1, t2, t3 = st.tabs(["대여 내역", "결제 내역", "마일리지"] if ui.is_app()
                         else ["대여 내역", "결제 내역", "마일리지 내역"])
    with t1:
        rows = user_ops.my_rentals(user_id)
        _rentals(rows) if rows else ui.empty("🚲", "대여 내역이 없습니다")
    with t2:
        rows = user_ops.my_payments(user_id)
        _payments(rows) if rows else ui.empty("💳", "결제 내역이 없습니다")
    with t3:
        rows = user_ops.my_mileage(user_id)
        _mileage(rows) if rows else ui.empty("🌱", "마일리지 내역이 없습니다")
