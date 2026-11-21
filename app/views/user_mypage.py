"""이용자 · 마이페이지: 대여·결제 내역, 마일리지 잔액·내역, 누적 탄소 절감량."""
import pandas as pd
import streamlit as st

import rules
import ui
import user_ops
from db import BusinessError


def _rentals(rows: list[dict]) -> None:
    if ui.is_mobile():
        ui.list_items([
            (
                f"{r['start_station']} → {r['return_station'] or '반납 전'}",
                ui.badge(ui.rental_state(r)),
                f"{ui.dt(r['rental_start_time'])} · 자전거 #{r['rental_bicycle_id']}"
                + (f" · {ui.km(r['rental_distance'])} · 🌱 {ui.carbon(rules.carbon_saved_g(r['rental_distance']))}"
                   if r["rental_distance"] is not None else ""),
                False,
            )
            for r in rows
        ])
        return
    st.dataframe(pd.DataFrame({
        "대여번호": [r["rental_id"] for r in rows],
        "상태": [ui.rental_state(r) for r in rows],
        "대여 시각": [ui.dt(r["rental_start_time"]) for r in rows],
        "반납 시각": [ui.dt(r["rental_end_time"]) for r in rows],
        "대여소": [r["start_station"] for r in rows],
        "반납 대여소": [r["return_station"] or "-" for r in rows],
        "자전거": [f"#{r['rental_bicycle_id']}" for r in rows],
        "이동거리": [ui.km(r["rental_distance"]) for r in rows],
        "줄인 탄소": ["-" if r["rental_distance"] is None else ui.carbon(rules.carbon_saved_g(r["rental_distance"]))
                  for r in rows],
    }), hide_index=True, width="stretch")


def _payments(rows: list[dict]) -> None:
    if ui.is_mobile():
        ui.list_items([
            (
                f"대여 {r['payment_rental_id']} 이용요금",
                ui.won(r["payment_final_amount"]),
                f"{ui.dt(r['payment_at'])} · {r['payment_method']}"
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
        "결제수단": [r["payment_method"] for r in rows],
    }), hide_index=True, width="stretch",
        column_config={k: st.column_config.NumberColumn(k, format="localized")
                       for k in ("이용금액(원)", "할인액(원)", "최종금액(원)")})


def _mileage(rows: list[dict]) -> None:
    if ui.is_mobile():
        ui.list_items([
            (
                f"{r['kind']} · 대여 {r['rental_id']}",
                ("+" if r["point"] > 0 else "−") + ui.pt(abs(r["point"])),
                ui.dt(r["at"]),
                r["point"] > 0,
            )
            for r in rows
        ])
        return
    st.dataframe(pd.DataFrame({
        "일시": [ui.dt(r["at"]) for r in rows],
        "구분": [r["kind"] for r in rows],
        "포인트(P)": [int(r["point"]) for r in rows],
        "대여번호": [r["rental_id"] for r in rows],
    }), hide_index=True, width="stretch",
        column_config={"포인트(P)": st.column_config.NumberColumn("포인트(P)", format="%+d")})


