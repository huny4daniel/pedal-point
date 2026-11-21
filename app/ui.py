"""공통 UI: 스타일, 머리말, 카드·지표·배지 컴포넌트, 포맷터."""
import base64
import html
import secrets
import threading
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import streamlit as st

import rules

ASSETS = Path(__file__).parent / "assets"

STATUS_LABELS = {
    # user
    "ACTIVE": "정상", "SUSPENDED": "이용정지", "WITHDRAWN": "탈퇴",
    # station
    "INACTIVE": "운영중지",
    # bicycle
    "AVAILABLE": "대여가능", "RENTED": "대여중", "MAINTENANCE": "정비중",
}
STATION_STATUS_LABELS = {"ACTIVE": "운영중", "INACTIVE": "운영중지"}

BADGE_COLORS = {
    "ACTIVE": "green", "AVAILABLE": "green", "반납 완료": "green", "적립": "green",
    "RENTED": "amber", "대여 중": "amber", "결제 대기": "amber", "MAINTENANCE": "amber", "SUSPENDED": "amber",
    "사용": "gray", "INACTIVE": "red", "WITHDRAWN": "red",
}


def rental_state(r: dict) -> str:
    """rental 행(payment_id 포함)의 상태: 대여 중 / 결제 대기 / 반납 완료."""
    if r["rental_end_time"] is None:
        return "대여 중"
    return "결제 대기" if r.get("payment_id") is None else "반납 완료"


