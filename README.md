# Pedal Point

탄소 마일리지 기반 공공자전거 서비스 — 데이터베이스 과제 5조

공공자전거로 이동한 거리만큼 줄어든 탄소량을 계산해 마일리지로 적립하고, 다음 이용요금 결제 때 할인으로 사용한다.

## 구성

| 구분 | 내용 |
|---|---|
| DBMS | MySQL 8.0 (8.0.16 이상, CHECK 제약 사용) |
| GUI | Python + Streamlit |
| DB 연결 | pymysql |

```
db/schema.sql        padal DB 생성 (테이블 7개, FK 10개, 뷰 1개, CHECK 제약)
db/sample_data.sql   샘플 데이터 (대여소 7, 자전거 30, 이용자 8, 관리자 3, 대여 19)
app/main.py          진입점 (로그인 → 이용자/관리자 화면)
app/rules.py         요금·마일리지 기준값과 계산식
app/user_ops.py      이용자 기능 SQL (대여·반납·결제는 트랜잭션)
app/admin_ops.py     관리자 기능 SQL
app/views/           화면 7개
.streamlit/          테마(발표자료 표지 디자인 기반)와 DB 접속 설정
```

## 실행 방법

1. DB 만들기 — **`schema.sql`은 기존 padal DB를 삭제하고 새로 만든다.**
   ```
   mysql -u root -p < db/schema.sql
   mysql -u root -p < db/sample_data.sql
   ```
2. 패키지 설치
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사해 MySQL 접속 정보 입력
4. 프로젝트 루트에서 실행
   ```
   streamlit run app/main.py
   ```

## 화면

| 화면 | 사용자 | 기능 |
|---|---|---|
| 로그인 | 공통 | 이용자/관리자 선택 후 ID를 골라 진입 (비밀번호 없음) |
| 대여소 검색·대여 | 이용자 | 지역·이름으로 대여소 검색, 대여 가능 자전거 선택 후 대여 |
| 반납·결제 | 이용자 | 반납 대여소·이동거리 입력, 마일리지 적립, 사용량 선택 후 결제 |
| 마이페이지 | 이용자 | 대여·결제 내역, 마일리지 잔액·내역, 누적 탄소 절감량 |
| 대여소·자전거 관리 | 관리자 | 등록·수정, 운영 상태·자전거 상태 변경 |
| 내역 조회 | 관리자 | 대여·결제·마일리지 내역 검색 (기간·사용자·대여소별) |
| 회원 관리·통계 | 관리자 | 회원 상태 변경, 탄소 절감·마일리지 통계 |

## 업무 규칙

- 탄소 절감량(g) = 이동거리(km) × 210, 적립 포인트 = 탄소 절감량 ÷ 10 (버림). 0P면 적립 기록 없음
- 요금: 60분 1,000원, 초과 5분마다 200원 (5분 미만도 5분)
- 할인: 1P = 1원, 이용금액의 50%와 보유 마일리지 중 작은 값까지
- 반납·적립·결제·사용은 하나의 트랜잭션으로 처리하고, 자전거·이용자 행을 `SELECT … FOR UPDATE`로 잠가 동시 대여와 잔액 초과 사용을 막는다
- 이번 반납으로 적립된 포인트는 다음 결제부터 사용한다
