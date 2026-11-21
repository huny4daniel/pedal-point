"""이용자 · 대여·반납 (한 메뉴에서 상황에 따라 화면이 바뀐다).

- 결제 직후: 영수증
- 대여 중: 반납 화면 (views/user_return.render_return)
- 결제 대기 건을 결제하는 중: 결제 화면 (render_pending)
- 그 밖: 대여 화면 — 검색 → 지도 핀(대여 가능 대수) → 대여소 정보 카드 → 자전거 선택 → 대여하기
  결제하지 않은 대여가 있으면 위에 안내 카드
"""
import streamlit as st

import rules
import ui
import user_ops
from db import BusinessError
from station_map import markers_for, station_map
from views import user_return

SEL_KEY = "rent_station"


def _tone(_s: dict, count: int) -> str:
    return "green" if count > 0 else "gray"


def _sheet(user_id: int, s: dict | None, blocked: str | None, stations: list[dict]) -> None:
    """지도에서 고른 대여소의 정보 카드. 아직 안 골랐으면 빌리기 좋은 대여소 목록."""
    with st.container(key="ppcard_sheet"):
        if s is None:
            ui.card_title("지금 빌리기 좋은 대여소", "지도에서 핀을 누르거나 아래에서 바로 골라 보세요.")
            top = sorted(stations, key=lambda x: -int(x["available_count"]))[:6]
            for t in top:
                n = int(t["available_count"])
                if st.button(f"{t['station_name']} · {n}대", key=f"top_{t['station_id']}", width="stretch",
                             icon=":material/pedal_bike:" if n else ":material/block:", disabled=n == 0):
                    st.session_state[SEL_KEY] = t["station_id"]
                    st.rerun()
            st.markdown(
                f'<div class="pp-fee" style="margin-top:.8rem"><span>기본 {rules.BASE_MINUTES}분 {ui.won(rules.BASE_FEE)}</span>'
                f'<span>초과 {rules.EXTRA_UNIT_MINUTES}분마다 {ui.won(rules.EXTRA_UNIT_FEE)}</span>'
                f'<span>1km 이동 = {rules.POINTS_PER_KM}P 적립</span></div>',
                unsafe_allow_html=True,
            )
            return

        avail, docks = int(s["available_count"]), int(s["station_totaldocks"])
        state = ui.badge("AVAILABLE", "대여 가능") if avail else ui.badge("INACTIVE", "자전거 없음")
        contact = f" · {ui.esc(s['station_contactnumber'])}" if s["station_contactnumber"] else ""
        st.markdown(
            f'<div class="pp-station-top"><div class="pp-sheet-name">{ui.esc(s["station_name"])}</div>{state}</div>'
            f'<div class="pp-sheet-addr">{ui.esc(s["station_address"])}{contact}</div>'
            f'<div class="pp-sheet-nums">'
            f'<div class="pp-sheet-num{" on" if avail else ""}"><b>{avail}</b><span>대여 가능</span></div>'
            f'<div class="pp-sheet-num"><b>{docks}</b><span>거치대</span></div>'
            f'<div class="pp-sheet-num"><b>{ui.won(rules.BASE_FEE)}</b><span>기본 {rules.BASE_MINUTES}분</span></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        if not avail:
            st.caption("지금 빌릴 수 있는 자전거가 없어요. 지도에서 초록색 핀을 골라 보세요.")
            return
        if blocked:
            st.error(blocked)
            return

        bikes = user_ops.available_bicycles(s["station_id"])
        bike_id = st.pills(
            "자전거 선택", [b["bicycle_id"] for b in bikes], format_func=lambda b: f"#{b}",
            default=bikes[0]["bicycle_id"], key=f"bike_pick_{s['station_id']}",
        )
        st.caption(f"초과 {rules.EXTRA_UNIT_MINUTES}분마다 {ui.won(rules.EXTRA_UNIT_FEE)} · "
                   f"반납할 때 1km당 {rules.POINTS_PER_KM}P가 적립돼요.")
        if st.button(f"자전거 #{bike_id} 대여하기" if bike_id else "자전거를 선택하세요", type="primary",
                     width="stretch", disabled=bike_id is None, icon=":material/pedal_bike:", key="rent_go"):
            try:
                rental_id = user_ops.rent_bicycle(user_id, s["station_id"], bike_id)
            except BusinessError as e:
                st.error(str(e))
            else:
                st.session_state["rent_done"] = f"자전거 #{bike_id} 대여를 시작했어요 · 대여번호 {rental_id}"
                st.session_state.pop(SEL_KEY, None)
                st.rerun()


def render() -> None:
    user_id = st.session_state["user_id"]
    if receipt := st.session_state.pop("return_receipt", None):
        ui.page_header("이용 완료", "반납·결제 완료")
        user_return.show_receipt(receipt)
        return

    ongoing = user_ops.ongoing_rentals(user_id)
    if ongoing:  # 1인 1대라 대여 중이면 반납 화면
        user_return.render_return(user_id, ongoing[0], st.session_state.pop("rent_done", None))
        return

    pending = user_ops.pending_rentals(user_id)
    paying = {r["rental_id"]: r for r in pending}.get(st.session_state.get(user_return.PAY_KEY))
    if paying:
        user_return.render_pending(user_id, paying)
        return
    st.session_state.pop(user_return.PAY_KEY, None)
    _rent_view(user_id, pending)


def _rent_view(user_id: int, pending: list[dict]) -> None:
    mobile = ui.is_mobile()
    me = user_ops.get_user(user_id)
    all_active = user_ops.search_stations("")
    ui.page_header(
        f"{ui.esc(me['user_name'])}님, 오늘도 가볍게 출발해요", "자전거 대여",
        "" if mobile else "지도에서 대여소를 누르고 바로 자전거를 빌려 보세요.",
        stats=[("보유 마일리지", ui.pt(me["user_mileage"])),
               ("대여 가능 자전거", f"{sum(int(x['available_count']) for x in all_active)}대"),
               ("운영 대여소", f"{len(all_active)}곳")],
    )
    if pending:
        user_return.pending_banner(pending)

    blocked = None
    if me["user_status"] != "ACTIVE":
        blocked = "이용이 정지된 회원입니다."
        st.warning(blocked + " 관리자에게 문의해 주세요.", icon=":material/block:")
    keyword = st.text_input("대여소 검색", placeholder="대여소 이름이나 주소 검색 (예: 정왕, 배곧)",
                            icon=":material/search:", label_visibility="collapsed")
    stations = user_ops.search_stations(keyword)
    by_id = {s["station_id"]: s for s in stations}
    sel_id = st.session_state.get(SEL_KEY)
    if sel_id not in by_id:
        sel_id = None
    if keyword.strip() and len(stations) == 1:  # 검색 결과가 하나면 바로 선택
        sel_id = stations[0]["station_id"]

    markers, missing = markers_for(stations, "available_count", _tone)

    def map_block(height: int) -> None:
        nonlocal sel_id
        if not stations:
            with st.container(key="ppcard_nostation"):
                ui.empty("🔍", "검색 결과가 없어요", "다른 이름이나 주소로 검색해 보세요.")
            return
        ev = station_map("rent_map", markers, sel_id, height=height)
        if "select" in ev and ev["select"] != st.session_state.get(SEL_KEY):
            st.session_state[SEL_KEY] = ev["select"]
            st.rerun()
        st.markdown(
            f'<div class="pp-legend"><span><i style="background:#12B76A"></i>대여 가능</span>'
            f'<span><i style="background:#9AA6A0"></i>자전거 없음</span>'
            f"<span>운영 중 대여소 {len(stations)}곳</span></div>",
            unsafe_allow_html=True,
        )
        if missing:  # 좌표가 아직 없는 대여소는 버튼으로 고른다
            st.caption("지도 위치가 등록되지 않은 대여소")
            for s in missing:
                if st.button(s["station_name"], key=f"nomap_{s['station_id']}", icon=":material/location_off:"):
                    st.session_state[SEL_KEY] = s["station_id"]
                    st.rerun()

    if mobile:
        map_block(360)
        _sheet(user_id, by_id.get(sel_id), blocked, stations)
    else:
        left, right = st.columns([2.1, 1], gap="medium")
        with left:
            map_block(0)  # 창 아래까지 채움
        with right:
            _sheet(user_id, by_id.get(sel_id), blocked, stations)
