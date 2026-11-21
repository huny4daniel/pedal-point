"""관리자 · 대여소·자전거 관리: 등록·수정, 상태 변경."""
import pandas as pd
import streamlit as st

import admin_ops
import ui
from db import BusinessError
from station_map import load_coords, markers_for, save_coord, station_map

STATION_STATUSES = ["ACTIVE", "INACTIVE"]
BIKE_STATUSES = ["AVAILABLE", "MAINTENANCE"]


def _flash(key: str) -> None:
    ui.flash(key)


def _station_form(prefix: str, s: dict | None) -> dict | None:
    """등록·수정 공용 입력 폼. 제출되면 입력값 dict, 아니면 None."""
    s = s or {}
    with st.form(f"{prefix}_station_form", clear_on_submit=s == {}, border=False):
        name = st.text_input("대여소 이름 *", s.get("station_name", ""), max_chars=100)
        address = st.text_input("주소 *", s.get("station_address", ""), max_chars=255)
        c1, c2, c3 = st.columns(3)
        contact = c1.text_input("연락처", s.get("station_contactnumber") or "", max_chars=20)
        docks = c2.number_input("거치대 수 *", min_value=1, value=int(s.get("station_totaldocks", 10)), step=1)
        status = c3.selectbox(
            "운영 상태", STATION_STATUSES,
            index=STATION_STATUSES.index(s.get("station_status", "ACTIVE")),
            format_func=ui.STATION_STATUS_LABELS.get,
        )
        if s:
            st.caption(f"현재 보관 중인 자전거 {int(s['docked_count'])}대 · 거치대 수는 이보다 적게 설정할 수 없습니다.")
        submitted = st.form_submit_button("저장" if s else "등록", type="primary", width="stretch")
    if not submitted:
        return None
    return {"name": name, "address": address, "contact": contact,
            "totaldocks": int(docks), "status": status}


def _pick_map(key: str, stations: list[dict], current: tuple | None, height: int = 300) -> tuple | None:
    """지도를 클릭해 위치를 고른다. 고른 좌표(session_state[key])를 돌려준다."""
    pick = st.session_state.get(key, current)
    markers, _ = markers_for(stations, "available_count", lambda s, c: "gray")
    ev = station_map(f"map_{key}", markers, None, height=height, mode="pick", pick=pick)
    if "pick" in ev and ev["pick"] != pick:
        st.session_state[key] = ev["pick"]
        st.rerun()
    if pick:
        st.caption(f"📍 선택한 위치 {pick[0]:.5f}, {pick[1]:.5f} · 지도를 다시 누르면 옮겨집니다.")
    else:
        st.caption("📍 지도에서 대여소 위치를 눌러 주세요.")
    return pick