CSS = """
<style>
.st-key-pp_viewport { display: none !important; }
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
/* 앱 배경: 옅은 초록 그라데이션 + 점 패턴 (흰 여백이 비어 보이지 않게) */
[data-testid="stApp"] {
  background:
    radial-gradient(circle at 88% -8%, rgba(18,183,106,.20), transparent 38%),
    radial-gradient(circle at -6% 108%, rgba(15,42,31,.12), transparent 42%),
    radial-gradient(rgba(15,42,31,.07) 1px, transparent 1.2px) 0 0 / 22px 22px,
    #EDF3EF;
  background-attachment: fixed;
}
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 1480px; padding-top: 1.4rem; padding-bottom: 2.5rem;
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
/* 화면 배치: 카드·지도가 든 단이 너무 좁아지면 아래로 내려 1단으로 (창 폭에 맞춰 자동) */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] :is([class*="st-key-ppcard_"], .pp-map, .pp-action)) {
  flex-wrap: wrap; row-gap: 1rem;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(:is([class*="st-key-ppcard_"], .pp-action)):not(:has(.st-key-ppcard_login)) {
  min-width: min(100%, 360px);
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(.pp-map) { min-width: min(100%, 460px); }

/* 머리말 배너 */
.pp-head { display: flex; align-items: center; justify-content: space-between; gap: 1.2rem; flex-wrap: wrap;
           margin-bottom: 1.1rem; padding: 1.25rem 1.5rem; border-radius: 22px; color: #fff; position: relative;
           overflow: hidden; background: var(--pp-forest);
           background-image: radial-gradient(circle at 100% 0%, rgba(18,183,106,.45), transparent 45%),
                             radial-gradient(circle at 0% 140%, rgba(18,183,106,.22), transparent 40%); }
.pp-head::after { content: ""; position: absolute; right: -40px; bottom: -60px; width: 260px; height: 160px;
                  border: 2px dashed rgba(255,255,255,.10); border-radius: 50%; pointer-events: none; }
.pp-eyebrow { color: #7EE2B1; font-weight: 700; font-size: .8rem; margin-bottom: .2rem; letter-spacing: .02em; }
.pp-title { color: #fff; font-weight: 800; font-size: 1.7rem; letter-spacing: -0.035em; line-height: 1.2; }
.pp-sub { color: #B9D4C6; font-size: .92rem; margin-top: .3rem; }
.pp-band-stats { display: flex; gap: .6rem; flex-wrap: wrap; position: relative; z-index: 1; }
.pp-band-stat { background: rgba(255,255,255,.09); border: 1px solid rgba(255,255,255,.14); border-radius: 14px;
                padding: .55rem .9rem; min-width: 96px; }
.pp-band-stat b { display: block; font-size: 1.2rem; font-weight: 800; letter-spacing: -0.02em; color: #fff; }
.pp-band-stat span { font-size: .74rem; color: #A9C9B8; }

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
.pp-login-note { color: var(--pp-muted); font-size: .78rem; margin-top: .9rem; text-align: center;
                 background: var(--pp-bg); border-radius: 10px; padding: .55rem .7rem; line-height: 1.5; }
.st-key-ppcard_login [data-testid="stForm"] { padding: 0; }
[data-baseweb="input"] [data-testid="stIconMaterial"] { color: var(--pp-muted) !important; }
.pp-app-brand { text-align: center; padding: 2.6rem 0 1.6rem 0; }
.pp-app-brand img { width: 64px; height: 64px; border-radius: 18px; box-shadow: 0 10px 24px rgba(15,42,31,.25); }
.pp-app-name { font-size: 1.7rem; font-weight: 800; letter-spacing: -0.04em; color: var(--pp-ink); margin-top: .9rem; }
.pp-app-tag { color: var(--pp-muted); font-size: .92rem; margin-top: .25rem; }
.pp-app-tag em { font-style: normal; color: var(--pp-green); font-weight: 700; }

/* 지도 (Leaflet) */
.pp-map { width: 100%; border-radius: 18px; overflow: hidden; border: 1px solid var(--pp-line);
          box-shadow: var(--pp-shadow); background: #E6ECE8; position: relative; z-index: 0; }
.pp-map .leaflet-control-attribution { font-size: 10px; }
.pp-pin-wrap { position: relative; }
.pp-pin { position: absolute; left: -19px; top: -46px; width: 38px; height: 38px;
          border-radius: 50% 50% 50% 4px; transform: rotate(-45deg); display: grid; place-items: center;
          background: var(--pp-green-2); border: 3px solid #fff; cursor: pointer;
          box-shadow: 0 4px 10px rgba(15,26,21,.28); transition: transform .12s ease; }
.pp-pin:hover { transform: rotate(-45deg) scale(1.08); }
.pp-pin b { transform: rotate(45deg); color: #fff; font-weight: 800; font-size: 14px; line-height: 1; }
.pp-pin.gray { background: #9AA6A0; }
.pp-pin.blue { background: #2E7CF6; }
.pp-pin.red { background: #D92D20; }
.pp-pin.pick { background: var(--pp-amber); }
.pp-pin.sel { left: -24px; top: -57px; width: 48px; height: 48px; background: var(--pp-forest);
              box-shadow: 0 0 0 6px rgba(18,183,106,.35), 0 6px 14px rgba(15,26,21,.35); }
.pp-pin.sel b { font-size: 16px; }
.pp-pin-label { position: absolute; top: 6px; left: 0; transform: translateX(-50%); white-space: nowrap;
                background: #fff; color: var(--pp-ink); font-weight: 700; font-size: 12px; padding: 3px 9px;
                border-radius: 8px; box-shadow: 0 2px 8px rgba(15,26,21,.22); pointer-events: none; }
.pp-legend { display: flex; flex-wrap: wrap; gap: .9rem; font-size: .8rem; color: var(--pp-muted); margin: .55rem .2rem 0 .2rem; }
.pp-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: .35rem;
               vertical-align: -1px; }

/* 홈: 행동 카드 (이용하기 / 이용 중 / 결제 대기) */
.pp-action { border-radius: 20px; padding: 1.3rem 1.4rem; margin-bottom: .6rem; color: #fff; min-height: 210px;
             display: flex; flex-direction: column; background: var(--pp-green);
             background-image: radial-gradient(circle at 100% 0%, rgba(255,255,255,.22), transparent 50%),
                               linear-gradient(135deg, #0A8A55, #12B76A); box-shadow: 0 10px 28px rgba(10,138,85,.28); }
.pp-action.riding { background: var(--pp-forest);
                    background-image: radial-gradient(circle at 100% 0%, rgba(18,183,106,.45), transparent 50%); }
.pp-action.pending { background: #8A4A0B; background-image: linear-gradient(135deg, #B54708, #DC6803); }
.pp-action-tag { font-size: .78rem; font-weight: 700; opacity: .85; }
.pp-action-title { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.035em; margin-top: .3rem; }
.pp-action-sub { font-size: .88rem; opacity: .85; margin-top: .2rem; }
.pp-action-nums { display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: .5rem; margin-top: auto; padding-top: 1rem; }
.pp-action-nums div { background: rgba(255,255,255,.13); border-radius: 12px; padding: .55rem .7rem; }
.pp-action-nums b { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 1.1rem; font-weight: 800; letter-spacing: -0.02em; }
.pp-action-nums span { font-size: .72rem; opacity: .8; }
.pp-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: .6rem; }
.pp-tile { background: var(--pp-bg); border-radius: 14px; padding: .75rem .85rem; }
.pp-tile i { font-style: normal; font-size: 1.05rem; }
.pp-tile b { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 1.25rem; font-weight: 800; color: var(--pp-ink); letter-spacing: -0.03em; margin-top: .2rem; }
.pp-tile span { font-size: .76rem; color: var(--pp-muted); white-space: nowrap; }
.pp-action, .pp-tile, .pp-band-stat, .pp-sheet-num { word-break: keep-all; }

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

/* 탄소 절감 체감 카드 */
.pp-eco { border-radius: 20px; padding: 1.2rem 1.3rem; margin-bottom: 1rem; border: 1px solid var(--pp-line);
          background: var(--pp-surface); box-shadow: var(--pp-shadow);
          background-image: radial-gradient(circle at 0% 0%, var(--pp-green-soft), transparent 55%); }
.pp-eco-head { display: flex; justify-content: space-between; align-items: baseline; gap: .6rem; flex-wrap: wrap; margin-bottom: .9rem; }
.pp-eco-head b { font-size: 1.05rem; font-weight: 800; color: var(--pp-ink); letter-spacing: -0.02em; }
.pp-eco-head span { font-size: .8rem; color: var(--pp-muted); }
.pp-eco-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: .8rem; }
.pp-eco-box { background: var(--pp-bg); border-radius: 16px; padding: .95rem 1rem; }
.pp-eco-level { display: flex; gap: .9rem; align-items: center; }
.pp-eco-tree { font-size: 2.6rem; line-height: 1; flex: 0 0 auto; filter: drop-shadow(0 4px 8px rgba(18,183,106,.25)); }
.pp-eco-k { font-size: .76rem; color: var(--pp-muted); font-weight: 600; }
.pp-eco-big { font-size: 1.7rem; font-weight: 800; color: var(--pp-green); letter-spacing: -0.035em; line-height: 1.15; }
.pp-eco-lv { font-size: .86rem; font-weight: 700; color: var(--pp-ink); }
.pp-eco-bar { height: 8px; background: var(--pp-line-2); border-radius: 99px; overflow: hidden; margin: .65rem 0 .35rem 0; }
.pp-eco-bar i { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, #7CD4A6, #12B76A); }
.pp-eco-note { font-size: .76rem; color: var(--pp-muted); }
.pp-eco-eq { display: flex; flex-direction: column; gap: .55rem; }
.pp-eco-eq div { display: flex; align-items: center; gap: .65rem; }
.pp-eco-eq i { font-style: normal; font-size: 1.35rem; width: 2rem; text-align: center; }
.pp-eco-eq b { display: block; font-size: 1.05rem; font-weight: 800; color: var(--pp-ink); letter-spacing: -0.02em; }
.pp-eco-eq span { font-size: .76rem; color: var(--pp-muted); }
.pp-eco-goal { display: flex; align-items: center; gap: .9rem; }
.pp-ring { width: 84px; height: 84px; border-radius: 50%; flex: 0 0 auto; display: grid; place-items: center;
           background: conic-gradient(#12B76A calc(var(--p) * 1%), var(--pp-line-2) 0); }
.pp-ring b { width: 64px; height: 64px; border-radius: 50%; background: var(--pp-bg); display: grid; place-items: center;
             font-size: 1rem; font-weight: 800; color: var(--pp-ink); }
.pp-eco-foot { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .85rem; }
.pp-eco-foot span { background: var(--pp-green-soft); color: var(--pp-green); font-size: .78rem; font-weight: 600;
                    padding: .3rem .7rem; border-radius: 99px; }
.pp-eco-inline { display: flex; flex-wrap: wrap; gap: .4rem; margin: .3rem 0 .2rem 0; }
.pp-eco-inline span { background: var(--pp-bg); color: var(--pp-ink-2); font-size: .78rem; font-weight: 600;
                      padding: .28rem .65rem; border-radius: 99px; }

.pp-unit { font-size: 1.05rem; font-weight: 800; color: var(--pp-ink-2); }

/* 이용 중 카드 */
.pp-ride { display: flex; align-items: center; gap: 1rem; color: #fff; border-radius: 18px;
           padding: 1rem 1.2rem; margin-bottom: 1.1rem; background: var(--pp-forest);
           background-image: radial-gradient(circle at 100% 0%, rgba(18,183,106,.4), transparent 55%); }
.pp-ride-dot { width: 42px; height: 42px; border-radius: 12px; background: rgba(255,255,255,.12);
               display: grid; place-items: center; font-size: 1.3rem; flex: 0 0 auto; }
.pp-ride-main { flex: 1 1 auto; min-width: 0; }
.pp-ride-tag { font-size: .75rem; font-weight: 700; color: #7EE2B1; letter-spacing: .02em; }
.pp-ride-title { font-weight: 800; font-size: 1.05rem; letter-spacing: -0.02em; }
.pp-ride-sub { font-size: .8rem; color: #A9C9B8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pp-ride-num { text-align: right; flex: 0 0 auto; }
.pp-ride-num b { display: block; font-size: 1.35rem; font-weight: 800; letter-spacing: -0.03em; }
.pp-ride-num span { font-size: .75rem; color: #A9C9B8; }

/* 대여소 정보 카드 (지도에서 고른 대여소) */
.pp-sheet-name { font-weight: 800; font-size: 1.3rem; color: var(--pp-ink); letter-spacing: -0.03em; }
.pp-sheet-addr { color: var(--pp-muted); font-size: .86rem; margin: .2rem 0 .9rem 0; }
.pp-sheet-nums { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; margin-bottom: 1rem; }
.pp-sheet-num { background: var(--pp-bg); border-radius: 12px; padding: .6rem .7rem; text-align: center; }
.pp-sheet-num b { display: block; font-size: 1.25rem; font-weight: 800; color: var(--pp-ink); letter-spacing: -0.02em; }
.pp-sheet-num span { font-size: .74rem; color: var(--pp-muted); }
.pp-sheet-num.on b { color: var(--pp-green); }
.pp-fee { display: flex; gap: .45rem; flex-wrap: wrap; margin: .2rem 0 .9rem 0; }
.pp-fee span { background: var(--pp-green-soft); color: var(--pp-green); font-size: .76rem; font-weight: 600;
               padding: .25rem .6rem; border-radius: 99px; }
.pp-steps { display: flex; gap: .4rem; margin: .4rem 0 1.1rem 0; }
.pp-step { flex: 1 1 0; font-size: .78rem; color: var(--pp-muted); font-weight: 600; padding-top: .45rem;
           border-top: 3px solid var(--pp-line); }
.pp-step.on { color: var(--pp-green); border-top-color: var(--pp-green-2); }

@media (max-width: 1100px) { .pp-hero-bike { display: none; } }
@media (max-width: 760px) {
  .pp-hero { min-height: 0; padding: 1.8rem; }
  .pp-hero-title { font-size: 2rem; margin-top: 1.6rem; }
}
</style>
"""


