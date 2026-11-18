"""로그인: 이용자/관리자 선택 후 진입 (비밀번호 없이 ID를 고르는 방식)."""
import streamlit as st

import admin_ops
import rules
import ui
import user_ops


def _hero() -> None:
    st.markdown(
        f"""
        <div class="pp-hero">
          <div class="pp-hero-brand"><img src="{ui.logo_icon_uri()}" alt="">Pedal Point</div>
          <div class="pp-hero-title">환경을 생각한 이동이<br>곧 <em>혜택</em>이 된다</div>
          <div class="pp-hero-desc">공공자전거로 이동한 거리만큼 줄어든 탄소량을 계산해
            마일리지로 적립하고, 다음 이용요금 결제 때 할인으로 사용합니다.</div>
          <img class="pp-hero-bike" src="{ui.bike_data_uri()}" alt="">
          <div class="pp-hero-steps">
            <div class="pp-hero-step"><b>1km 이동</b><span>탄소 {rules.CARBON_G_PER_KM}g 절감</span></div>
            <div class="pp-hero-step"><b>{rules.CARBON_G_PER_POINT}g 절감</b><span>1P 적립</span></div>
            <div class="pp-hero-step"><b>1P = 1원</b><span>다음 결제에서 할인</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    app = ui.is_app()
    if app:  # 스마트폰 앱: 한 칸, 이용자 전용
        hero, form = st.container(), st.container()
    else:
        hero, form = st.columns([1.25, 1], gap="large", vertical_alignment="center")
    with hero:
        _hero()

    with form, st.container(key="ppcard_login"):
        st.markdown(
            '<div class="pp-login-title">시작하기</div>'
            '<div class="pp-login-sub">'
            + ("계정을 선택해 들어가세요." if app else "사용자 구분을 고르고 계정을 선택해 들어가세요.")
            + "</div>",
            unsafe_allow_html=True,
        )
        role = "이용자" if app else st.segmented_control(
            "사용자 구분", ["이용자", "관리자"], default="이용자", key="login_role",
            label_visibility="collapsed", width="stretch",
        )
        if role == "관리자":
            staff = admin_ops.login_staff()
            options = {
                s["staff_id"]: f"{s['staff_name']} (ID {s['staff_id']})"
                + (f" · {s['station_name']}" if s["station_name"] else "")
                for s in staff
            }
            staff_id = st.selectbox("관리자 계정", list(options), format_func=options.get)
            if st.button("관리자로 시작", type="primary", width="stretch",
                         icon=":material/arrow_forward:", icon_position="right",
                         disabled=staff_id is None):
                st.session_state.update(role="admin", staff_id=staff_id)
                st.rerun()
        elif role == "이용자":
            users = user_ops.login_users()
            options = {
                u["user_id"]: f"{u['user_name']} (ID {u['user_id']})"
                + ("" if u["user_status"] == "ACTIVE" else f" · {ui.label(u['user_status'])}")
                for u in users
            }
            user_id = st.selectbox("이용자 계정", list(options), format_func=options.get)
            if st.button("이용자로 시작", type="primary", width="stretch",
                         icon=":material/arrow_forward:", icon_position="right",
                         disabled=user_id is None):
                st.session_state.update(role="user", user_id=user_id)
                st.rerun()
        st.markdown('<div class="pp-login-note">비밀번호 없이 사용자 ID를 골라 들어갑니다.</div>',
                    unsafe_allow_html=True)