def _stations_tab() -> None:
    _flash("station_msg")
    stations = admin_ops.all_stations()
    by_id = {s["station_id"]: s for s in stations}
    coords = load_coords()

    # 현황 지도: 핀 숫자 = 대여 가능 대수, 빨간 핀 = 운영 중지. 핀을 누르면 오른쪽에서 수정
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        markers, missing = markers_for(
            stations, "available_count",
            lambda s, c: "red" if s["station_status"] != "ACTIVE" else ("green" if c else "gray"),
        )
        sel = st.session_state.get("admin_station")
        if sel not in by_id and stations:
            sel = st.session_state["admin_station"] = stations[0]["station_id"]
        ev = station_map("admin_map", markers, sel, height=470)
        if "select" in ev and ev["select"] != sel:
            st.session_state["admin_station"] = ev["select"]
            st.rerun()
        st.markdown(
            '<div class="pp-legend"><span><i style="background:#12B76A"></i>대여 가능</span>'
            '<span><i style="background:#9AA6A0"></i>자전거 없음</span>'
            '<span><i style="background:#D92D20"></i>운영 중지</span>'
            + (f"<span>지도 위치 미지정 {len(missing)}곳</span>" if missing else "")
            + "</div>",
            unsafe_allow_html=True,
        )

    with right, st.container(key="ppcard_station_edit"):
        ui.card_title("대여소 수정 · 운영 상태 변경", "지도에서 핀을 누르거나 목록에서 고르세요.")
        ids = list(by_id)
        sel = st.session_state.get("admin_station")
        sid = st.selectbox("수정할 대여소", ids, index=ids.index(sel) if sel in by_id else 0,
                           format_func=lambda i: f"{by_id[i]['station_name']} (ID {i})"
                           + ("" if i in coords else " · 위치 미지정"))
        if sid != sel:
            st.session_state["admin_station"] = sid
        if sid is not None:
            if st.toggle("지도에서 위치 바꾸기", value=sid not in coords, key=f"move_{sid}"):
                _pick_map(f"pick_edit_{sid}", [s for s in stations if s["station_id"] != sid], coords.get(sid), 240)
            data = _station_form(f"edit_{sid}", by_id[sid])
            if data:
                try:
                    admin_ops.update_station(sid, data)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    if pick := st.session_state.pop(f"pick_edit_{sid}", None):
                        save_coord(sid, *pick)
                    st.session_state["station_msg"] = f"대여소 ID {sid} 정보를 저장했습니다."
                    st.rerun()

    st.write("")
    with st.container(key="ppcard_station_new"):
        ui.card_title("대여소 등록", "지도에서 위치를 누르고 정보를 입력하세요. * 표시는 필수입니다.")
        c1, c2 = st.columns([1.2, 1], gap="large")
        with c1:
            pick = _pick_map("pick_new", stations, None, 300)
        with c2:
            data = _station_form("new", None)
        if data:
            if not pick:
                st.error("지도에서 대여소 위치를 먼저 눌러 주세요.")
            else:
                try:
                    sid = admin_ops.create_station(data)
                except BusinessError as e:
                    st.error(str(e))
                else:
                    save_coord(sid, *pick)
                    st.session_state.pop("pick_new", None)
                    st.session_state["admin_station"] = sid
                    st.session_state["station_msg"] = f"대여소를 등록했습니다 (ID {sid})."
                    st.rerun()

    st.write("")
    st.dataframe(pd.DataFrame({
        "ID": [s["station_id"] for s in stations],
        "대여소": [s["station_name"] for s in stations],
        "주소": [s["station_address"] for s in stations],
        "연락처": [s["station_contactnumber"] or "-" for s in stations],
        "거치대": [s["station_totaldocks"] for s in stations],
        "보관 중": [int(s["docked_count"]) for s in stations],
        "대여가능": [int(s["available_count"]) for s in stations],
        "정비중": [int(s["maintenance_count"]) for s in stations],
        "운영 상태": [ui.STATION_STATUS_LABELS[s["station_status"]] for s in stations],
        "지도 위치": ["등록" if s["station_id"] in coords else "미지정" for s in stations],
    }), hide_index=True, width="stretch")


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
        "현재 대여소": [b["station_name"] or "대여 중" for b in bikes],
        "등록일": [ui.dt(b["bicycle_registered_at"]) for b in bikes],
    }), hide_index=True, width="stretch", height=320)
    st.write("")

    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(key="ppcard_bike_new"):
        ui.card_title("자전거 등록", "새 자전거를 대여소에 배치합니다. 빈 거치대가 있어야 합니다.")
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
    stations = admin_ops.all_stations()
    bikes = admin_ops.all_bicycles()
    count = lambda code: sum(b["bicycle_status"] == code for b in bikes)
    ui.page_header("관리자", "대여소·자전거 관리", "대여소와 자전거를 등록·수정하고 운영 상태를 바꿉니다.", stats=[
        ("운영 중 대여소", f"{sum(s['station_status'] == 'ACTIVE' for s in stations)} / {len(stations)}곳"),
        ("대여가능", f"{count('AVAILABLE')}대"), ("대여 중", f"{count('RENTED')}대"),
        ("정비 중", f"{count('MAINTENANCE')}대"),
    ])
    t1, t2 = st.tabs(["대여소", "자전거"])
    with t1:
        _stations_tab()
    with t2:
        _bicycles_tab()
