"""PedalPoint · 탄소 마일리지 기반 공공자전거 서비스

실행: streamlit run app/main.py  (프로젝트 루트에서)
"""
import streamlit as st

import ui
from views import admin_assets, admin_history, admin_members, login, user_mypage, user_rent, user_return

st.set_page_config(page_title="Pedal Point", page_icon="🚲", layout="wide")
ui.apply_style()


def logout() -> None:
    for key in ("role", "user_id", "staff_id"):
        st.session_state.pop(key, None)
    st.rerun()


def sidebar(name: str, role_label: str, extra: str = "") -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="pp-who"><div class="pp-avatar">{name[:1]}</div><div>'
            f'<div class="pp-who-name">{name}</div>'
            f'<div class="pp-who-role">{role_label}{extra}</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("로그아웃", icon=":material/logout:", width="stretch"):
            logout()


role = st.session_state.get("role")
if role:
    st.logo(str(ui.ASSETS / "logo.svg"), size="large", icon_image=str(ui.ASSETS / "logo_icon.svg"))

if role == "user":
    pages = [
        st.Page(user_rent.render, title="대여소 검색·대여", icon=":material/search:",
                url_path="rent", default=True),
        st.Page(user_return.render, title="반납·결제", icon=":material/payments:",
                url_path="return"),
        st.Page(user_mypage.render, title="마이페이지", icon=":material/person:",
                url_path="mypage"),
    ]
elif role == "admin":
    pages = [
        st.Page(admin_assets.render, title="대여소·자전거 관리", icon=":material/pedal_bike:",
                url_path="assets", default=True),
        st.Page(admin_history.render, title="내역 조회", icon=":material/receipt_long:",
                url_path="history"),
        st.Page(admin_members.render, title="회원 관리·통계", icon=":material/group:",
                url_path="members"),
    ]
else:
    pages = [st.Page(login.render, title="로그인", icon=":material/login:",
                     url_path="login", default=True)]

nav = st.navigation(pages, position="sidebar" if role else "hidden")

if role == "user":
    from user_ops import get_user

    me = get_user(st.session_state["user_id"])
    if not me or me["user_status"] == "WITHDRAWN":
        logout()
    status = "" if me["user_status"] == "ACTIVE" else f" · {ui.label(me['user_status'])}"
    sidebar(me["user_name"], "이용자", status)
elif role == "admin":
    from admin_ops import get_staff

    staff = get_staff(st.session_state["staff_id"])
    if not staff or not staff["staff_is_active"]:
        logout()
    extra = f" · {staff['station_name']}" if staff["station_name"] else ""
    sidebar(staff["staff_name"], "관리자", extra)

nav.run()
