"""이용자 회원가입: 아이디·비밀번호·이름·연락처 (로그인 카드 안에서 전환)."""
import streamlit as st

import user_ops
from db import BusinessError

# 비밀번호·연락처 실시간 검사: 브라우저에서 입력할 때마다 조건 충족 여부를 표시한다.
# 서버로 값을 보내지 않는 화면 표시용이고, 실제 검사는 가입 시 user_ops.signup()이 rules의 정규식으로 한다.
_LIVE_CHECK_JS = r"""
const PW = ".st-key-signup_pw input", PW2 = ".st-key-signup_pw2 input", PHONE = ".st-key-signup_phone input";
const PW_RULES = [
  ["8자 이상",                (v) => v.length >= 8],
  ["영문 포함",               (v) => /[A-Za-z]/.test(v)],
  ["숫자 포함",               (v) => /\d/.test(v)],
  ["특수문자 @ - ! 중 1개 이상", (v) => /[@\-!]/.test(v)],
  ["영문·숫자·@ - ! 만 사용",  (v) => /^[A-Za-z\d@\-!]*$/.test(v)],
];
const PW_FULL = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@\-!])[A-Za-z\d@\-!]{8,}$/;
const PHONE_FULL = /^010-\d{4}-\d{4}$/;

const val = (sel) => document.querySelector(sel)?.value ?? "";
const item = (state, text) =>
  `<li class="pp-chk-${state}"><span>${state === "ok" ? "✓" : state === "bad" ? "✕" : "•"}</span>${text}</li>`;

function renderPw(root) {
  const pw = val(PW), pw2 = val(PW2);
  let html = PW_RULES.map(([text, test]) => item(pw === "" ? "idle" : test(pw) ? "ok" : "bad", text)).join("");
  if (pw2 !== "") html += item(pw === pw2 ? "ok" : "bad", pw === pw2 ? "비밀번호 확인 일치" : "비밀번호 확인 불일치");
  const head = pw === "" ? "" : PW_FULL.test(pw)
    ? '<div class="pp-chk-head ok">사용할 수 있는 비밀번호예요</div>'
    : '<div class="pp-chk-head bad">아래 조건을 모두 맞춰 주세요</div>';
  root.innerHTML = `<div class="pp-chk">${head}<ul class="pp-chk-grid">${html}</ul></div>`;
}

function renderPhone(root) {
  const v = val(PHONE);
  let li;
  if (v === "") li = item("idle", "010-0000-0000 형식으로 입력");
  else if (PHONE_FULL.test(v)) li = item("ok", "올바른 연락처 형식이에요");
  else if (/[^\d-]/.test(v)) li = item("bad", "숫자와 하이픈(-)만 입력해 주세요");
  else if (!"010".startsWith(v.slice(0, 3))) li = item("bad", "010으로 시작해야 해요");
  else li = item("bad", "010-0000-0000 형식으로 입력해 주세요");
  root.innerHTML = `<div class="pp-chk"><ul>${li}</ul></div>`;
}

const RENDER = { pw: renderPw, phone: renderPhone };
const WATCH = { pw: [PW, PW2], phone: [PHONE] };

export default function (component) {
  const { parentElement, data } = component;
  if (!document.getElementById("pp-chk-style")) {  // 스타일은 문서에 한 번만 넣는다
    const style = document.createElement("style");
    style.id = "pp-chk-style"; style.textContent = data.css;
    document.head.appendChild(style);
  }
  window.__ppChkRoots = window.__ppChkRoots || {};
  window.__ppChkRoots[data.kind] = parentElement;
  if (!window.__ppChkListen) {  // 문서 전체에 한 번만 등록 (입력칸이 다시 그려져도 계속 동작)
    window.__ppChkListen = (e) => {
      for (const [kind, sels] of Object.entries(WATCH)) {
        const root = window.__ppChkRoots[kind];
        if (root?.isConnected && e.target.matches?.(sels.join(","))) RENDER[kind](root);
      }
    };
    document.addEventListener("input", window.__ppChkListen, true);
  }
  RENDER[data.kind](parentElement);
}
"""
_SIGNUP_KEYS = ("signup_id", "signup_pw", "signup_pw2", "signup_name", "signup_phone")
_LIVE_CHECK_CSS = ", ".join(f'.st-key-{k} [data-testid="InputInstructions"]' for k in _SIGNUP_KEYS) + """
{ display: none; }
.pp-chk { font-size: .84rem; margin: -.2rem 0 .4rem 0; }
.pp-chk ul { list-style: none; margin: 0; padding: 0; }
.pp-chk ul.pp-chk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: .15rem .8rem; }
.pp-chk li { display: flex; gap: .4rem; align-items: center; color: var(--pp-muted, #7C8A83); }
.pp-chk li span { width: 1rem; text-align: center; font-weight: 700; }
.pp-chk li.pp-chk-ok { color: var(--pp-green, #0A8A55); }
.pp-chk li.pp-chk-bad { color: var(--pp-red, #B42318); }
.pp-chk-head { font-weight: 700; margin-bottom: .25rem; }
.pp-chk-head.ok { color: var(--pp-green, #0A8A55); }
.pp-chk-head.bad { color: var(--pp-red, #B42318); }
"""
_live_check = st.components.v2.component("pp_live_check", js=_LIVE_CHECK_JS, isolate_styles=False)


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
                                 icon=":material/person:", key="signup_id")
        c1, c2 = st.columns(2)
        password = c1.text_input("비밀번호", type="password", placeholder="영문·숫자·@-! 8자 이상",
                                 key="signup_pw")
        password2 = c2.text_input("비밀번호 확인", type="password", placeholder="한 번 더 입력",
                                  key="signup_pw2")
        _live_check(key="signup_pw_check", data={"kind": "pw", "css": _LIVE_CHECK_CSS})
        name = st.text_input("이름", max_chars=50, icon=":material/badge:", key="signup_name")
        phone = st.text_input("연락처", placeholder="010-0000-0000", max_chars=13,
                              icon=":material/smartphone:", key="signup_phone")
        _live_check(key="signup_phone_check", data={"kind": "phone", "css": _LIVE_CHECK_CSS})
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