MOBILE_CSS = """
<style>
/* ---- 모바일 전용 화면 (세로 비율 창): 이용자 전용 레이아웃 ---- */
header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"], [data-testid="stToolbar"], [data-testid="stStatusWidget"] {
  display: none !important;
}
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 480px; padding: .6rem 1rem calc(6.2rem + env(safe-area-inset-bottom)) 1rem !important;
}
.pp-head { margin-bottom: .8rem; padding: 1rem 1.1rem; border-radius: 18px; gap: .7rem; }
.pp-title { font-size: 1.3rem; }
.pp-sub { font-size: .82rem; }
.pp-band-stats { width: 100%; gap: .4rem; }
.pp-band-stat { flex: 1 1 0; min-width: 0; padding: .45rem .6rem; }
.pp-band-stat b { font-size: 1rem; }
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

</style>
"""


# 다크 모드: Streamlit 위젯은 config.toml의 [theme.dark], 우리 CSS는 색 변수를 바꿔서 맞춘다
DARK_CSS = """
<style>
:root {
  --pp-bg: #16201C; --pp-surface: #18221E; --pp-line: #26332D; --pp-line-2: #22302A;
  --pp-ink: #E6EFEA; --pp-ink-2: #B9C7C0; --pp-muted: #8C9C94;
  --pp-green: #34D399; --pp-green-soft: rgba(18,183,106,.16);
  --pp-amber: #F5B14C; --pp-amber-soft: rgba(245,177,76,.14);
  --pp-red: #F97066; --pp-red-soft: rgba(249,112,102,.14); --pp-gray-soft: #24302A;
  --pp-shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25);
}
[data-testid="stApp"] {
  background:
    radial-gradient(circle at 88% -8%, rgba(18,183,106,.16), transparent 38%),
    radial-gradient(circle at -6% 108%, rgba(18,183,106,.08), transparent 42%),
    radial-gradient(rgba(255,255,255,.045) 1px, transparent 1.2px) 0 0 / 22px 22px,
    #0C1411;
  background-attachment: fixed;
}
.pp-head { background-color: #0B1F17; border: 1px solid #1E3A2E; }
.pp-stat.accent { background-color: #0B1F17; border-color: #1E3A2E; }
[data-testid="stTabs"] [role="tablist"] { background: #1A2621; }
[data-testid="stTab"][aria-selected="true"] { background: #2A3832; }
.pp-pin { border-color: #0C1411; }
.pp-pin-label { background: #18221E; color: #E6EFEA; }
.pp-map { background: #1A2621; }
.pp-map .leaflet-tile-pane { filter: invert(1) hue-rotate(180deg) brightness(.92) contrast(.9) saturate(.6); }
.pp-map .leaflet-control-zoom a, .pp-map .leaflet-bar a { background: #18221E; color: #E6EFEA; border-color: #26332D; }
.pp-map .leaflet-control-attribution { background: rgba(12,20,17,.7); color: #8C9C94; }
.pp-map .leaflet-tooltip { background: #18221E; color: #E6EFEA; border-color: #26332D; }
.pp-done { border-color: #1E5A3E; }
.st-key-ppbar .stButton button { background: #18221E; }
.st-key-ppnav { background: rgba(17,26,22,.96) !important; }
.pp-login-note { background: #16201C; }
</style>
"""


