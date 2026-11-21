"""관리자 · 회원 관리·통계: 회원 상태 변경, 탄소 절감·마일리지 통계."""
import pandas as pd
import streamlit as st

import admin_ops
import ui
from db import BusinessError

STATUS_LABELS = {"ACTIVE": "정상", "SUSPENDED": "이용정지", "WITHDRAWN": "탈퇴"}
LABEL_TO_STATUS = {v: k for k, v in STATUS_LABELS.items()}
EDITABLE = ["이름", "연락처", "상태"]


def _members_tab() -> None:
    ui.flash("member_msg")
    users = admin_ops.all_users()
    original = pd.DataFrame({
        "번호": [u["user_id"] for u in users],
        "아이디": [u["user_login_id"] for u in users],
        "이름": [u["user_name"] for u in users],
        "연락처": [u["user_phone"] for u in users],
        "상태": [STATUS_LABELS[u["user_status"]] for u in users],
        "대여 중": [bool(u["renting"]) for u in users],
        "보유 마일리지(P)": [int(u["user_mileage"]) for u in users],
        "가입일": [ui.dt(u["user_created_at"]) for u in users],
    })

    st.caption("이름·연락처·상태 칸을 더블클릭해서 바로 고친 뒤 ‘변경 저장’을 누르세요. "
               "대여 중인 회원은 정지·탈퇴로 바꿀 수 없고, 회원은 삭제하지 않습니다.")
    ver = st.session_state.get("member_editor_ver", 0)
    edited = st.data_editor(
        original, key=f"member_editor_{ver}", hide_index=True, width="stretch", height=460,
        num_rows="fixed",
        disabled=[c for c in original.columns if c not in EDITABLE],
        column_config={
            "번호": st.column_config.NumberColumn("번호", width="small"),
            "이름": st.column_config.TextColumn("이름 ✎", max_chars=50, required=True),
            "연락처": st.column_config.TextColumn("연락처 ✎", max_chars=20, required=True,
                                               validate=r"^010-\d{4}-\d{4}$"),
            "상태": st.column_config.SelectboxColumn("상태 ✎", options=list(LABEL_TO_STATUS), required=True),
            "대여 중": st.column_config.CheckboxColumn("대여 중", width="small"),
            "보유 마일리지(P)": st.column_config.NumberColumn("보유 마일리지(P)", format="localized"),
        },
    )

    changed = (edited[EDITABLE] != original[EDITABLE]).any(axis=1)
    rows = edited[changed]
    c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="center")
    if rows.empty:
        c1.caption("변경된 내용이 없습니다.")
    else:
        names = ", ".join(rows["아이디"].tolist()[:5]) + (" …" if len(rows) > 5 else "")
        c1.markdown(f"**변경 {len(rows)}명** · {names}")
    if c2.button("되돌리기", width="stretch", disabled=rows.empty, icon=":material/undo:"):
        st.session_state["member_editor_ver"] = ver + 1
        st.rerun()
    if c3.button("변경 저장", type="primary", width="stretch", disabled=rows.empty, icon=":material/save:"):
        try:
            n = admin_ops.update_users([
                {"user_id": int(r["번호"]), "user_login_id": r["아이디"], "user_name": r["이름"],
                 "user_phone": r["연락처"], "user_status": LABEL_TO_STATUS.get(r["상태"], r["상태"])}
                for _, r in rows.iterrows()
            ])
        except BusinessError as e:
            st.error(str(e) + " (아무것도 저장되지 않았습니다)")
        else:
            st.session_state["member_msg"] = f"회원 {n}명의 정보를 저장했습니다."
            st.session_state["member_editor_ver"] = ver + 1
            st.rerun()


def _stats_tab() -> None:
    s = admin_ops.statistics()
    ui.stat_cards([
        ("누적 탄소 절감량", ui.carbon(s["carbon_g"]), "", True),
        ("누적 이동거리", ui.km(s["total_km"]), "", False),
        ("반납 완료 대여", f"{int(s['rental_count']):,}", "건", False),
    ])
    ui.stat_cards([
        ("총 적립 마일리지", ui.pt(s["total_earned"]), "", False),
        ("총 사용 마일리지", ui.pt(s["total_used"]), "", False),
        ("보유 마일리지 합계", ui.pt(s["total_balance"]), "", False),
        ("총 결제액", ui.won(s["total_paid"]), "", False),
    ])

    rows = admin_ops.user_statistics()
    with st.container(key="ppcard_chart"):
        ui.card_title("회원별 탄소 절감량", "반납 완료된 대여의 이동거리 기준 (g)")
        st.bar_chart(
            pd.DataFrame({
                "회원": [r["user_name"] for r in rows],
                "탄소 절감량(g)": [float(r["carbon_g"]) for r in rows],
            }),
            x="회원", y="탄소 절감량(g)", height=260, sort=False,
        )
    st.write("")
    st.dataframe(pd.DataFrame({
        "회원": [f"{r['user_name']} ({r['user_login_id']})" for r in rows],
        "반납 대여 수": [r["rental_count"] for r in rows],
        "이동거리": [ui.km(r["total_km"]) for r in rows],
        "탄소 절감량": [ui.carbon(r["carbon_g"]) for r in rows],
        "보유 마일리지(P)": [int(r["user_mileage"]) for r in rows],
    }), hide_index=True, width="stretch")


def render() -> None:
    ui.page_header("관리자", "회원 관리·통계", "회원 상태를 바꾸고 누적 탄소 절감량과 마일리지 통계를 봅니다.")
    t1, t2 = st.tabs(["회원 관리", "통계"])
    with t1:
        _members_tab()
    with t2:
        _stats_tab()