def _account(user_id: int) -> None:
    """내 정보: 조회·이름/연락처 수정, 비밀번호 변경, 탈퇴."""
    me = user_ops.get_user(user_id)
    ui.flash("account_msg")
    with st.container(key="ppcard_profile"):
        ui.card_title("회원정보")
        ui.calc_rows([
            ("아이디", me["user_login_id"]),
            ("회원 상태", ui.label(me["user_status"])),
            ("가입일", ui.dt(me["user_created_at"])),
            ("보유 마일리지", ui.pt(me["user_mileage"])),
        ])
        with st.form("profile_form", border=False):
            c1, c2 = st.columns(2)
            name = c1.text_input("이름", me["user_name"], max_chars=50)
            phone = c2.text_input("연락처", me["user_phone"], max_chars=13, placeholder="010-0000-0000")
            if st.form_submit_button("정보 수정", type="primary", width="stretch"):
                try:
                    user_ops.update_profile(user_id, name, phone)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    st.session_state["account_msg"] = "회원정보를 수정했습니다."
                    st.rerun()

    with st.container(key="ppcard_password"):
        ui.card_title("비밀번호 변경")
        with st.form("password_form", border=False, clear_on_submit=True):
            cur = st.text_input("현재 비밀번호", type="password")
            c1, c2 = st.columns(2)
            new = c1.text_input("새 비밀번호", type="password", placeholder=f"{rules.MIN_PASSWORD}자 이상")
            new2 = c2.text_input("새 비밀번호 확인", type="password")
            if st.form_submit_button("비밀번호 변경", width="stretch"):
                try:
                    user_ops.change_password(user_id, cur, new, new2)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    st.session_state["account_msg"] = "비밀번호를 변경했습니다."
                    st.rerun()

    with st.expander("회원 탈퇴", icon=":material/person_remove:"):
        st.warning(f"탈퇴하면 다시 로그인할 수 없고, 보유 마일리지 {ui.pt(me['user_mileage'])}는 사라집니다. "
                   "이용·결제 기록은 운영을 위해 보관됩니다. 대여 중이거나 결제하지 않은 대여가 있으면 탈퇴할 수 없어요.")
        with st.form("withdraw_form", border=False):
            pw = st.text_input("비밀번호 확인", type="password")
            agree = st.checkbox("안내 내용을 확인했고 탈퇴에 동의합니다.")
            if st.form_submit_button("탈퇴하기", width="stretch"):
                if not agree:
                    st.error("탈퇴 동의에 체크해 주세요.")
                else:
                    try:
                        user_ops.withdraw(user_id, pw)
                    except BusinessError as e:
                        st.error(str(e))
                    else:
                        for k in ("role", "user_id"):
                            st.session_state.pop(k, None)
                        st.session_state["signup_done"] = "탈퇴가 완료되었습니다. 그동안 이용해 주셔서 감사합니다."
                        st.rerun()


def render() -> None:
    user_id = st.session_state["user_id"]
    me = user_ops.get_user(user_id)
    s = user_ops.my_summary(user_id)
    ui.page_header(
        f"{ui.esc(me['user_login_id'])} · {ui.label(me['user_status'])}", f"{ui.esc(me['user_name'])}님의 마이페이지",
        "" if ui.is_mobile() else f"지금까지 {int(s['rental_count'])}번 이동하며 탄소 {ui.carbon(s['carbon_g'])}을 줄였어요.",
        stats=[("보유 마일리지", ui.pt(s["user_mileage"])),
               ("줄인 탄소", ui.carbon(s["carbon_g"])),
               ("이동거리", ui.km(s["total_km"])),
               ("적립 / 사용", f"{int(s['total_earned']):,} / {int(s['total_used']):,}P")],
    )

    month_km = user_ops.month_summary(user_id)["km"]
    ui.carbon_impact(s["carbon_g"], rules.carbon_saved_g(month_km), user_ops.carbon_rank(user_id),
                     title="나의 탄소 절감 기록")

    t1, t2, t3, t4 = st.tabs(["대여", "결제", "마일리지", "내 정보"] if ui.is_mobile()
                             else ["대여 내역", "결제 내역", "마일리지 내역", "내 정보"])
    with t1:
        rows = user_ops.my_rentals(user_id)
        _rentals(rows) if rows else ui.empty("🚲", "대여 내역이 없습니다")
    with t2:
        rows = user_ops.my_payments(user_id)
        _payments(rows) if rows else ui.empty("💳", "결제 내역이 없습니다")
    with t3:
        rows = user_ops.my_mileage(user_id)
        _mileage(rows) if rows else ui.empty("🌱", "마일리지 내역이 없습니다")
    with t4:
        _account(user_id)