def is_dark() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


# 브라우저 창 비율 감지 + 테마 전환.
#  - 세로가 더 길거나 폭이 640px 이하이면 모바일 전용 화면. 창 크기가 바뀌면 같은 세션(로그인 유지)에서 다시 그린다.
#  - 테마 전환: Streamlit은 고른 테마를 localStorage(stActiveTheme-<경로>-v2)에 두고 새로고침 때 읽는다.
#    새로고침하면 세션이 새로 만들어지므로, 1분짜리 일회용 토큰을 sessionStorage에 넘겨 로그인을 이어받는다.
_VIEWPORT_JS = """
export default function (component) {
  const { data, setStateValue } = component;
  const sw = data.switch;
  if (sw && window.__ppSwitched !== sw.token) {
    window.__ppSwitched = sw.token;
    sessionStorage.setItem("ppResume", sw.token);
    for (const p of new Set([window.location.pathname, ...sw.paths])) {
      localStorage.setItem(`stActiveTheme-${p}-v2`, JSON.stringify(sw.theme));
    }
    window.location.reload();
    return;
  }
  const resume = sessionStorage.getItem("ppResume");
  if (resume) { sessionStorage.removeItem("ppResume"); setStateValue("resume", resume); }

  const isMobile = () => window.innerHeight > window.innerWidth || window.innerWidth <= 640;
  const send = () => {
    const m = isMobile();
    if (m !== data.mobile) setStateValue("mobile", m);  // 서버가 아는 값과 다를 때만 알림
  };
  send();
  let timer;
  const onResize = () => { clearTimeout(timer); timer = setTimeout(send, 150); };
  window.addEventListener("resize", onResize);
  return () => { window.removeEventListener("resize", onResize); clearTimeout(timer); };
}
"""
_viewport = st.components.v2.component("pp_viewport", js=_VIEWPORT_JS)

