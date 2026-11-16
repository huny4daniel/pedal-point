"""이용자 · 대여소 검색·대여."""
import pandas as pd
import streamlit as st

import ui
import user_ops
from db import BusinessError


def render() -> None:
    user_id = st.session_state["user_id"]
    ui.page_header("RENT", "대여소 검색·대여", "지역·이름으로 대여소를 찾고 대여 가능한 자전거를 빌립니다.")

    if msg := st.session_state.pop("rent_done", None):
        st.success(msg)

    c1, c2 = st.columns([1, 2])
    region = c1.selectbox("지역", ["전체", *user_ops.regions()])
    keyword = c2.text_input("대여소 이름", placeholder="예: 정왕")
    stations = user_ops.search_stations(None if region == "전체" else region, keyword.strip())

    if not stations:
        st.info("조건에 맞는 운영 중인 대여소가 없습니다.")
        return

    df = pd.DataFrame(
        {
            "대여소": [s["station_name"] for s in stations],
            "지역": [s["station_region"] for s in stations],
            "주소": [s["station_address"] for s in stations],
            "연락처": [s["station_contactnumber"] or "-" for s in stations],
            "대여 가능": [int(s["available_count"]) for s in stations],
            "총 거치대": [s["station_totaldocks"] for s in stations],
        }
    )
    st.caption("대여소를 선택하면 대여 가능한 자전거가 표시됩니다.")
    event = st.dataframe(
        df, hide_index=True, width="stretch",
        on_select="rerun", selection_mode="single-row", key="station_table",
    )
    selected = event.selection.rows
    if not selected:
        return
    station = stations[selected[0]]

    st.subheader(f"{station['station_name']} · 대여 가능 자전거")
    bikes = user_ops.available_bicycles(station["station_id"])
    if not bikes:
        st.warning("이 대여소에는 지금 대여 가능한 자전거가 없습니다.")
        return

    me = user_ops.get_user(user_id)
    if me["user_status"] != "ACTIVE":
        st.error("이용정지 상태라 대여할 수 없습니다. 관리자에게 문의해 주세요.")
        return

    bike_id = st.radio(
        "자전거 선택",
        [b["bicycle_id"] for b in bikes],
        format_func=lambda b: f"자전거 #{b}",
        horizontal=True,
    )
    if st.button("대여하기", type="primary"):
        try:
            rental_id = user_ops.rent_bicycle(user_id, station["station_id"], bike_id)
        except BusinessError as e:
            st.error(str(e))
        else:
            st.session_state["rent_done"] = (
                f"자전거 #{bike_id} 대여를 시작했습니다 (대여번호 {rental_id}). "
                "반납은 ‘반납·결제’ 화면에서 할 수 있습니다."
            )
            st.rerun()
