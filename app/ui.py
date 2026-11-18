"""공통 UI: 스타일, 머리말, 카드·지표·배지 컴포넌트, 포맷터."""
import base64
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets"

STATUS_LABELS = {
    # user
    "ACTIVE": "정상", "SUSPENDED": "이용정지", "WITHDRAWN": "탈퇴",
    # station
    "INACTIVE": "운영중지",
    # bicycle
    "AVAILABLE": "대여가능", "RENTED": "대여중", "MAINTENANCE": "정비중",
    # rental
    "RENTING": "대여중", "RETURNED": "반납완료",
    # mileage
    "EARN": "적립", "USE": "사용",
}
STATION_STATUS_LABELS = {"ACTIVE": "운영중", "INACTIVE": "운영중지"}

BADGE_COLORS = {
    "ACTIVE": "green", "AVAILABLE": "green", "RETURNED": "green", "EARN": "green",
    "RENTED": "amber", "RENTING": "amber", "MAINTENANCE": "amber", "SUSPENDED": "amber",
    "USE": "gray", "INACTIVE": "red", "WITHDRAWN": "red",
}

CSS = """
<style>
:root {
  --pp-bg: #F4F6F5;
  --pp-surface: #FFFFFF;
  --pp-line: #E3E8E5;
  --pp-line-2: #EEF2EF;
  --pp-ink: #0F1A15;
  --pp-ink-2: #3F4D46;
  --pp-muted: #7C8A83;
  --pp-green: #0A8A55;
  --pp-green-2: #12B76A;
  --pp-green-soft: #E7F6EE;
  --pp-forest: #0F2A1F;
  --pp-amber: #B54708;
  --pp-amber-soft: #FEF3E2;
  --pp-red: #B42318;
  --pp-red-soft: #FEECEB;
  --pp-gray-soft: #EEF2EF;
  --pp-shadow: 0 1px 2px rgba(15, 26, 21, .04), 0 6px 20px rgba(15, 26, 21, .05);
}

/* 기본 크롬 정리 */
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"], [data-testid="stMainMenu"], footer { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 1200px; padding-top: 2.2rem; padding-bottom: 4rem;
}
h1, h2, h3, h4 { letter-spacing: -0.02em; }

/* 사이드바 */
[data-testid="stSidebar"] { border-right: 1px solid var(--pp-line); }
[data-testid="stSidebarNav"] a { border-radius: 10px; }
[data-testid="stSidebarNav"] a span { font-weight: 500; }
.pp-who {
  display: flex; align-items: center; gap: .75rem; padding: .85rem .9rem;
  background: var(--pp-bg); border-radius: 14px; margin: .2rem 0 .7rem 0;
}
.pp-avatar {
  width: 38px; height: 38px; border-radius: 50%; flex: 0 0 auto;
  display: grid; place-items: center; font-weight: 700; font-size: .95rem;
  background: var(--pp-forest); color: #fff;
}
.pp-who-name { font-weight: 700; color: var(--pp-ink); line-height: 1.3; }
.pp-who-role { font-size: .78rem; color: var(--pp-muted); line-height: 1.4; }

/* 카드 컨테이너: key가 ppcard_ 로 시작하는 st.container */
[class*="st-key-ppcard_"] {
  background: var(--pp-surface); border: 1px solid var(--pp-line);
  border-radius: 18px; padding: 1.3rem 1.4rem; box-shadow: var(--pp-shadow);
}
[class*="st-key-ppcard_sel"] {
  border: 1.5px solid var(--pp-green-2); box-shadow: 0 0 0 4px var(--pp-green-soft);
}
.pp-card-title { font-weight: 700; font-size: 1.05rem; color: var(--pp-ink); letter-spacing: -0.02em; }
.pp-card-sub { font-size: .85rem; color: var(--pp-muted); margin: .15rem 0 .5rem 0; }

/* 페이지 머리말 */
.pp-head { margin-bottom: 1.5rem; }
.pp-eyebrow { color: var(--pp-green); font-weight: 600; font-size: .85rem; margin-bottom: .3rem; }
.pp-title { color: var(--pp-ink); font-weight: 800; font-size: 1.85rem; letter-spacing: -0.035em; line-height: 1.2; }
.pp-sub { color: var(--pp-muted); font-size: .98rem; margin-top: .35rem; }

/* 탭: 세그먼트 형태 */
[data-testid="stTabs"] [role="tablist"] {
  gap: 2px; background: #E8EDEA; padding: 4px; border-radius: 12px; width: fit-content;
  border: none !important; box-shadow: none !important; margin-bottom: .4rem;
}
[data-testid="stTabs"] [role="tablist"]::before, [data-testid="stTabs"] [role="tablist"]::after,
[data-testid="stTabs"] div:has(> [role="tablist"])::before, [data-testid="stTabs"] div:has(> [role="tablist"])::after {
  display: none !important;
}
[data-testid="stTabs"] div:has(> [role="tablist"]) { border: none !important; box-shadow: none !important; }
[data-testid="stTab"] {
  height: 36px; padding: 0 1.05rem !important; border-radius: 9px; background: transparent;
  display: flex; align-items: center; border: none !important;
}
[data-testid="stTab"] p { font-weight: 600; color: var(--pp-ink-2) !important; }
[data-testid="stTab"][aria-selected="true"] { background: #fff; box-shadow: 0 1px 3px rgba(15,26,21,.12); }
[data-testid="stTab"][aria-selected="true"] p { color: var(--pp-ink) !important; }
[data-testid="stTab"] .react-aria-SelectionIndicator { display: none !important; }

/* 버튼 */
.stButton button, .stFormSubmitButton button { font-weight: 600; min-height: 42px; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  box-shadow: 0 2px 8px rgba(10, 138, 85, .22);
}

/* 표·알림 */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 12px; }

/* 지표 카드 */
.pp-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: .9rem; margin: 0 0 1.4rem 0; }
.pp-stat { background: var(--pp-surface); border: 1px solid var(--pp-line); border-radius: 18px;
           padding: 1.1rem 1.25rem; box-shadow: var(--pp-shadow); }
.pp-stat-label { color: var(--pp-muted); font-size: .84rem; font-weight: 500; margin-bottom: .45rem; }
.pp-stat-value { color: var(--pp-ink); font-size: 1.7rem; font-weight: 800;
                 font-variant-numeric: tabular-nums; letter-spacing: -0.03em; line-height: 1.1; }
.pp-stat-value small { font-size: .9rem; color: var(--pp-muted); font-weight: 600; margin-left: .2rem; }
.pp-stat.accent { background: var(--pp-forest); border-color: var(--pp-forest);
                  background-image: radial-gradient(circle at 100% 0%, rgba(18,183,106,.35), transparent 55%); }
.pp-stat.accent .pp-stat-label { color: #A9C9B8; }
.pp-stat.accent .pp-stat-value { color: #fff; }
.pp-stat.accent .pp-stat-value small { color: #A9C9B8; }

/* 계산 내역 */
.pp-rows { margin: .1rem 0 .6rem 0; }
.pp-row { display: flex; justify-content: space-between; gap: 1rem; padding: .45rem 0;
          font-variant-numeric: tabular-nums; font-size: .95rem; }
.pp-row span:first-child { color: var(--pp-muted); }
.pp-row span:last-child { color: var(--pp-ink); font-weight: 600; text-align: right; }
.pp-row.minus span:last-child { color: var(--pp-green); }
.pp-row.total { border-top: 1px solid var(--pp-line); margin-top: .4rem; padding-top: .9rem; align-items: baseline; }
.pp-row.total span:first-child { color: var(--pp-ink); font-weight: 700; }
.pp-row.total span:last-child { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em; }

/* 배지 */
.pp-badge { display: inline-flex; align-items: center; padding: .18rem .6rem;
            border-radius: 999px; font-size: .76rem; font-weight: 600; white-space: nowrap; }
.pp-badge.green { background: var(--pp-green-soft); color: var(--pp-green); }
.pp-badge.gray  { background: var(--pp-gray-soft); color: var(--pp-ink-2); }
.pp-badge.amber { background: var(--pp-amber-soft); color: var(--pp-amber); }
.pp-badge.red   { background: var(--pp-red-soft); color: var(--pp-red); }

/* 대여소 카드 내용 */
.pp-station-top { display: flex; justify-content: space-between; align-items: flex-start; gap: .6rem; }
.pp-station-name { font-weight: 700; font-size: 1.08rem; color: var(--pp-ink); letter-spacing: -0.02em; }
.pp-station-addr { color: var(--pp-muted); font-size: .84rem; margin: .2rem 0 .9rem 0;
                   white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pp-avail { display: flex; align-items: baseline; gap: .3rem; margin-bottom: .45rem; }
.pp-avail b { font-size: 1.5rem; font-weight: 800; color: var(--pp-ink); letter-spacing: -0.03em; }
.pp-avail span { font-size: .84rem; color: var(--pp-muted); }
.pp-meter { height: 6px; background: var(--pp-line-2); border-radius: 99px; overflow: hidden; margin-bottom: .4rem; }
.pp-meter > i { display: block; height: 100%; background: var(--pp-green-2); border-radius: 99px; }

/* 빈 상태 */
.pp-empty { text-align: center; padding: 2.2rem 1rem; color: var(--pp-muted); font-size: .92rem; }
.pp-empty-icon { width: 56px; height: 56px; margin: 0 auto .9rem auto; border-radius: 16px;
                 background: var(--pp-green-soft); display: grid; place-items: center; font-size: 1.6rem; }
.pp-empty-title { color: var(--pp-ink); font-weight: 700; font-size: 1.05rem; margin-bottom: .25rem; }

/* 완료 배너 */
.pp-done { display: flex; gap: 1rem; align-items: center; background: var(--pp-green-soft);
           border: 1px solid #BFE7D1; border-radius: 16px; padding: 1rem 1.2rem; margin-bottom: 1.2rem; }
.pp-done-icon { width: 38px; height: 38px; border-radius: 50%; background: var(--pp-green-2); color: #fff;
                display: grid; place-items: center; font-weight: 800; flex: 0 0 auto; }
.pp-done-title { font-weight: 700; color: var(--pp-ink); }
.pp-done-sub { font-size: .88rem; color: var(--pp-ink-2); }

/* 로그인 히어로 */
.pp-hero {
  position: relative; overflow: hidden; border-radius: 26px; padding: 2.4rem 2.6rem 2.2rem 2.6rem;
  min-height: 540px; display: flex; flex-direction: column; color: #fff;
  background: var(--pp-forest);
  background-image: radial-gradient(circle at 110% -10%, rgba(18,183,106,.45), transparent 50%),
                    radial-gradient(circle at -20% 120%, rgba(18,183,106,.18), transparent 45%);
}
.pp-hero-brand { display: flex; align-items: center; gap: .6rem; font-weight: 800; font-size: 1.05rem; color: #fff; }
.pp-hero-brand img { width: 30px; height: 30px; }
.pp-hero-title { color: #fff; font-size: 2.6rem; font-weight: 800; line-height: 1.22;
                 letter-spacing: -0.045em; margin: 2.4rem 0 .9rem 0; }
.pp-hero-title em { font-style: normal; color: var(--pp-green-2); }
.pp-hero-desc { color: #B9D4C6; font-size: 1rem; line-height: 1.65; max-width: 26rem; }
.pp-hero-steps { display: flex; gap: .6rem; flex-wrap: wrap; margin-top: auto; padding-top: 2rem;
                 position: relative; z-index: 1; }
.pp-hero-step { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.13);
                border-radius: 14px; padding: .75rem .95rem; flex: 1 1 120px; backdrop-filter: blur(4px); }
.pp-hero-step b { display: block; font-size: 1.02rem; color: #fff; }
.pp-hero-step span { font-size: .78rem; color: #A9C9B8; }
.pp-hero-bike { position: absolute; right: -18px; bottom: 112px; width: 220px; opacity: .9; }
.pp-login-title { font-size: 1.55rem; font-weight: 800; letter-spacing: -0.035em; color: var(--pp-ink); }
.pp-login-sub { color: var(--pp-muted); font-size: .92rem; margin: .3rem 0 1.3rem 0; }
.pp-login-note { color: var(--pp-muted); font-size: .8rem; margin-top: .6rem; text-align: center; }

@media (max-width: 1100px) { .pp-hero-bike { display: none; } }
@media (max-width: 760px) {
  .pp-hero { min-height: 0; padding: 1.8rem; }
  .pp-hero-title { font-size: 2rem; margin-top: 1.6rem; }
}
</style>
"""


