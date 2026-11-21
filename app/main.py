"""PedalPoint · 탄소 마일리지 기반 공공자전거 서비스

실행: streamlit run app/main.py  (프로젝트 루트에서)

- PC 화면(가로 창): 이용자·관리자 웹 화면 (사이드바 메뉴)
- 모바일 전용 화면(세로가 더 길거나 폭 640px 이하인 창): 이용자 전용, 상단 바 + 하단 탭
  창 크기를 바꾸면 로그인을 유지한 채 바로 전환된다. 관리자는 항상 PC 화면.
"""
import streamlit as st

import ui
from db import BusinessError
from views import admin_assets, admin_history, admin_members, login, user_home, user_mypage, user_rent

st.set_page_config(page_title="Pedal Point", page_icon="🚲", layout="wide")
ui.sync_viewport()
MOBILE = ui.is_mobile()
ui.apply_style()


def logout() -> None:
    for key in ("role", "user_id", "staff_id", "auth_mode"):
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
        c1, c2 = st.columns(2)
        with c1:
            ui.theme_toggle("theme_sidebar")
        if c2.button("로그아웃", icon=":material/logout:", width="stretch"):
            logout()


def app_bar(name: str, extra: str = "") -> None:
    """모바일 상단 바: 로고 · 이용자 이름 · 로그아웃."""
    with st.container(key="ppbar", horizontal=True, vertical_alignment="center"):
        st.markdown(
            f'<div class="pp-bar-brand"><img src="{ui.logo_icon_uri()}" alt="">Pedal Point</div>',
            unsafe_allow_html=True, width="stretch",
        )
        st.markdown(f'<div class="pp-bar-user">{name}님{extra}</div>', unsafe_allow_html=True, width="content")
        ui.theme_toggle("theme_bar", label=False)
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
if role and not MOBILE:
    st.logo(str(ui.ASSETS / "logo.svg"), size="large", icon_image=str(ui.ASSETS / "logo_icon.svg"))

if role == "user":
    pages = [
        st.Page(user_home.render, title="홈", icon=":material/home:", url_path="home", default=True),
        # 대여·반납은 한 메뉴: 대여 중이 아니면 대여 화면, 대여 중이면 반납·결제 화면
        st.Page(user_rent.render, title="대여·반납", icon=":material/pedal_bike:", url_path="ride"),
        st.Page(user_mypage.render, title="마이" if MOBILE else "마이페이지", icon=":material/person:",
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

nav = st.navigation(pages, position="sidebar" if role and not MOBILE else "hidden")
# ui.go("mypage")처럼 메뉴 이름으로 이동 (기본 페이지는 url_path가 비어 있어 이름을 따로 둔다)
PAGE_KEYS = {"user": ["home", "ride", "mypage"], "admin": ["assets", "history", "members"]}
st.session_state["_pages"] = dict(zip(PAGE_KEYS.get(role, ["login"]), pages))

# DB 오류는 db.py에서 BusinessError("처리 중 오류가 발생했습니다 …")로 바뀌어 올라온다.
# 화면 안에서 잡지 않은 오류도 스택 트레이스 대신 안내 문구로 보여준다.
try:
    if role == "user":
        from user_ops import get_user

        me = get_user(st.session_state["user_id"])
        if not me or me["user_status"] == "WITHDRAWN":
            logout()
        status = "" if me["user_status"] == "ACTIVE" else f" · {ui.label(me['user_status'])}"
        mileage = f" · {ui.pt(me['user_mileage'])}"
        if MOBILE:
            app_bar(me["user_name"], mileage + status)
            bottom_nav(pages, nav)
        else:
            sidebar(me["user_name"], "이용자", mileage + status)
    elif role == "admin":
        from admin_ops import get_staff

        staff = get_staff(st.session_state["staff_id"])
        if not staff or not staff["staff_is_active"]:
            logout()
        extra = f" · {staff['station_name']}" if staff["station_name"] else ""
        sidebar(staff["staff_name"], "관리자", extra)

    nav.run()
except BusinessError as e:
    st.error(str(e))
