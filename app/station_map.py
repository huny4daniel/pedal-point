"""대여소 지도: 좌표 파일 관리와 Leaflet(OpenStreetMap) 지도 컴포넌트.

DB(station)에는 위도·경도가 없으므로 좌표는 app/station_coords.json에 station_id별로 둔다.
시연 데이터 20곳은 대여소 이름 기준의 대략적인 실제 위치이고, 관리자가 지도에서 지정·수정한다.
"""
import json
import threading
from pathlib import Path

import streamlit as st

COORDS_FILE = Path(__file__).parent / "station_coords.json"
DEFAULT_CENTER = [37.38, 126.77]  # 시흥시
_lock = threading.Lock()


# ---------------------------------------------------------------- 좌표 파일
def load_coords() -> dict[int, tuple[float, float]]:
    try:
        raw = json.loads(COORDS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {int(k): (float(v[0]), float(v[1])) for k, v in raw.items()}


def save_coord(station_id: int, lat: float, lng: float) -> None:
    with _lock:
        coords = load_coords()
        coords[int(station_id)] = (round(lat, 6), round(lng, 6))
        lines = [f'  "{k}": [{v[0]}, {v[1]}]' for k, v in sorted(coords.items())]  # 대여소 하나당 한 줄
        COORDS_FILE.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


# ---------------------------------------------------------------- 지도 컴포넌트
_JS = r"""
const LEAFLET = "https://unpkg.com/leaflet@1.9.4/dist/leaflet";

function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (!window.__ppLeaflet) {
    window.__ppLeaflet = new Promise((resolve, reject) => {
      const css = document.createElement("link");
      css.rel = "stylesheet"; css.href = LEAFLET + ".css";
      document.head.appendChild(css);
      const js = document.createElement("script");
      js.src = LEAFLET + ".js";
      js.onload = () => resolve(window.L);
      js.onerror = reject;
      document.head.appendChild(js);
    });
  }
  return window.__ppLeaflet;
}

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function pinIcon(L, m, selected) {
  const label = selected ? `<div class="pp-pin-label">${esc(m.name)}</div>` : "";
  return L.divIcon({
    className: "pp-pin-wrap",
    html: `<div class="pp-pin ${esc(m.tone)}${selected ? " sel" : ""}"><b>${esc(m.count)}</b></div>${label}`,
    iconSize: [0, 0],
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  let root = parentElement.querySelector(".pp-map");
  if (!root) {
    root = document.createElement("div");
    root.className = "pp-map";
    parentElement.appendChild(root);
  }
  // height 0 = 화면 아래까지 남은 세로 공간을 채운다
  const sizeRoot = () => {
    if (root.__ppData.height) { root.style.height = root.__ppData.height + "px"; return; }
    const top = root.getBoundingClientRect().top + window.scrollY;
    root.style.height = Math.max(420, window.innerHeight - top - 64) + "px";
  };
  if (!root.__ppSized) {
    root.__ppSized = true;
    window.addEventListener("resize", () => { if (root.isConnected) sizeRoot(); });
  }
  root.__ppData = data;
  root.__ppSet = setTriggerValue;
  sizeRoot();  // 클릭 핸들러는 항상 최신 함수를 쓴다

  loadLeaflet().then((L) => {
    let s = root.__pp;
    if (!s) {
      const map = L.map(root, { zoomControl: true, scrollWheelZoom: true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: "&copy; OpenStreetMap",
      }).addTo(map);
      s = root.__pp = { map, layer: L.layerGroup().addTo(map), fitted: false, lastSel: null, pick: null,
                        autoFit: true, fitting: false };
      map.on("click", (e) => {
        if (root.__ppData.mode === "pick") root.__ppSet("pick", { lat: e.latlng.lat, lng: e.latlng.lng });
      });
      // 사용자가 직접 움직이기 전까지는 지도 크기가 바뀔 때마다 전체 범위를 다시 맞춘다
      map.on("dragstart", () => { s.autoFit = false; });
      map.on("zoomstart", () => { if (!s.fitting) s.autoFit = false; });
      new ResizeObserver(() => {
        map.invalidateSize();
        if (s.autoFit && s.fitAll && root.__ppData.selected == null && !root.__ppData.pick) s.fitAll();
      }).observe(root);
    }
    const d = root.__ppData;

    s.layer.clearLayers();
    for (const m of d.markers) {
      const selected = m.id === d.selected;
      const mk = L.marker([m.lat, m.lng], { icon: pinIcon(L, m, selected), zIndexOffset: selected ? 1000 : 0 });
      if (!selected) mk.bindTooltip(esc(m.name), { direction: "top", offset: [0, -40] });
      if (d.mode !== "pick") mk.on("click", () => root.__ppSet("select", m.id));
      mk.addTo(s.layer);
    }
    if (d.pick) {
      L.marker([d.pick.lat, d.pick.lng], {
        icon: L.divIcon({ className: "pp-pin-wrap", html: '<div class="pp-pin pick"><b>+</b></div>', iconSize: [0, 0] }),
        zIndexOffset: 2000,
      }).addTo(s.layer);
    }

    s.fitAll = () => {
      const pts = root.__ppData.markers.map((m) => [m.lat, m.lng]);
      s.fitting = true;
      s.map.invalidateSize();
      if (pts.length > 1) s.map.fitBounds(pts, { padding: [40, 40], maxZoom: 15, animate: false });
      else if (pts.length === 1) s.map.setView(pts[0], 15, { animate: false });
      else s.map.setView(root.__ppData.center, 13, { animate: false });
      s.fitting = false;
    };
    const sel = d.markers.find((m) => m.id === d.selected) || (d.pick && { lat: d.pick.lat, lng: d.pick.lng });
    const selKey = d.selected ?? (d.pick ? `${d.pick.lat},${d.pick.lng}` : null);
    if (sel && selKey !== s.lastSel) {
      // 줌은 유지하되 너무 멀리 있으면 동네가 보이는 정도(14)까지만 당긴다
      s.map.setView([sel.lat, sel.lng], Math.max(s.map.getZoom() || 0, 14), { animate: s.fitted });
    } else if (!s.fitted) {
      s.fitting = true;
      s.map.setView(d.center, 13, { animate: false });
      s.fitting = false;
      setTimeout(() => s.fitAll(), 120);  // 크기가 잡힌 뒤에 범위를 맞춘다 (먼저 맞추면 너무 멀리 축소됨)
    }
    s.fitted = true;
    s.lastSel = selKey;
    setTimeout(() => s.map.invalidateSize(), 60);
  });
}
"""

_component = st.components.v2.component("pp_station_map", js=_JS, isolate_styles=False)


def station_map(key: str, markers: list[dict], selected: int | None = None, *, height: int = 0,
                mode: str = "select", pick: tuple[float, float] | None = None) -> dict:
    """대여소 지도를 그리고 이번 실행에서 일어난 클릭을 돌려준다.

    markers: [{"id", "name", "lat", "lng", "count", "tone"}]  tone: green / gray / blue / red
    height: 픽셀 높이. 0이면 브라우저 창 아래까지 남은 공간을 채운다
    mode: "select" (마커 클릭 → {"select": id}) 또는 "pick" (지도 클릭 → {"pick": (lat, lng)})
    """
    data = {
        "markers": markers, "selected": selected, "height": height, "mode": mode,
        "center": DEFAULT_CENTER,
        "pick": {"lat": pick[0], "lng": pick[1]} if pick else None,
    }
    res = _component(key=key, data=data, on_select_change=lambda: None, on_pick_change=lambda: None)
    out = {}
    if getattr(res, "select", None) is not None:
        out["select"] = int(res.select)
    p = getattr(res, "pick", None)
    if p:
        out["pick"] = (float(p["lat"]), float(p["lng"]))
    return out


def markers_for(stations: list[dict], count_key: str, tone_fn) -> tuple[list[dict], list[dict]]:
    """대여소 행 → 지도 마커. 좌표가 없는 대여소는 두 번째 목록으로 돌려준다."""
    coords = load_coords()
    markers, missing = [], []
    for s in stations:
        c = coords.get(s["station_id"])
        if c is None:
            missing.append(s)
            continue
        count = int(s[count_key])
        markers.append({"id": s["station_id"], "name": s["station_name"], "lat": c[0], "lng": c[1],
                        "count": count, "tone": tone_fn(s, count)})
    return markers, missing