_RESUME: dict[str, tuple[dict, float]] = {}  # 토큰 → (복원할 로그인 상태, 만든 시각)
_RESUME_LOCK = threading.Lock()
_RESUME_KEYS = ("role", "user_id", "staff_id", "viewport_mobile")
_ALL_PATHS = ["/", "/home", "/ride", "/mypage", "/login", "/assets", "/history", "/members"]


def _take_resume(token: str) -> dict | None:
    """일회용 토큰으로 로그인 상태를 돌려받는다 (60초 안, 한 번만)."""
    now = time.time()
    with _RESUME_LOCK:
        for t in [t for t, (_, ts) in _RESUME.items() if now - ts > 60]:
            _RESUME.pop(t, None)
        item = _RESUME.pop(token, None)
    return item[0] if item else None


def sync_viewport() -> None:
    """화면 맨 처음에 호출. 창 비율(session_state["viewport_mobile"])을 맞추고, 테마 전환·로그인 복원을 처리한다."""
    known = st.session_state.get("viewport_mobile")
    switch = st.session_state.pop("_theme_switch", None)
    res = _viewport(key="pp_viewport", data={"mobile": known, "switch": switch},
                    on_mobile_change=lambda: None, on_resume_change=lambda: None)
    mobile = getattr(res, "mobile", None)
    if mobile is not None:
        st.session_state["viewport_mobile"] = bool(mobile)
    token = getattr(res, "resume", None)
    if token and not st.session_state.get("_resumed"):
        st.session_state["_resumed"] = True
        if saved := _take_resume(str(token)):
            st.session_state.update(saved)
            st.rerun()