APP_CSS = """
<style>
/* ---- 스마트폰 앱(WebView) 모드: 이용자 전용 모바일 레이아웃 ---- */
header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"], [data-testid="stToolbar"], [data-testid="stStatusWidget"] {
  display: none !important;
}
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 480px; padding: .6rem 1rem calc(6.2rem + env(safe-area-inset-bottom)) 1rem !important;
}
.pp-head { margin-bottom: 1rem; }
.pp-eyebrow { display: none; }
.pp-title { font-size: 1.45rem; }
.pp-sub { font-size: .88rem; }
[class*="st-key-ppcard_"] { border-radius: 16px; padding: 1.05rem 1.1rem; }
.pp-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .6rem; }
.pp-stat { padding: .9rem 1rem; border-radius: 16px; }
.pp-stat-value { font-size: 1.3rem; }
.pp-stat-label { font-size: .78rem; }
.stButton button, .stFormSubmitButton button { min-height: 48px; }
[data-testid="stTabs"] [role="tablist"] { width: 100%; }
[data-testid="stTab"] { flex: 1 1 0; justify-content: center; padding: 0 .4rem !important; }

/* 상단 바 */
.st-key-ppbar {
  position: sticky; top: 0; z-index: 999; background: var(--pp-bg);
  padding: .45rem 0 .55rem 0; margin-bottom: .2rem; gap: .5rem;
}
.pp-bar-brand { display: flex; align-items: center; gap: .5rem; font-weight: 800; font-size: 1.05rem;
                color: var(--pp-ink); letter-spacing: -0.02em; }
.pp-bar-brand img { width: 28px; height: 28px; }
.pp-bar-user { font-size: .85rem; color: var(--pp-ink-2); font-weight: 600; white-space: nowrap; }
.st-key-ppbar .stButton button { min-height: 36px; width: 36px; padding: 0; border-radius: 50%;
                                  background: #fff; border: 1px solid var(--pp-line); }

/* 하단 탭 */
.st-key-ppnav {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); z-index: 1000;
  width: 100%; max-width: 480px; gap: 0 !important;
  background: rgba(255,255,255,.96); backdrop-filter: blur(8px);
  border-top: 1px solid var(--pp-line); box-shadow: 0 -4px 18px rgba(15,26,21,.06);
  padding: .35rem .5rem calc(.35rem + env(safe-area-inset-bottom)) .5rem;
}
.st-key-ppnav > [data-testid="stElementContainer"], .st-key-ppnav > div { flex: 1 1 0; min-width: 0; }
.st-key-ppnav [data-testid="stPageLink"] a {
  flex-direction: column; justify-content: center; gap: .1rem; padding: .35rem 0;
  border-radius: 12px; background: transparent !important;
}
.st-key-ppnav [data-testid="stPageLink"] a p { font-size: .74rem; font-weight: 600; color: var(--pp-muted); }
.st-key-ppnav [data-testid="stPageLink"] a [data-testid="stIconMaterial"] { font-size: 1.45rem; color: var(--pp-muted); }
.st-key-ppnav [class*="_on"] [data-testid="stPageLink"] a p,
.st-key-ppnav [class*="_on"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"] { color: var(--pp-green); }

/* 로그인 */
.pp-hero { min-height: 0; padding: 1.5rem 1.4rem 1.3rem 1.4rem; border-radius: 22px; margin-bottom: 1rem; }
.pp-hero-title { font-size: 1.75rem; margin: 1.3rem 0 .6rem 0; }
.pp-hero-desc { font-size: .88rem; }
.pp-hero-bike { display: none; }
.pp-hero-steps { padding-top: 1.2rem; gap: .45rem; }
.pp-hero-step { padding: .6rem .7rem; min-width: 0; flex: 1 1 0; }
.pp-hero-step b { font-size: .9rem; }
.pp-hero-step span { font-size: .7rem; }

/* 목록 */
.pp-list { display: flex; flex-direction: column; gap: .55rem; }
.pp-item { background: var(--pp-surface); border: 1px solid var(--pp-line); border-radius: 14px;
           padding: .8rem .95rem; }
.pp-item-top { display: flex; justify-content: space-between; align-items: center; gap: .6rem; }
.pp-item-title { font-weight: 700; color: var(--pp-ink); font-size: .95rem; letter-spacing: -0.02em;
                 min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pp-item-value { font-weight: 800; font-size: 1rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
.pp-item-value.plus { color: var(--pp-green); }
.pp-item-sub { color: var(--pp-muted); font-size: .8rem; margin-top: .25rem; }
</style>
"""


