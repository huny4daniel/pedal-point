"""관리자 · 회원 관리·통계: 회원 상태 변경, 탄소 절감·마일리지 통계."""
import pandas as pd
import streamlit as st

import admin_ops
import ui
from db import BusinessError

USER_STATUSES = ["ACTIVE", "SUSPENDED", "WITHDRAWN"]


def _members_tab() -> None:
    ui.flash("member_msg")

    users = admin_ops.all_users()
    st.dataframe(pd.DataFrame({
        "ID": [u["user_id"] for u in users],
        "이름": [u["user_name"] for u in users],
        "생년월일": [u["user_birth_date"].isoformat() if u["user_birth_date"] else "-" for u in users],
        "전화번호": [u["user_phone"] for u in users],
        "주소": [u["user_address"] or "-" for u in users],
        "상태": [ui.label(u["user_status"]) for u in users],
        "가입일": [ui.dt(u["user_created_at"]) for u in users],
        "마일리지 잔액(P)": [int(u["balance"]) for u in users],
    }), hide_index=True, width="stretch")

    st.write("")
    by_id = {u["user_id"]: u for u in users}
    with st.container(key="ppcard_member_status"), st.form("user_status_form", border=False):
        ui.card_title("회원 상태 변경", "이용정지 회원은 대여할 수 없고, 탈퇴 회원은 로그인 목록에서 빠집니다.")
        c1, c2, c3 = st.columns([2, 1.3, 0.8], vertical_alignment="bottom")
        uid = c1.selectbox(
            "회원", list(by_id),
            format_func=lambda i: f"{by_id[i]['user_name']} (ID {i}) · {ui.label(by_id[i]['user_status'])}",
        )
        new_status = c2.selectbox("변경할 상태", USER_STATUSES, format_func=ui.label)
        if c3.form_submit_button("변경", type="primary", width="stretch"):
            try:
                admin_ops.change_user_status(uid, new_status)
            except BusinessError as e:
                st.error(str(e))
            else:
                st.session_state["member_msg"] = (
                    f"{by_id[uid]['user_name']} 회원 상태를 {ui.label(new_status)}(으)로 바꿨습니다."
                )
                st.rerun()


def _stats_tab() -> None:
    s = admin_ops.statistics()
    ui.stat_cards([
        ("누적 탄소 절감량", ui.carbon(s["carbon_g"]), "", True),
        ("누적 이동거리", ui.km(s["total_km"]), "", False),
        ("반납 완료 대여", f"{s['rental_count']:,}", "건", False),
    ])
    ui.stat_cards([
        ("총 적립 마일리지", ui.pt(s["earned"]), "", False),
        ("총 사용 마일리지", ui.pt(s["used"]), "", False),
        ("미사용 잔액 합계", ui.pt(s["balance"]), "", False),
    ])

    rows = admin_ops.user_statistics()
    with st.container(key="ppcard_chart"):
        ui.card_title("이용자별 탄소 절감량", "반납 완료된 대여의 이동거리 기준 (g)")
        st.bar_chart(
            pd.DataFrame({
                "이용자": [r["user_name"] for r in rows],
                "탄소 절감량(g)": [float(r["carbon_g"]) for r in rows],
            }).sort_values("탄소 절감량(g)", ascending=False),
            x="이용자", y="탄소 절감량(g)", height=260, sort=False,
        )
    st.write("")
    st.dataframe(pd.DataFrame({
        "이용자": [f"{r['user_name']} ({r['user_id']})" for r in rows],
        "반납 대여 수": [r["rental_count"] for r in rows],
        "이동거리": [ui.km(r["total_km"]) for r in rows],
        "탄소 절감량": [ui.carbon(r["carbon_g"]) for r in rows],
        "적립(P)": [int(r["total_earned"]) for r in rows],
        "사용(P)": [int(r["total_used"]) for r in rows],
        "잔액(P)": [int(r["balance"]) for r in rows],
    }), hide_index=True, width="stretch")


def render() -> None:
    ui.page_header("관리자", "회원 관리·통계", "회원 상태를 바꾸고 누적 탄소 절감량과 마일리지 통계를 봅니다.")
    t1, t2 = st.tabs(["회원 관리", "통계"])
    with t1:
        _members_tab()
    with t2:
        _stats_tab()
