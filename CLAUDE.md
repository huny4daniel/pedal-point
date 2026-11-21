# Pedal Point — 작업 지침

탄소 마일리지 공공자전거 서비스 (DB 과제). Streamlit + pymysql, DB 이름 `pedal`. 사용법과 화면 설명은 README.md.

## 바꾸면 안 되는 것

- `sql/GreenRide_DDL.sql`, `sql/GreenRide_DML.sql`은 팀 확정본이다. 구조·데이터를 고치지 말고 코드를 맞춘다
  (심각한 문제가 있으면 먼저 사용자에게 묻는다). ERD는 `docs/ERD.mwb`
- 요금·적립·할인 규칙은 DML 데이터 기준이다 (`app/rules.py`). `docs/`의 가이드 PDF 6장 규칙(5분 200원, 1km 21P,
  50% 한도)은 참고용이고 따르지 않는다
- DB에 없는 값(대여소 좌표 등)은 DB 밖에 둔다: 좌표는 `app/station_coords.json`

## 코드 규칙

- SQL은 모두 `%s` 파라미터 바인딩, 테이블 `user`는 항상 백틱. SQL은 `user_ops.py`·`admin_ops.py`에만 둔다
- 여러 테이블을 바꾸는 작업은 `db.transaction()` 한 블록에서, 경합하는 행은 `SELECT … FOR UPDATE`
- 업무 규칙 위반은 `BusinessError("안내 문구")`, 화면은 `st.error`로 보여준다. pymysql 오류는 `db.py`가
  `DBError`(BusinessError 하위, `errno` 보존)로 바꾼다 — 중복 키는 `e.errno == 1062`로 판단
- 대여 상태 = `rental_end_time` NULL 여부, 결제 대기 = 반납됐지만 payment 없음, 적립 = mileage,
  사용 = `payment_discount > 0`, 보유 마일리지 `user.user_mileage`는 결제 트랜잭션에서 함께 갱신
- 화면 문구·주석은 한국어. DB 값을 HTML에 넣을 때는 `ui.esc()`

## 화면 구조

- `main.py`가 역할(`st.session_state["role"]`)과 화면 모드로 메뉴를 만든다. 다른 메뉴로 이동은 `ui.go("ride")`처럼
  `PAGE_KEYS`의 이름을 쓴다 (기본 페이지는 url_path가 비어 있음)
- 이용자 메뉴: 홈(`user_home`) / 대여·반납(`user_rent.render`가 상황별로 대여 화면·`user_return`의 반납·결제 화면을 고름) / 마이페이지
- 모바일 화면: `ui.sync_viewport()`의 JS 컴포넌트가 창 비율(세로가 길거나 폭 640px 이하)을 알려주고 `ui.is_mobile()`로
  분기한다. 관리자는 항상 PC 화면. 모바일 전용 스타일은 `ui.MOBILE_CSS`
- 테마: `config.toml`의 `[theme.light]`/`[theme.dark]`. `ui.theme_toggle()`이 localStorage에 테마를 쓰고 새로고침하며,
  일회용 토큰으로 로그인을 복원한다. 우리 CSS는 `--pp-*` 변수를 쓰고 다크는 `ui.DARK_CSS`가 변수를 덮어쓴다
- 카드는 key가 `ppcard_`로 시작하는 `st.container`. 머리말은 `ui.page_header(…, stats=[…])` 배너
- 지도는 `station_map.station_map()` (components v2 + Leaflet). 마커 클릭은 `{"select": id}`, pick 모드는 `{"pick": (lat, lng)}`

## 확인 방법

- DB 초기화: `.venv\Scripts\python.exe init_db.py --reset` (테스트로 데이터를 바꿨으면 끝나고 되돌린다)
- 화면 렌더링: `streamlit.testing.v1.AppTest`로 `views.<화면>.render()`를 session_state(`role`, `user_id`/`staff_id`,
  `viewport_mobile`)와 함께 실행해 예외가 없는지 본다. 지도 클릭은 AppTest로 못 하므로 session_state
  (`rent_station`, `return_station`)를 직접 넣는다
- 실행 중인 서버는 코드 변경을 자동으로 다시 읽지 않는다 (`runOnSave = false`) → 서버 재시작 후 확인
- `run.bat`은 CRLF여야 한다 (`.gitattributes`로 고정). Git Bash `sed -i`로 고치지 않는다