def is_app() -> bool:
    """스마트폰 앱(User-Agent에 PedalPointApp)이나 ?app=1 로 접속했는지. 세션 동안 유지한다."""
    if "app_mode" not in st.session_state:
        try:
            ua = st.context.headers.get("User-Agent", "")
        except Exception:
            ua = ""
        st.session_state["app_mode"] = "PedalPointApp" in ua or st.query_params.get("app") == "1"
    return st.session_state["app_mode"]


def apply_style() -> None:
    st.markdown(CSS + (APP_CSS if is_app() else ""), unsafe_allow_html=True)


def list_items(items: list[tuple]) -> None:
    """모바일 목록. items: (제목 HTML, 오른쪽 값 HTML, 보조 문구, 값 강조 여부)"""
    html = "".join(
        f'<div class="pp-item"><div class="pp-item-top"><div class="pp-item-title">{title}</div>'
        f'<div class="pp-item-value{" plus" if plus else ""}">{value}</div></div>'
        f'<div class="pp-item-sub">{sub}</div></div>'
        for title, value, sub, plus in items
    )
    st.markdown(f'<div class="pp-list">{html}</div>', unsafe_allow_html=True)


def _data_uri(name: str) -> str:
    data = (ASSETS / name).read_bytes()
    mime = "image/svg+xml" if name.endswith(".svg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def bike_data_uri() -> str:
    return _data_uri("bike.png")


def logo_icon_uri() -> str:
    return _data_uri("logo_icon.svg")


def page_header(eyebrow: str, title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="pp-head"><div class="pp-eyebrow">{eyebrow}</div>'
        f'<div class="pp-title">{title}</div>'
        + (f'<div class="pp-sub">{sub}</div>' if sub else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def card_title(title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="pp-card-title">{title}</div>'
        + (f'<div class="pp-card-sub">{sub}</div>' if sub else '<div style="height:.5rem"></div>'),
        unsafe_allow_html=True,
    )


def badge(code: str, text: str | None = None) -> str:
    return f'<span class="pp-badge {BADGE_COLORS.get(code, "gray")}">{text or label(code)}</span>'


def stat_cards(items: list[tuple]) -> None:
    """items: (라벨, 값, 단위, 강조 여부)"""
    cards = []
    for name, value, unit, accent in items:
        cls = "pp-stat accent" if accent else "pp-stat"
        unit_html = f"<small>{unit}</small>" if unit else ""
        cards.append(
            f'<div class="{cls}"><div class="pp-stat-label">{name}</div>'
            f'<div class="pp-stat-value">{value}{unit_html}</div></div>'
        )
    st.markdown(f'<div class="pp-stats">{"".join(cards)}</div>', unsafe_allow_html=True)


def calc_rows(rows: list[tuple], total: tuple | None = None) -> None:
    """rows: (항목, 값). 값이 '- '로 시작하면 할인 줄로 표시한다."""
    html = "".join(
        f'<div class="pp-row{" minus" if str(v).startswith("- ") else ""}">'
        f"<span>{k}</span><span>{v}</span></div>"
        for k, v in rows
    )
    if total:
        html += f'<div class="pp-row total"><span>{total[0]}</span><span>{total[1]}</span></div>'
    st.markdown(f'<div class="pp-rows">{html}</div>', unsafe_allow_html=True)


def empty(icon: str, title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="pp-empty"><div class="pp-empty-icon">{icon}</div>'
        f'<div class="pp-empty-title">{title}</div><div>{sub}</div></div>',
        unsafe_allow_html=True,
    )


def done(title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="pp-done"><div class="pp-done-icon">✓</div><div>'
        f'<div class="pp-done-title">{title}</div><div class="pp-done-sub">{sub}</div></div></div>',
        unsafe_allow_html=True,
    )


def flash(key: str) -> None:
    """직전 동작의 완료 메시지(session_state[key])를 한 번 보여준다."""
    if msg := st.session_state.pop(key, None):
        done(msg)


# ---------------------------------------------------------------- 포맷터
def won(v) -> str:
    return f"{int(v):,}원"


def pt(v) -> str:
    return f"{int(v):,}P"


def km(v) -> str:
    return "-" if v is None else f"{Decimal(v):,.2f}km"


def carbon(g) -> str:
    g = Decimal(g)
    if g >= 1000:
        return f"{g / 1000:,.2f}kg"
    return f"{g:,.0f}g"


def dt(v: datetime | None) -> str:
    return "-" if v is None else v.strftime("%Y-%m-%d %H:%M")


def minutes(v: float) -> str:
    total = int(v)
    h, m = divmod(total, 60)
    return f"{h}시간 {m}분" if h else f"{m}분"


def label(code: str | None) -> str:
    return "-" if code is None else STATUS_LABELS.get(code, code)