def theme_toggle(key: str, label: bool = True) -> None:
    """다크/라이트 전환 버튼. 누르면 새로고침하되 로그인은 그대로 이어진다."""
    dark = is_dark()
    text = ("라이트 모드" if dark else "다크 모드") if label else ""
    if st.button(text, key=key, icon=":material/light_mode:" if dark else ":material/dark_mode:",
                 help="라이트 모드로" if dark else "다크 모드로", width="stretch" if label else "content"):
        token = secrets.token_urlsafe(16)
        saved = {k: st.session_state[k] for k in _RESUME_KEYS if k in st.session_state}
        with _RESUME_LOCK:
            _RESUME[token] = (saved, time.time())
        st.session_state["_theme_switch"] = {"theme": "Light" if dark else "Dark", "token": token,
                                             "paths": _ALL_PATHS}
        st.rerun()


def is_mobile() -> bool:
    """모바일 전용 화면 여부. 이용자(와 로그인 화면)만 해당하고, 관리자는 항상 PC 화면."""
    return bool(st.session_state.get("viewport_mobile")) and st.session_state.get("role") != "admin"


def apply_style() -> None:
    st.markdown(CSS + (MOBILE_CSS if is_mobile() else "") + (DARK_CSS if is_dark() else ""),
                unsafe_allow_html=True)


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


