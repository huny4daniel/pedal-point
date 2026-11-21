"""로그인: 아이디·비밀번호로 이용자·관리자 인증, 이용자 회원가입으로 전환."""
import streamlit as st

import admin_ops
import rules
import ui
import user_ops
from db import BusinessError
from views import signup

DEMO_HINT = "시연용 계정 · 이용자 hong1, kim2, lee3 … · 관리자 admin01 ~ admin18 · 비밀번호 1234"
DEMO_HINT_MOBILE = "시연용 계정 · hong1, kim2, lee3 … · 비밀번호 1234"


# 로그인 화면 전용: 화면 전체를 브랜드 배경(숲색 + 자전거 경로 무늬)으로 채운다
_ROUTE_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='600' viewBox='0 0 900 600'>"
    "<g fill='none' stroke='%2312B76A' stroke-opacity='.22' stroke-width='3' stroke-dasharray='2 12' stroke-linecap='round'>"
    "<path d='M-20 480 C 160 380 260 520 420 420 S 700 260 920 330'/>"
    "<path d='M-20 160 C 140 220 300 80 470 150 S 760 60 920 120'/></g>"
    "<g fill='%2312B76A' fill-opacity='.30'><circle cx='420' cy='420' r='7'/><circle cx='470' cy='150' r='7'/>"
    "<circle cx='160' cy='410' r='5'/><circle cx='760' cy='290' r='5'/></g></svg>"
)
LOGIN_CSS = f"""
<style>
[data-testid="stApp"] {{
  background: url("{_ROUTE_SVG}") center / cover no-repeat,
              radial-gradient(circle at 85% 10%, rgba(18,183,106,.35), transparent 40%),
              radial-gradient(circle at 10% 100%, rgba(18,183,106,.18), transparent 45%),
              #0F2A1F;
  background-attachment: fixed;
}}
[data-testid="stMainBlockContainer"] {{ max-width: 1240px; padding-top: max(2.5rem, calc(50vh - 330px)); }}
.pp-hero {{ background: transparent !important; background-image: none !important; padding: 0 1rem 0 0;
           min-height: 0; border-radius: 0; overflow: visible; }}
.pp-hero-title {{ font-size: clamp(2.1rem, 3.3vw, 3.2rem); margin-top: 1.8rem; }}
.pp-hero-bike {{ position: static; display: block; width: 200px; margin: 1.6rem 0 0 0; opacity: .95; }}
.pp-live {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem; margin-top: 1.6rem; }}
.pp-live div {{ border-left: 3px solid var(--pp-green-2); padding: .15rem 0 .15rem .8rem; }}
.pp-live b {{ display: block; color: #fff; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.03em; }}
.pp-live span {{ color: #A9C9B8; font-size: .8rem; }}
.st-key-ppcard_login {{ box-shadow: 0 24px 60px rgba(0,0,0,.35) !important; border: none !important; }}
.st-key-pplogin_theme button {{ background: rgba(255,255,255,.10) !important; color: #fff !important;
                                border: 1px solid rgba(255,255,255,.22) !important; box-shadow: none !important; }}
.st-key-pplogin_theme [data-testid="stIconMaterial"] {{ color: #fff !important; }}
.pp-app-name {{ color: #fff !important; }}
.pp-app-tag {{ color: #B9D4C6 !important; }}
.pp-app-tag em {{ color: #7EE2B1 !important; }}
</style>
"""


def _hero() -> None:
    s = user_ops.service_stats()
    st.markdown(
        f"""
        <div class="pp-hero">
          <div class="pp-hero-brand"><img src="{ui.logo_icon_uri()}" alt="">Pedal Point</div>
          <div class="pp-hero-title">환경을 생각한 이동이<br>곧 <em>혜택</em>이 된다</div>
          <div class="pp-hero-desc">공공자전거로 이동한 거리만큼 줄어든 탄소량을 계산해
            마일리지로 적립하고, 다음 이용요금 결제 때 할인으로 사용합니다.</div>
          <div class="pp-live">
            <div><b>{s['stations']}곳</b><span>운영 중인 대여소</span></div>
            <div><b>{s['bikes']}대</b><span>지금 빌릴 수 있는 자전거</span></div>
            <div><b>{ui.carbon(rules.carbon_saved_g(s['total_km']))}</b><span>함께 줄인 탄소</span></div>
          </div>
          <div class="pp-hero-steps">
            <div class="pp-hero-step"><b>1km 이동</b><span>탄소 {rules.CARBON_G_PER_KM}g 절감</span></div>
            <div class="pp-hero-step"><b>1km 이동</b><span>{rules.POINTS_PER_KM}P 적립</span></div>
            <div class="pp-hero-step"><b>1P = 1원</b><span>다음 결제에서 할인</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _app_brand() -> None:
    """모바일 로그인 상단: 로고·서비스명·한 줄 소개."""
    st.markdown(
        f'<div class="pp-app-brand"><img src="{ui.logo_icon_uri()}" alt="">'
        f'<div class="pp-app-name">Pedal Point</div>'
        f'<div class="pp-app-tag">환경을 생각한 이동이 곧 <em>혜택</em>이 된다</div></div>',
        unsafe_allow_html=True,
    )


def _login_form(app: bool) -> None:
    if msg := st.session_state.pop("signup_done", None):
        st.success(msg)
    st.markdown(
        '<div class="pp-login-title">로그인</div>'
        '<div class="pp-login-sub">아이디와 비밀번호를 입력하세요.</div>',
        unsafe_allow_html=True,
    )
    role = "이용자" if app else st.segmented_control(
        "사용자 구분", ["이용자", "관리자"], default="이용자", key="login_role",
        label_visibility="collapsed", width="stretch",
    ) or "이용자"

    with st.form("login_form", border=False):
        login_id = st.text_input("아이디", placeholder="아이디", icon=":material/person:")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호",
                                 icon=":material/lock:")
        submitted = st.form_submit_button("로그인", type="primary", width="stretch")

    if submitted:
        if not login_id.strip() or not password:
            st.error("아이디와 비밀번호를 모두 입력해 주세요.")
        else:
            try:
                if role == "관리자":
                    staff = admin_ops.authenticate_staff(login_id, password)
                    st.session_state.update(role="admin", staff_id=staff["staff_id"])
                else:
                    user = user_ops.authenticate_user(login_id, password)
                    st.session_state.update(role="user", user_id=user["user_id"])
            except BusinessError as e:
                st.error(str(e))
            else:
                st.rerun()

    if role == "이용자" and st.button("회원가입", width="stretch", icon=":material/person_add:"):
        st.session_state["auth_mode"] = "signup"
        st.rerun()

    st.markdown(f'<div class="pp-login-note">{DEMO_HINT_MOBILE if app else DEMO_HINT}</div>', unsafe_allow_html=True)


def _auth_card(app: bool) -> None:
    if st.session_state.get("auth_mode") == "signup":
        signup.render_form()
    else:
        _login_form(app)


def render() -> None:
    app = ui.is_mobile()
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    with st.container(key="pplogin_theme", horizontal=True, horizontal_alignment="right"):
        ui.theme_toggle("theme_login", label=False)
    if app:  # 모바일 전용 화면: 한 칸, 이용자 전용
        _app_brand()
        with st.container(key="ppcard_login"):
            _auth_card(app=True)
        return

    hero, form = st.columns([1.25, 1], gap="large", vertical_alignment="center")
    with hero:
        _hero()
    with form, st.container(key="ppcard_login"):
        _auth_card(app=False)
