"""이용자 회원가입: 아이디·비밀번호·이름·연락처 (로그인 카드 안에서 전환)."""
import streamlit as st

import user_ops
from db import BusinessError


def _back_to_login() -> None:
    st.session_state["auth_mode"] = "login"


def render_form() -> None:
    st.markdown(
        '<div class="pp-login-title">회원가입</div>'
        '<div class="pp-login-sub">가입하면 바로 자전거를 빌리고 마일리지를 모을 수 있어요.</div>',
        unsafe_allow_html=True,
    )
    with st.form("signup_form", border=False):
        login_id = st.text_input("아이디", placeholder="영문·숫자 4~20자", max_chars=20,
                                 icon=":material/person:")
        c1, c2 = st.columns(2)
        password = c1.text_input("비밀번호", type="password", placeholder="4자 이상")
        password2 = c2.text_input("비밀번호 확인", type="password", placeholder="한 번 더 입력")
        name = st.text_input("이름", max_chars=50, icon=":material/badge:")
        phone = st.text_input("연락처", placeholder="010-0000-0000", max_chars=13,
                              icon=":material/smartphone:")
        submitted = st.form_submit_button("가입하기", type="primary", width="stretch")

    if submitted:
        try:
            user_ops.signup(login_id, password, password2, name, phone)
        except BusinessError as e:
            st.error(str(e))
        else:
            st.session_state["signup_done"] = f"{login_id.strip()} 계정으로 가입했습니다. 로그인해 주세요."
            _back_to_login()
            st.rerun()

    st.button("로그인으로 돌아가기", width="stretch", icon=":material/arrow_back:", on_click=_back_to_login)
