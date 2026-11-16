"""공통 UI: 표지 디자인 기반 스타일, 헤더, 지표 카드, 포맷터."""
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

CSS = """
<style>
:root {
  --pp-bg: #0F2A1F;
  --pp-surface: #173A2B;
  --pp-line: #2A4D3C;
  --pp-green: #2FBF71;
  --pp-green-deep: #17804A;
  --pp-text: #F4F6F0;
  --pp-mint: #B9D4C6;
  --pp-muted: #8FAE9F;
}
.block-container { padding-top: 2.4rem; max-width: 1180px; }
h1, h2, h3 { letter-spacing: -0.02em; }

/* 페이지 머리말: 표지의 초록 라벨 + 굵은 제목 구성 */
.pp-eyebrow {
  color: var(--pp-green); font-weight: 700; font-size: .82rem;
  letter-spacing: .12em; margin-bottom: .25rem;
}
.pp-title {
  color: var(--pp-text); font-weight: 900; font-size: 2.2rem;
  letter-spacing: -0.03em; line-height: 1.15; margin: 0 0 .35rem 0;
}
.pp-sub { color: var(--pp-mint); font-size: 1rem; margin-bottom: 1.4rem; }

/* 표지 히어로 */
.pp-hero {
  display: flex; align-items: center; gap: 2rem;
  padding: 3.2rem 0 2.4rem 0; border-bottom: 1px solid var(--pp-line);
  margin-bottom: 2rem;
}
.pp-hero-text { flex: 1 1 auto; min-width: 0; }
.pp-hero .pp-title { font-size: 4.2rem; letter-spacing: -0.045em; margin-bottom: .8rem; }
.pp-hero .pp-sub { font-size: 1.35rem; color: var(--pp-text); margin-bottom: .9rem; }
.pp-hero .pp-note { color: var(--pp-mint); font-size: .95rem; }
.pp-hero img { width: 38%; max-width: 380px; flex: 0 0 auto; }
@media (max-width: 760px) {
  .pp-hero { flex-direction: column; align-items: flex-start; padding-top: 1.6rem; }
  .pp-hero .pp-title { font-size: 2.8rem; }
  .pp-hero img { width: 70%; }
}

/* 지표 카드 */
.pp-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: .8rem; margin: .4rem 0 1.4rem 0; }
.pp-stat { background: var(--pp-surface); border: 1px solid var(--pp-line);
           border-radius: 12px; padding: 1rem 1.1rem; }
.pp-stat-label { color: var(--pp-mint); font-size: .8rem; margin-bottom: .3rem; }
.pp-stat-value { color: var(--pp-text); font-size: 1.55rem; font-weight: 700;
                 font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.pp-stat-value small { font-size: .85rem; color: var(--pp-mint); font-weight: 500; margin-left: .2rem; }
.pp-stat.accent { border-color: var(--pp-green); }
.pp-stat.accent .pp-stat-value { color: var(--pp-green); }

/* 계산 내역 줄 */
.pp-rows { background: var(--pp-surface); border: 1px solid var(--pp-line);
           border-radius: 12px; padding: .6rem 1.1rem; margin-bottom: 1rem; }
.pp-row { display: flex; justify-content: space-between; padding: .45rem 0;
          border-bottom: 1px dashed var(--pp-line); font-variant-numeric: tabular-nums; }
.pp-row:last-child { border-bottom: none; }
.pp-row span:first-child { color: var(--pp-mint); }
.pp-row.total span { color: var(--pp-text); font-weight: 700; font-size: 1.1rem; }
.pp-row.total span:last-child { color: var(--pp-green); }

/* 사이드바 브랜드 */
.pp-brand { font-weight: 900; font-size: 1.45rem; letter-spacing: -0.03em; color: var(--pp-text); }
.pp-brand-sub { color: var(--pp-green); font-size: .75rem; font-weight: 700; letter-spacing: .1em; }
.pp-who { color: var(--pp-mint); font-size: .88rem; margin: .8rem 0 .2rem 0; }
.pp-who b { color: var(--pp-text); }
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def bike_data_uri() -> str:
    data = (ASSETS / "bike.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def page_header(eyebrow: str, title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="pp-eyebrow">{eyebrow}</div>'
        f'<div class="pp-title">{title}</div>'
        + (f'<div class="pp-sub">{sub}</div>' if sub else ""),
        unsafe_allow_html=True,
    )


def stat_cards(items: list[tuple]) -> None:
    """items: (라벨, 값, 단위, 강조 여부)"""
    cards = []
    for label, value, unit, accent in items:
        cls = "pp-stat accent" if accent else "pp-stat"
        unit_html = f"<small>{unit}</small>" if unit else ""
        cards.append(
            f'<div class="{cls}"><div class="pp-stat-label">{label}</div>'
            f'<div class="pp-stat-value">{value}{unit_html}</div></div>'
        )
    st.markdown(f'<div class="pp-stats">{"".join(cards)}</div>', unsafe_allow_html=True)


def calc_rows(rows: list[tuple], total: tuple | None = None) -> None:
    html = "".join(f'<div class="pp-row"><span>{k}</span><span>{v}</span></div>' for k, v in rows)
    if total:
        html += f'<div class="pp-row total"><span>{total[0]}</span><span>{total[1]}</span></div>'
    st.markdown(f'<div class="pp-rows">{html}</div>', unsafe_allow_html=True)


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
