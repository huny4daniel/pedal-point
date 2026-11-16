"""로그인: 이용자/관리자 선택 후 진입 (비밀번호 없이 ID를 고르는 방식)."""
import streamlit as st

import admin_ops
import ui
import user_ops


def render() -> None:
    st.markdown(
        f"""
        <div class="pp-hero">
          <div class="pp-hero-text">
            <div class="pp-eyebrow">탄소 마일리지 기반 공공자전거 서비스</div>
            <div class="pp-title">Pedal Point</div>
            <div class="pp-sub">환경을 생각한 이동이 곧 혜택이 된다</div>
            <div class="pp-note">탄 만큼 줄어든 탄소가 마일리지로 쌓이고, 다음 이용요금에서 할인됩니다.</div>
          </div>
          <img src="{ui.bike_data_uri()}" alt="자전거 일러스트">
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, _ = st.columns([5, 4])
    with left:
        role = st.segmented_control(
            "사용자 구분", ["이용자", "관리자"], default="이용자", key="login_role"
        )
        if role == "관리자":
            staff = admin_ops.login_staff()
            options = {
                s["staff_id"]: f"{s['staff_name']} (ID {s['staff_id']})"
                + (f" · {s['station_name']}" if s["station_name"] else "")
                for s in staff
            }
            staff_id = st.selectbox("관리자 선택", list(options), format_func=options.get)
            if st.button("관리자 화면으로 진입", type="primary", disabled=staff_id is None):
                st.session_state.update(role="admin", staff_id=staff_id)
                st.rerun()
        elif role == "이용자":
            users = user_ops.login_users()
            options = {
                u["user_id"]: f"{u['user_name']} (ID {u['user_id']})"
                + ("" if u["user_status"] == "ACTIVE" else f" · {ui.label(u['user_status'])}")
                for u in users
            }
            user_id = st.selectbox("이용자 선택", list(options), format_func=options.get)
            if st.button("이용자 화면으로 진입", type="primary", disabled=user_id is None):
                st.session_state.update(role="user", user_id=user_id)
                st.rerun()
