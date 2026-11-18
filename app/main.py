"""PedalPoint · 탄소 마일리지 기반 공공자전거 서비스

실행: streamlit run app/main.py  (프로젝트 루트에서)

- PC 브라우저: 이용자·관리자 웹 화면
- 스마트폰 앱(android/의 WebView 앱) 또는 주소 끝 ?app=1: 이용자 전용 모바일 화면
"""
import streamlit as st

import ui
from views import admin_assets, admin_history, admin_members, login, user_mypage, user_rent, user_return

st.set_page_config(page_title="Pedal Point", page_icon="🚲", layout="wide")
APP = ui.is_app()
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


def app_bar(name: str, extra: str = "") -> None:
    """모바일 상단 바: 로고 · 이용자 이름 · 로그아웃."""
    with st.container(key="ppbar", horizontal=True, vertical_alignment="center"):
        st.markdown(
            f'<div class="pp-bar-brand"><img src="{ui.logo_icon_uri()}" alt="">Pedal Point</div>',
            unsafe_allow_html=True, width="stretch",
        )
        st.markdown(f'<div class="pp-bar-user">{name}님{extra}</div>', unsafe_allow_html=True, width="content")
        if st.button("", icon=":material/logout:", key="app_logout", help="로그아웃"):
            logout()


def bottom_nav(pages: list, current) -> None:
    """모바일 하단 탭. 현재 탭은 key에 _on을 붙여 강조한다."""
    with st.container(key="ppnav", horizontal=True):
        for i, page in enumerate(pages):
            on = page.url_path == current.url_path
            with st.container(key=f"ppnavitem_{i}{'_on' if on else ''}"):
                st.page_link(page, width="stretch")


role = st.session_state.get("role")
if APP and role == "admin":  # 앱은 이용자 전용
    logout()
if role and not APP:
    st.logo(str(ui.ASSETS / "logo.svg"), size="large", icon_image=str(ui.ASSETS / "logo_icon.svg"))

if role == "user":
    pages = [
        st.Page(user_rent.render, title="대여" if APP else "대여소 검색·대여",
                icon=":material/pedal_bike:" if APP else ":material/search:", url_path="rent", default=True),
        st.Page(user_return.render, title="반납·결제", icon=":material/payments:", url_path="return"),
        st.Page(user_mypage.render, title="마이" if APP else "마이페이지", icon=":material/person:",
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

nav = st.navigation(pages, position="sidebar" if role and not APP else "hidden")

if role == "user":
    from user_ops import get_user

    me = get_user(st.session_state["user_id"])
    if not me or me["user_status"] == "WITHDRAWN":
        logout()
    status = "" if me["user_status"] == "ACTIVE" else f" · {ui.label(me['user_status'])}"
    if APP:
        app_bar(me["user_name"], status)
        bottom_nav(pages, nav)
    else:
        sidebar(me["user_name"], "이용자", status)
elif role == "admin":
    from admin_ops import get_staff

    staff = get_staff(st.session_state["staff_id"])
    if not staff or not staff["staff_is_active"]:
        logout()
    extra = f" · {staff['station_name']}" if staff["station_name"] else ""
    sidebar(staff["staff_name"], "관리자", extra)

nav.run()
