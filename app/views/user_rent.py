"""이용자 · 대여소 검색·대여."""
import streamlit as st

import rules
import ui
import user_ops
from db import BusinessError


def _station_card(s: dict, selected: bool) -> None:
    avail, docks = int(s["available_count"]), int(s["station_totaldocks"])
    ratio = 0 if docks == 0 else min(avail / docks, 1) * 100
    state = ui.badge("AVAILABLE", "대여 가능") if avail else ui.badge("INACTIVE", "자전거 없음")
    key = f"ppcard_sel_{s['station_id']}" if selected else f"ppcard_st_{s['station_id']}"
    with st.container(key=key):
        st.markdown(
            f'<div class="pp-station-top"><div class="pp-station-name">{s["station_name"]}</div>{state}</div>'
            f'<div class="pp-station-addr">{s["station_region"]} · {s["station_address"]}</div>'
            f'<div class="pp-avail"><b>{avail}</b><span>대 / 거치대 {docks}</span></div>'
            f'<div class="pp-meter"><i style="width:{ratio:.0f}%"></i></div>',
            unsafe_allow_html=True,
        )
        if st.button("선택됨" if selected else "이 대여소 선택", key=f"pick_{s['station_id']}",
                     type="primary" if selected else "secondary", width="stretch",
                     icon=":material/check:" if selected else None):
            st.session_state["rent_station"] = s["station_id"]
            st.rerun()


def _rent_panel(user_id: int, station: dict | None) -> None:
    with st.container(key="ppcard_rentpanel"):
        if station is None:
            ui.empty("🚲", "대여소를 선택하세요", "왼쪽 목록에서 대여소를 고르면<br>대여 가능한 자전거가 표시됩니다.")
            return

        ui.card_title(station["station_name"], f"{station['station_region']} · {station['station_address']}")
        bikes = user_ops.available_bicycles(station["station_id"])
        if not bikes:
            ui.empty("⏳", "대여 가능한 자전거가 없어요", "다른 대여소를 선택해 주세요.")
            return

        me = user_ops.get_user(user_id)
        if me["user_status"] != "ACTIVE":
            st.error("이용정지 상태라 대여할 수 없습니다. 관리자에게 문의해 주세요.")
            return

        bike_id = st.pills(
            f"자전거 선택 · {len(bikes)}대",
            [b["bicycle_id"] for b in bikes],
            format_func=lambda b: f"#{b}",
            default=bikes[0]["bicycle_id"],
            key=f"bike_pick_{station['station_id']}",
        )
        st.caption(f"기본 {rules.BASE_MINUTES}분 {ui.won(rules.BASE_FEE)} · 반납 시 이동거리만큼 마일리지가 적립됩니다.")
        if st.button("대여하기", type="primary", width="stretch", disabled=bike_id is None,
                     icon=":material/pedal_bike:"):
            try:
                rental_id = user_ops.rent_bicycle(user_id, station["station_id"], bike_id)
            except BusinessError as e:
                st.error(str(e))
            else:
                st.session_state["rent_done"] = (
                    f"자전거 #{bike_id} 대여를 시작했습니다 · 대여번호 {rental_id}"
                )
                st.session_state.pop("rent_station", None)
                st.rerun()


def render() -> None:
    user_id = st.session_state["user_id"]
    ui.page_header("이용자", "대여소 검색·대여", "가까운 대여소를 찾고 바로 자전거를 빌려 보세요.")
    if msg := st.session_state.pop("rent_done", None):
        ui.done(msg, "반납은 ‘반납·결제’ 메뉴에서 할 수 있습니다.")

    c1, c2 = st.columns([1, 2])
    region = c1.selectbox("지역", ["전체", *user_ops.regions()])
    keyword = c2.text_input("대여소 이름", placeholder="대여소 이름으로 검색 (예: 정왕)",
                            icon=":material/search:")
    stations = user_ops.search_stations(None if region == "전체" else region, keyword.strip())

    sel_id = st.session_state.get("rent_station")
    by_id = {s["station_id"]: s for s in stations}

    left, right = st.columns([1.7, 1], gap="large")
    with left:
        if not stations:
            with st.container(key="ppcard_nostation"):
                ui.empty("🔍", "조건에 맞는 대여소가 없어요", "지역이나 검색어를 바꿔 보세요.")
        else:
            st.markdown(f'<div class="pp-card-sub">운영 중인 대여소 {len(stations)}곳</div>',
                        unsafe_allow_html=True)
            cols = st.columns(2)
            for i, s in enumerate(stations):
                with cols[i % 2]:
                    _station_card(s, s["station_id"] == sel_id)
    with right:
        _rent_panel(user_id, by_id.get(sel_id))
