"""관리자 · 대여소·자전거 관리: 등록·수정, 상태 변경."""
from decimal import Decimal

import pandas as pd
import streamlit as st

import admin_ops
import ui
from db import BusinessError

STATION_STATUSES = ["ACTIVE", "INACTIVE"]
BIKE_STATUSES = ["AVAILABLE", "MAINTENANCE"]


def _flash(key: str) -> None:
    ui.flash(key)


def _station_form(prefix: str, s: dict | None) -> dict | None:
    """등록·수정 공용 입력 폼. 제출되면 입력값 dict, 아니면 None."""
    s = s or {}
    with st.form(f"{prefix}_station_form", clear_on_submit=s == {}, border=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("대여소 이름 *", s.get("station_name", ""), max_chars=100)
        region = c2.text_input("지역명 *", s.get("station_region", ""), max_chars=50)
        address = st.text_input("주소 *", s.get("station_address", ""), max_chars=255)
        c3, c4, c5 = st.columns(3)
        contact = c3.text_input("연락처", s.get("station_contactnumber") or "", max_chars=20)
        lat = c4.number_input("위도", value=float(s["station_latitude"]) if s.get("station_latitude") is not None else None,
                              min_value=-90.0, max_value=90.0, format="%.7f", placeholder="선택 입력")
        lon = c5.number_input("경도", value=float(s["station_longitude"]) if s.get("station_longitude") is not None else None,
                              min_value=-180.0, max_value=180.0, format="%.7f", placeholder="선택 입력")
        c6, c7 = st.columns(2)
        docks = c6.number_input("총 거치대 수 *", min_value=0, value=int(s.get("station_totaldocks", 10)), step=1)
        status = c7.selectbox(
            "운영 상태", STATION_STATUSES,
            index=STATION_STATUSES.index(s.get("station_status", "ACTIVE")),
            format_func=ui.STATION_STATUS_LABELS.get,
        )
        submitted = st.form_submit_button("저장" if s else "등록", type="primary", width="stretch")
    if not submitted:
        return None
    return {
        "name": name, "region": region, "address": address, "contact": contact,
        "latitude": None if lat is None else Decimal(f"{lat:.7f}"),
        "longitude": None if lon is None else Decimal(f"{lon:.7f}"),
        "totaldocks": int(docks), "status": status,
    }


def _stations_tab() -> None:
    _flash("station_msg")
    stations = admin_ops.all_stations()
    st.dataframe(pd.DataFrame({
        "ID": [s["station_id"] for s in stations],
        "대여소": [s["station_name"] for s in stations],
        "지역": [s["station_region"] for s in stations],
        "주소": [s["station_address"] for s in stations],
        "연락처": [s["station_contactnumber"] or "-" for s in stations],
        "총 거치대": [s["station_totaldocks"] for s in stations],
        "거치 자전거": [int(s["docked_count"]) for s in stations],
        "대여가능": [int(s["available_count"] or 0) for s in stations],
        "정비중": [int(s["maintenance_count"] or 0) for s in stations],
        "운영 상태": [ui.STATION_STATUS_LABELS[s["station_status"]] for s in stations],
    }), hide_index=True, width="stretch")
    st.write("")

    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(key="ppcard_station_new"):
        ui.card_title("대여소 등록", "* 표시는 필수 입력입니다.")
        data = _station_form("new", None)
        if data:
            try:
                sid = admin_ops.create_station(data)
            except BusinessError as e:
                st.error(str(e))
            else:
                st.session_state["station_msg"] = f"대여소를 등록했습니다 (ID {sid})."
                st.rerun()
    with c2, st.container(key="ppcard_station_edit"):
        ui.card_title("대여소 수정 · 운영 상태 변경", "수정할 대여소를 고른 뒤 값을 바꾸고 저장하세요.")
        by_id = {s["station_id"]: s for s in stations}
        sid = st.selectbox("수정할 대여소", list(by_id),
                           format_func=lambda i: f"{by_id[i]['station_name']} (ID {i})")
        if sid is not None:
            data = _station_form(f"edit_{sid}", by_id[sid])
            if data:
                try:
                    admin_ops.update_station(sid, data)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    st.session_state["station_msg"] = f"대여소 ID {sid} 정보를 저장했습니다."
                    st.rerun()


def _bicycles_tab() -> None:
    _flash("bike_msg")
    stations = admin_ops.all_stations()
    st_names = {s["station_id"]: s["station_name"] for s in stations}

    f1, f2 = st.columns(2)
    f_station = f1.selectbox("대여소 필터", [None, *st_names],
                             format_func=lambda i: "전체" if i is None else st_names[i])
    f_status = f2.selectbox("상태 필터", [None, "AVAILABLE", "RENTED", "MAINTENANCE"],
                            format_func=lambda c: "전체" if c is None else ui.label(c))
    bikes = admin_ops.all_bicycles(f_station, f_status)
    st.dataframe(pd.DataFrame({
        "자전거": [f"#{b['bicycle_id']}" for b in bikes],
        "상태": [ui.label(b["bicycle_status"]) for b in bikes],
        "현재 대여소": [b["station_name"] or "- (대여 중)" for b in bikes],
        "등록일": [ui.dt(b["bicycle_registered_at"]) for b in bikes],
    }), hide_index=True, width="stretch", height=320)
    st.write("")

    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(key="ppcard_bike_new"):
        ui.card_title("자전거 등록", "새 자전거를 대여소에 배치합니다.")
        with st.form("new_bike_form", border=False):
            station_id = st.selectbox("배치할 대여소", list(st_names), format_func=st_names.get)
            status = st.selectbox("상태", BIKE_STATUSES, format_func=ui.label)
            if st.form_submit_button("등록", type="primary", width="stretch"):
                try:
                    bid = admin_ops.register_bicycle(station_id, status)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    st.session_state["bike_msg"] = f"자전거 #{bid}를 등록했습니다."
                    st.rerun()
    with c2, st.container(key="ppcard_bike_status"):
        ui.card_title("자전거 상태 변경", "대여가능 ↔ 정비중 (대여 중인 자전거는 제외)")
        changeable = [b for b in admin_ops.all_bicycles() if b["bicycle_status"] != "RENTED"]
        by_id = {b["bicycle_id"]: b for b in changeable}
        with st.form("bike_status_form", border=False):
            bid = st.selectbox(
                "자전거", list(by_id),
                format_func=lambda i: f"#{i} · {ui.label(by_id[i]['bicycle_status'])} · {by_id[i]['station_name']}",
            )
            new_status = st.selectbox("변경할 상태", BIKE_STATUSES, format_func=ui.label)
            if st.form_submit_button("변경", type="primary", width="stretch"):
                try:
                    admin_ops.change_bicycle_status(bid, new_status)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    st.session_state["bike_msg"] = f"자전거 #{bid} 상태를 {ui.label(new_status)}(으)로 바꿨습니다."
                    st.rerun()


def render() -> None:
    ui.page_header("관리자", "대여소·자전거 관리", "대여소와 자전거를 등록·수정하고 운영 상태를 바꿉니다.")
    stations = admin_ops.all_stations()
    bikes = admin_ops.all_bicycles()
    count = lambda code: sum(b["bicycle_status"] == code for b in bikes)
    ui.stat_cards([
        ("운영 중 대여소", f"{sum(s['station_status'] == 'ACTIVE' for s in stations)}", f"/ {len(stations)}곳", True),
        ("대여가능 자전거", f"{count('AVAILABLE')}", "대", False),
        ("대여 중", f"{count('RENTED')}", "대", False),
        ("정비 중", f"{count('MAINTENANCE')}", "대", False),
    ])
    t1, t2 = st.tabs(["대여소", "자전거"])
    with t1:
        _stations_tab()
    with t2:
        _bicycles_tab()