def page_header(eyebrow: str, title: str, sub: str = "", stats: list[tuple] | None = None) -> None:
    """화면 머리말 배너 (숲색 배경). stats: [(라벨, 값)] — 배너 오른쪽에 핵심 수치."""
    chips = "".join(f'<div class="pp-band-stat"><b>{v}</b><span>{k}</span></div>' for k, v in (stats or []))
    st.markdown(
        f'<div class="pp-head"><div class="pp-band-text"><div class="pp-eyebrow">{eyebrow}</div>'
        f'<div class="pp-title">{title}</div>'
        + (f'<div class="pp-sub">{sub}</div>' if sub else "")
        + "</div>"
        + (f'<div class="pp-band-stats">{chips}</div>' if chips else "")
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


# ---------------------------------------------------------------- 이동·이스케이프
def esc(v) -> str:
    """DB 값(이름·주소 등)을 HTML에 넣을 때 이스케이프한다."""
    return html.escape("" if v is None else str(v))


def go(url_path: str) -> None:
    """다른 메뉴로 이동 (main.py가 등록한 st.Page 사용)."""
    page = st.session_state.get("_pages", {}).get(url_path)
    if page is not None:
        st.switch_page(page)


# ---------------------------------------------------------------- 탄소 절감 체감
def _num(v, small_digits: int = 1) -> str:
    v = float(v)
    return f"{v:,.{small_digits}f}" if v < 10 else f"{v:,.0f}"


def carbon_equiv_chips(carbon_g) -> str:
    """줄인 탄소를 생활 수치로 바꾼 작은 칩 (영수증·반납 화면용)."""
    if not carbon_g:
        return ""
    e = rules.carbon_equivalents(carbon_g)
    return ('<div class="pp-eco-inline">'
            f'<span>🚗 승용차 {_num(e["car_km"])}km 대신 달렸어요</span>'
            f'<span>🌲 소나무 {_num(e["pine_days"])}그루의 하루 흡수량</span></div>')


def carbon_impact(total_g, month_g, rank: dict | None = None, community_g=None, title: str = "내가 줄인 탄소") -> None:
    """탄소 절감 체감 카드: 나의 숲 단계·누적 절감량, 생활 속 환산, 이번 달 목표, 순위·함께 줄인 양."""
    lv = rules.carbon_level(total_g)
    eq = rules.carbon_equivalents(total_g)
    pct = min(float(Decimal(str(month_g or 0)) / rules.MONTH_GOAL_G * 100), 100.0)
    remain_goal = max(rules.MONTH_GOAL_G - Decimal(str(month_g or 0)), Decimal(0))
    nxt = (f"다음 단계 {lv['next_icon']} {lv['next_name']}까지 {carbon(lv['remain_g'])}" if lv["next_name"]
           else "가장 높은 단계에 도착했어요!")
    foot = []
    if rank and rank.get("rank"):
        foot.append(f"🏅 이용자 {rank['riders']}명 중 {rank['rank']}위 · 상위 {rank['top_pct']}%")
    if community_g is not None:
        ce = rules.carbon_equivalents(community_g)
        foot.append(f"🌍 Pedal Point 이용자가 함께 줄인 탄소 {carbon(community_g)} "
                    f"= 소나무 {_num(ce['pine_years'])}그루의 1년 흡수량")
    st.markdown(
        f'<div class="pp-eco"><div class="pp-eco-head"><b>{title}</b>'
        f'<span>자전거 1km = 승용차 대신 탄소 {rules.CARBON_G_PER_KM}g 절감</span></div>'
        f'<div class="pp-eco-grid">'
        # 1) 나의 숲
        f'<div class="pp-eco-box"><div class="pp-eco-level"><div class="pp-eco-tree">{lv["icon"]}</div><div>'
        f'<div class="pp-eco-k">나의 숲 · {lv["step"]}/{lv["steps"]}단계</div>'
        f'<div class="pp-eco-big">{carbon(total_g)}</div>'
        f'<div class="pp-eco-lv">{lv["name"]}</div></div></div>'
        f'<div class="pp-eco-bar"><i style="width:{lv["progress"] * 100:.0f}%"></i></div>'
        f'<div class="pp-eco-note">{nxt}</div></div>'
        # 2) 생활 속 환산
        f'<div class="pp-eco-box pp-eco-eq">'
        f'<div><i>🚗</i><div><b>{_num(eq["car_km"])}km</b><span>승용차 대신 달린 거리</span></div></div>'
        f'<div><i>🌲</i><div><b>{_num(eq["pine_days"])}그루</b><span>소나무가 하루 동안 흡수하는 양</span></div></div>'
        f'<div><i>🌳</i><div><b>{_num(eq["pine_years"], 2)}그루</b><span>소나무가 1년 동안 흡수하는 양</span></div></div>'
        f"</div>"
        # 3) 이번 달 목표
        f'<div class="pp-eco-box pp-eco-goal"><div class="pp-ring" style="--p:{pct:.0f}"><b>{pct:.0f}%</b></div><div>'
        f'<div class="pp-eco-k">이번 달 목표 {carbon(rules.MONTH_GOAL_G)}</div>'
        f'<div class="pp-eco-big" style="font-size:1.35rem">{carbon(month_g or 0)}</div>'
        f'<div class="pp-eco-note">' + (f"목표까지 {carbon(remain_goal)} 남았어요" if remain_goal > 0
                                        else "이번 달 목표 달성! 🎉") + "</div></div></div>"
        f"</div>"
        + (f'<div class="pp-eco-foot">{"".join(f"<span>{x}</span>" for x in foot)}</div>' if foot else "")
        + "</div>",
        unsafe_allow_html=True,
    )


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
