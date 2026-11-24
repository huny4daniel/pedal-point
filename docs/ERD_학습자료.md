# Pedal Point ERD 완전 숙지 자료

일반적인 DB 개념 설명이 아니라 **우리 pedal DB에만 해당하는 내용**이다.
기준: `sql/GreenRide_DDL.sql`(구조), `sql/GreenRide_DML.sql`(시연 데이터), `docs/ERD.png`(그림).

공부 순서: 0장 암기 → 1~3장 테이블·관계 → 4~5장 제약·상태 → 6장 기능별 행 변화 → 9장 문제 풀기.
9장 문제를 답을 가리고 전부 맞히면 숙지 완료.

---

## 0. 한 장 요약 (이것만은 외운다)

- **테이블 7개**: station, adminstaff, bicycle, user, rental, payment, mileage
- **FK 8개**: rental이 4개(user, bicycle, 출발 대여소, 반납 대여소), payment 1개, mileage 1개, adminstaff 1개, bicycle 1개
- **CHECK 9개**: station 1, user 1, rental 3, payment 3, mileage 1
- **UNIQUE 5개**: 관리자 아이디, 이용자 아이디, 이용자 연락처, payment의 대여번호, mileage의 대여번호
- **중심 테이블은 rental**. 이용자·자전거·대여소가 rental로 모이고, payment와 mileage는 rental에 1:0..1로 붙는다
- **station은 rental과 두 번 연결**된다 (start_station_id, return_station_id)
- **기본키는 전부 INT AUTO_INCREMENT 대리키**. 복합키·식별 관계 없음 → ERD 선은 전부 점선(비식별 관계)
- **상태는 컬럼이 아니라 데이터로 판단하는 것이 2개**: 대여 중(= rental_end_time NULL), 결제 대기(= 반납됐는데 payment 없음)
- **반정규화 1개**: user.user_mileage (보유 마일리지). 결제 트랜잭션에서 같이 갱신
- **삭제 대신 상태**: 회원은 ACTIVE/SUSPENDED/WITHDRAWN, 관리자는 staff_is_active 1/0, 대여소는 ACTIVE/INACTIVE

```
                 adminstaff ──(담당 0..1)──┐
                                            ▼
user ─1───N─ rental ─N───1─ station (출발, 필수)
               │    ─N───1─ station (반납, 반납 후에만)
               │    ─N───1─ bicycle ─N───0..1─ station (현재 위치)
               ├─1───0..1─ payment
               └─1───0..1─ mileage
```

---

## 1. 테이블 한눈에

| # | 테이블 | 뜻 | 한 행 = | 시연 데이터 | 부모(참조하는 쪽) |
|---|---|---|---|---|---|
| 1 | station | 대여소 | 대여소 1곳 | 20곳 (18·20번 INACTIVE) | 없음 (최상위) |
| 2 | adminstaff | 관리자 | 직원 1명 | 20명 (19·20번 퇴사) | station |
| 3 | bicycle | 자전거 | 자전거 1대 | 40대 (RENTED 3, MAINTENANCE 1) | station |
| 4 | `user` | 이용자 | 회원 1명 | 20명 (19 정지, 20 탈퇴) | 없음 (최상위) |
| 5 | rental | 대여 | 대여 1건 | 33건 (1~26 완료, 27~30 결제 대기, 31~33 대여 중) | user, bicycle, station×2 |
| 6 | payment | 결제 | 대여 1건의 결제 | 26건 (그중 마일리지 사용 9건) | rental |
| 7 | mileage | 마일리지 적립 | 대여 1건의 적립 | 26건 (대여 1~26) | rental |

생성 순서(DDL 순서)가 곧 의존 순서다: 부모가 먼저 있어야 자식의 FK를 걸 수 있다.
station → adminstaff → bicycle → user → rental → payment → mileage

`user`는 MySQL 예약어와 겹칠 수 있어 SQL에서 항상 백틱으로 감싼다.

---

## 2. 테이블별 상세

표기: PK 기본키, FK 외래키, UQ 유니크, NN NOT NULL, AI AUTO_INCREMENT

### 2-1. station (대여소)

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| station_id | INT | NN | AI | PK | 대여소 번호 |
| station_name | VARCHAR(100) | NN | | | 이름 (예: 시흥시청역) |
| station_address | VARCHAR(255) | NN | | | 주소 |
| station_contactnumber | VARCHAR(20) | **NULL 허용** | | | 연락처 (없을 수 있음) |
| station_totaldocks | INT | NN | | | 거치대 총 개수 |
| station_status | ENUM('ACTIVE','INACTIVE') | NN | 'ACTIVE' | | 운영 / 운영 중지 |

- CHECK `chk_station_docks`: station_totaldocks > 0
- **없는 것**: 위도·경도 → 지도 좌표는 `app/station_coords.json`에 station_id 기준으로 저장
- **없는 것**: 현재 자전거 수, 빈 거치대 수 → bicycle을 세서 계산 (2-3, 7장)
- 시연 데이터: 시흥시 20곳, 거치대 8/10/15개, 18번(시흥프리미엄아울렛)·20번(물왕저수지) INACTIVE
- INACTIVE 대여소: 대여 불가, 반납 불가. 관리자 지도에서 빨간 핀

### 2-2. adminstaff (관리자)

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| staff_id | INT | NN | AI | PK | 관리자 번호 |
| staff_login_id | VARCHAR(50) | NN | | UQ `uq_staff_login_id` | 로그인 아이디 |
| staff_password | VARCHAR(255) | NN | | | bcrypt 해시 (평문 아님, 60자 정도라 255로 여유) |
| staff_name | VARCHAR(50) | NN | | | 이름 |
| staff_phone | VARCHAR(20) | NN | | | 연락처 (**UNIQUE 아님**, 이용자와 다름) |
| staff_is_active | TINYINT | NN | 1 | | 1 재직 / 0 퇴사 |
| staff_station_id | INT | **NULL 허용** | | FK → station | 담당 대여소 |

- FK `fk_staff_station`: ON UPDATE CASCADE, **ON DELETE SET NULL** (대여소가 지워지면 담당 없음)
- 관리자 1명 = 담당 대여소 최대 1곳. 한 대여소에 여러 관리자는 가능 (station 1 : adminstaff N)
- 퇴사(0)는 로그인 불가. 행은 지우지 않는다
- 시연 데이터: admin01~admin18 → 대여소 1~18 담당, admin19·20 퇴사
- 담당 대여소는 관리자 "내역 조회"의 대여소 필터 기본값으로 쓰인다

### 2-3. bicycle (자전거)

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| bicycle_id | INT | NN | AI | PK | 자전거 번호 |
| bicycle_status | ENUM('AVAILABLE','RENTED','MAINTENANCE') | NN | 'AVAILABLE' | | 대여 가능 / 대여 중 / 정비 중 |
| bicycle_registered_at | DATETIME | NN | CURRENT_TIMESTAMP | | 등록 시각 |
| bicycle_station_id | INT | **NULL 허용** | | FK → station | **현재** 있는 대여소 |

- FK `fk_bicycle_station`: ON UPDATE CASCADE, **ON DELETE SET NULL**
- bicycle_station_id는 "소속"이 아니라 **현재 위치**다. 빌리면 NULL, 반납하면 반납 대여소로 바뀐다
- 상태와 위치의 정상 조합:

| bicycle_status | bicycle_station_id | 뜻 |
|---|---|---|
| AVAILABLE | 대여소 번호 | 거치대에 있고 빌릴 수 있음 |
| MAINTENANCE | 대여소 번호 | 거치대에 있지만 정비 중 (거치대는 차지함) |
| RENTED | NULL | 누군가 타고 있음 |

- 이 조합은 **DB 제약으로 강제되지 않는다** (CHECK 없음). 프로그램이 대여·반납 때 두 컬럼을 같이 바꾼다
- 관리자는 AVAILABLE ↔ MAINTENANCE만 바꿀 수 있고, RENTED인 자전거는 바꿀 수 없다
- 시연 데이터: 40대. 23·31·36번 RENTED(위치 NULL), 40번 MAINTENANCE(4번 대여소)

### 2-4. `user` (이용자)

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| user_id | INT | NN | AI | PK | 회원 번호 |
| user_login_id | VARCHAR(50) | NN | | UQ `uq_user_login_id` | 아이디 (앱 규칙: 영문·숫자 4~20자) |
| user_password | VARCHAR(255) | NN | | | bcrypt 해시 |
| user_name | VARCHAR(50) | NN | | | 이름 |
| user_phone | VARCHAR(20) | NN | | UQ `uq_user_phone` | 연락처 (앱 규칙: 010-0000-0000) |
| user_mileage | INT | NN | 0 | | **보유 마일리지 (반정규화)** |
| user_status | ENUM('ACTIVE','SUSPENDED','WITHDRAWN') | NN | 'ACTIVE' | | 정상 / 이용정지 / 탈퇴 |
| user_created_at | DATETIME | NN | CURRENT_TIMESTAMP | | 가입 시각 |

- CHECK `chk_user_mileage`: user_mileage >= 0 (마일리지 음수 불가)
- **user_mileage = 적립 합계(mileage) − 사용 합계(payment.payment_discount)** 가 항상 성립해야 한다
- 상태별: ACTIVE 모두 가능 / SUSPENDED 로그인은 되지만 대여 불가 / WITHDRAWN 로그인 불가
- 탈퇴해도 행이 남는다 → 연락처 UNIQUE 때문에 같은 번호로 재가입 불가 (한계)
- 시연 데이터 주요 계정 (비밀번호 모두 1234):

| 아이디 | user_id | 마일리지 | 상태 |
|---|---|---|---|
| hong1 | 1 | 208 | 대여 중(31번) + 결제 대기(29번) |
| kim2 | 2 | 0 | 이용 기록 없음 |
| lee3 | 3 | 465 | 대여 중·결제 대기 없음 → 시연용 |
| park4 | 4 | 0 | 대여 중(32번) + 결제 대기(28번) |
| kang7 | 7 | 767 | 대여 중(33번) |
| jang10 | 10 | 1660 | 마일리지 최다 |
| kwon16 | 16 | 573 | 결제 대기(27번) |
| ahn18 | 18 | 455 | 결제 대기(30번) |
| song19 | 19 | 0 | SUSPENDED |
| ryu20 | 20 | 0 | WITHDRAWN |

### 2-5. rental (대여) — 중심 테이블

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| rental_id | INT | NN | AI | PK | 대여 번호 |
| rental_start_time | DATETIME | NN | CURRENT_TIMESTAMP | | 대여 시각 |
| rental_end_time | DATETIME | **NULL 허용** | | | 반납 시각 (NULL = 대여 중) |
| rental_distance | DECIMAL(6,2) | **NULL 허용** | | | 이동거리 km (반납 때 입력) |
| rental_user_id | INT | NN | | FK → user | 누가 |
| rental_bicycle_id | INT | NN | | FK → bicycle | 어떤 자전거를 |
| start_station_id | INT | NN | | FK → station | 어디서 빌려 |
| return_station_id | INT | **NULL 허용** | | FK → station | 어디에 반납 (NULL = 대여 중) |

FK 4개:

| 제약 이름 | 컬럼 | 참조 | ON UPDATE | ON DELETE |
|---|---|---|---|---|
| fk_rental_user | rental_user_id | user | CASCADE | RESTRICT |
| fk_rental_bicycle | rental_bicycle_id | bicycle | CASCADE | RESTRICT |
| fk_rental_start_station | start_station_id | station | CASCADE | RESTRICT |
| fk_rental_return_station | return_station_id | station | **RESTRICT** | RESTRICT |

CHECK 3개:

| 제약 이름 | 조건 | 막는 것 |
|---|---|---|
| chk_rental_time | end_time IS NULL OR end_time >= start_time | 빌린 시각보다 먼저 반납 |
| chk_rental_distance | distance IS NULL OR distance >= 0 | 음수 거리 |
| chk_rental_return | (end, 반납소, 거리 **셋 다 NULL**) OR (**셋 다 NOT NULL**) | 반납 정보가 반만 채워진 상태 |

- chk_rental_return이 핵심: 반납 3종 세트(rental_end_time, return_station_id, rental_distance)는 **같이 비고 같이 채워진다**. 그래서 반납 UPDATE 한 문장에서 셋을 동시에 넣는다
- DECIMAL(6,2): 전체 6자리 중 소수 2자리 → DB상 최대 9999.99km. 앱은 0~99.99km로 더 좁게 제한
- 요금은 rental에 저장하지 않는다. 시작·종료 시각으로 계산해 payment에 저장
- ERD 그림의 rental→station 선이 두 개인 이유 = 출발·반납 FK 2개
- ON DELETE RESTRICT 4개 전부: 대여 이력이 있는 회원·자전거·대여소는 **삭제 불가**

### 2-6. payment (결제)

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| payment_id | INT | NN | AI | PK | 결제 번호 |
| payment_amount | INT | NN | | | 이용금액 (할인 전) |
| payment_discount | INT | NN | 0 | | 마일리지 할인액 = **사용한 포인트** (1P=1원) |
| payment_final_amount | INT | NN | | | 최종 결제액 |
| payment_method | ENUM('카드','계좌이체','간편결제') | NN | | | 결제수단 |
| payment_at | DATETIME | NN | CURRENT_TIMESTAMP | | 결제 시각 |
| payment_rental_id | INT | NN | | UQ + FK → rental | 어느 대여의 결제인지 |

- UNIQUE `uq_payment_rental`: 대여 1건에 결제 **최대 1건** (중복 결제 방지). 이 UNIQUE 덕분에 rental : payment = 1 : 0..1
- FK `fk_payment_rental`: ON UPDATE CASCADE, ON DELETE RESTRICT
- CHECK 3개:
  - `chk_payment_amount`: amount >= 0
  - `chk_payment_discount`: 0 <= discount <= amount (이용금액보다 많이 할인 불가)
  - `chk_payment_final`: final_amount = amount − discount (계산이 틀린 행은 저장 불가)
- **마일리지 사용 내역 = payment_discount > 0 인 payment 행**. 별도 사용 테이블 없음
- 시연 데이터: 26건(대여 1~26), 마일리지 사용 9건. 27~30번 대여는 payment가 없음 = 결제 대기

### 2-7. mileage (마일리지 적립)

| 컬럼 | 타입 | NULL | 기본값 | 키 | 의미 |
|---|---|---|---|---|---|
| mileage_id | INT | NN | AI | PK | 적립 번호 |
| mileage_point | INT | NN | | | 적립 포인트 (이동거리 × 100, 소수 버림) |
| mileage_created_at | DATETIME | NN | CURRENT_TIMESTAMP | | 적립 시각 |
| mileage_rental_id | INT | NN | | UQ + FK → rental | 어느 대여로 적립됐는지 |

- UNIQUE `uq_mileage_rental`: 대여 1건에 적립 최대 1건 → rental : mileage = 1 : 0..1
- FK `fk_mileage_rental`: ON UPDATE CASCADE, ON DELETE RESTRICT
- CHECK `chk_mileage_point`: point >= 0
- **mileage는 적립만 기록한다**. 이름이 mileage지만 사용 내역은 payment에 있다
- **user와 직접 연결되지 않는다**. 누구의 적립인지는 mileage → rental → user 로 따라가서 안다
- 적립 행은 **결제할 때** 생긴다 (반납 때가 아님). 그래서 결제 대기 대여(27~30)는 mileage도 없다
- 0P면 행을 만들지 않는다 (예: 이동거리 0.00km). 그래서 "적립 0..1"

---

## 3. 관계 8개 완전 정리

| # | 부모 (1) | 자식 (N) | FK 컬럼 | 자식 쪽 필수? | 카디널리티 | ON UPDATE | ON DELETE |
|---|---|---|---|---|---|---|---|
| 1 | station | adminstaff | staff_station_id | 선택 (NULL 가능) | 1 : 0..N | CASCADE | SET NULL |
| 2 | station | bicycle | bicycle_station_id | 선택 (대여 중 NULL) | 1 : 0..N | CASCADE | SET NULL |
| 3 | user | rental | rental_user_id | 필수 | 1 : 0..N | CASCADE | RESTRICT |
| 4 | bicycle | rental | rental_bicycle_id | 필수 | 1 : 0..N | CASCADE | RESTRICT |
| 5 | station | rental (출발) | start_station_id | 필수 | 1 : 0..N | CASCADE | RESTRICT |
| 6 | station | rental (반납) | return_station_id | 선택 (대여 중 NULL) | 1 : 0..N | **RESTRICT** | RESTRICT |
| 7 | rental | payment | payment_rental_id | 필수 + UNIQUE | 1 : 0..1 | CASCADE | RESTRICT |
| 8 | rental | mileage | mileage_rental_id | 필수 + UNIQUE | 1 : 0..1 | CASCADE | RESTRICT |

### 규칙으로 외우기

- **이력 테이블(rental, payment, mileage)이 참조하는 FK는 전부 ON DELETE RESTRICT** → 기록이 있는 부모는 못 지운다
- **"현재 소속"을 나타내는 FK 2개(관리자 담당, 자전거 위치)만 ON DELETE SET NULL** → 대여소가 없어지면 소속만 비운다
- **ON UPDATE는 반납 대여소 하나만 RESTRICT, 나머지 7개 CASCADE**. 기본키를 바꾸는 일이 없어 실제 동작 차이는 없음 (통일하지 않은 것은 약점으로 인정)
- **1:0..1 관계 2개는 FK + UNIQUE로 만든다** (payment, mileage). UNIQUE가 없으면 1:N이 된다

### ERD 그림(ERD.png) 읽는 법

- 모든 선이 **점선** = 비식별 관계 (자식의 PK에 부모 키가 들어가지 않음, 자식은 자기 AI 대리키를 가짐)
- `||` (막대 두 개) = 정확히 1, `|<` 또는 까마귀발 = 여러 개, `o` (동그라미) = 0 가능
- payment·mileage 쪽 끝의 `o|` = 0 또는 1 → 결제·적립이 아직 없을 수 있음
- 아이콘: 노란 열쇠 = PK, 빨간 마름모 = FK, 파란 마름모 = NOT NULL, 빈 마름모 = NULL 허용
  - 그래서 rental_end_time, rental_distance, return_station_id, staff_station_id, bicycle_station_id, station_contactnumber가 **빈 마름모**
- 주의: 그림에서 rental–station(반납) 선의 station 쪽도 `||`로 보이지만, 실제 return_station_id는 NULL 허용이다 (대여 중일 때). "rental 행 입장에서는 반납 후에만 값이 있다"로 설명

### 기억할 경로 (JOIN 방향)

- 누가 적립받았나: mileage → rental → `user`
- 누가 결제했나: payment → rental → `user`
- 대여소별 결제 합계: payment → rental → station (start_station_id 기준)
- 자전거가 지금 어디 있나: bicycle → station (bicycle_station_id)
- 지금 누가 타고 있나: rental WHERE rental_end_time IS NULL → bicycle, `user`

---

## 4. 제약조건 전체 목록 (외우기용)

### UNIQUE 5개

| 이름 | 테이블.컬럼 | 이유 |
|---|---|---|
| uq_staff_login_id | adminstaff.staff_login_id | 관리자 아이디 중복 방지 |
| uq_user_login_id | user.user_login_id | 이용자 아이디 중복 방지 |
| uq_user_phone | user.user_phone | 연락처 1개당 계정 1개 |
| uq_payment_rental | payment.payment_rental_id | 대여 1건 = 결제 최대 1건 (중복 결제 방지) |
| uq_mileage_rental | mileage.mileage_rental_id | 대여 1건 = 적립 최대 1건 (중복 적립 방지) |

### CHECK 9개

| # | 이름 | 조건 |
|---|---|---|
| 1 | chk_station_docks | station_totaldocks > 0 |
| 2 | chk_user_mileage | user_mileage >= 0 |
| 3 | chk_rental_time | end IS NULL OR end >= start |
| 4 | chk_rental_distance | distance IS NULL OR distance >= 0 |
| 5 | chk_rental_return | 반납 3종 세트 전부 NULL 또는 전부 NOT NULL |
| 6 | chk_payment_amount | amount >= 0 |
| 7 | chk_payment_discount | discount >= 0 AND discount <= amount |
| 8 | chk_payment_final | final_amount = amount − discount |
| 9 | chk_mileage_point | mileage_point >= 0 |

- MySQL은 **8.0.16부터** CHECK를 실제로 검사한다 (그 이전 버전은 문법만 받고 무시). 그래서 README의 요구 버전이 8.0.16 이상
- ENUM 컬럼 4개(station_status, bicycle_status, user_status, payment_method)도 허용 값 외에는 저장을 막는 일종의 도메인 제약

### DB가 못 막고 프로그램이 막는 규칙 (중요 — Q&A 단골)

| 규칙 | 왜 DB로 못 막나 | 프로그램에서 막는 방법 |
|---|---|---|
| 1인 1대 대여 | 다른 행(내 다른 대여)을 봐야 함 | user 행 FOR UPDATE 후 대여 중 건수 확인 |
| 빈 거치대가 있어야 반납 | bicycle 행 개수를 세야 함 | station 행 FOR UPDATE 후 COUNT |
| 대여 가능 자전거만 대여 | 상태 조합 검사 | bicycle 행 FOR UPDATE 후 상태·위치 확인 |
| 정지 회원 대여 불가 | 다른 테이블 값 | user_status 확인 |
| 운영 중 대여소만 대여·반납 | 다른 테이블 값 | station_status 확인 |
| 할인 ≤ 보유 마일리지 | 다른 테이블 값 | user 행 FOR UPDATE 후 한도 계산 |
| user_mileage = 적립 − 사용 | 여러 테이블 합계 | 결제·적립·잔액 갱신을 한 트랜잭션에서 |
| 자전거 상태와 위치의 조합 | (CHECK로 가능은 했지만 DDL에 없음) | 대여·반납 UPDATE에서 두 컬럼을 같이 변경 |

CHECK는 **한 행 안의 컬럼끼리만** 비교할 수 있다. 다른 행이나 다른 테이블을 봐야 하는 규칙은 트리거나 프로그램 몫이다.

---

## 5. 상태 판단표

### 대여 건의 상태 (상태 컬럼 없음, 데이터로 판단)

| 상태 | rental_end_time | return_station_id / distance | payment 행 | mileage 행 | 시연 데이터 |
|---|---|---|---|---|---|
| 대여 중 | NULL | NULL / NULL | 없음 | 없음 | 31~33 |
| 결제 대기 | 있음 | 있음 / 있음 | **없음** | 없음 | 27~30 |
| 완료 | 있음 | 있음 / 있음 | 있음 | 있음 (0P면 없음) | 1~26 |

```sql
-- 대여 중
SELECT * FROM rental WHERE rental_end_time IS NULL;
-- 결제 대기
SELECT r.* FROM rental r LEFT JOIN payment p ON p.payment_rental_id = r.rental_id
WHERE r.rental_end_time IS NOT NULL AND p.payment_id IS NULL;
```

### 그 밖의 상태 컬럼

| 테이블 | 컬럼 | 값 | 효과 |
|---|---|---|---|
| user | user_status | ACTIVE / SUSPENDED / WITHDRAWN | 정상 / 로그인 O 대여 X / 로그인 X |
| adminstaff | staff_is_active | 1 / 0 | 재직 / 로그인 X |
| station | station_status | ACTIVE / INACTIVE | 대여·반납 가능 / 불가 |
| bicycle | bicycle_status | AVAILABLE / RENTED / MAINTENANCE | 대여 가능 / 타는 중 / 정비 중 |

---

## 6. 기능별로 어떤 행이 바뀌나 (가장 중요)

시연 중 "지금 DB에서 무슨 일이 일어났나요?"에 바로 답할 수 있어야 한다.

### 회원가입
- `user` INSERT 1행 (비밀번호는 bcrypt 해시, mileage 0, status ACTIVE, created_at 현재)
- 아이디·연락처 중복 → UNIQUE 위반(오류 1062) → "이미 사용 중인 아이디 또는 연락처입니다."

### 대여 (트랜잭션 1개)
1. `user` 행 잠금(FOR UPDATE) → SUSPENDED면 중단
2. 이 회원의 대여 중 rental 있는지 확인 → 있으면 중단 (1인 1대)
3. `station` 상태 확인 → INACTIVE면 중단
4. `bicycle` 행 잠금 → AVAILABLE이고 그 대여소에 있는지 확인
5. **`bicycle` UPDATE**: status = RENTED, station_id = NULL
6. **`rental` INSERT**: start_time = NOW(), user, bicycle, start_station (반납 3종은 NULL)

→ 바뀌는 테이블 2개: bicycle(수정), rental(추가)

### 반납 + 결제 + 적립 (트랜잭션 1개)
1. `rental` 행 잠금 → 내 대여인지, 아직 반납 안 됐는지
2. 반납 `station` 행 잠금 → ACTIVE인지, (거치대 수 − 그 대여소 자전거 수) > 0 인지
3. **`rental` UPDATE**: end_time, distance, return_station_id 셋을 한 번에 (chk_rental_return)
4. **`bicycle` UPDATE**: status = AVAILABLE, station_id = 반납 대여소
5. 요금 계산 (60분 1,000원 + 초과 30분마다 500원, 30분 미만도 올림)
6. `user` 행 잠금 → 할인 한도 = min(이용금액, 보유 마일리지) 확인
7. **`payment` INSERT**: amount, discount(사용 포인트), final = amount − discount, method
8. **`mileage` INSERT**: 거리 × 100 (소수 버림), 0P면 생략
9. **`user` UPDATE**: user_mileage = user_mileage − 사용 + 적립

→ 바뀌는 테이블 5개: rental, bicycle, payment, mileage, user. 중간 실패 시 전부 롤백

예시 (lee3, 바로 반납, 3.2km, 465P 사용):

- payment: amount 1000, discount 465, final 535
- mileage: point 320
- user_mileage: 465 − 465 + 320 = 320
- 한도는 적립 전 잔액으로 계산 → 이번에 쌓인 320P는 다음 결제부터

### 결제 대기 건 결제
- 반납은 이미 되어 있으므로 rental·bicycle은 그대로
- payment INSERT, mileage INSERT, user UPDATE (위 7~9단계만)
- 이미 payment가 있으면 "이미 결제된 대여입니다." (UNIQUE로도 막힘)

### 회원 탈퇴
- 대여 중 rental 있으면 거부, 결제 대기 있으면 거부
- `user` UPDATE: user_status = WITHDRAWN (DELETE 아님 → rental 이력의 FK가 살아 있음)

### 관리자: 대여소 등록·수정
- `station` INSERT / UPDATE. 좌표는 DB가 아니라 station_coords.json
- 거치대 수를 현재 보관 중인 자전거 수보다 적게 바꾸는 것은 거부

### 관리자: 자전거 등록·상태 변경
- 등록: `bicycle` INSERT (AVAILABLE 또는 MAINTENANCE, 빈 거치대 있어야 함)
- 변경: `bicycle` UPDATE status (AVAILABLE ↔ MAINTENANCE만, RENTED는 변경 불가)

### 관리자: 회원 정보·상태 일괄 저장
- 여러 `user` UPDATE를 한 트랜잭션으로. 하나라도 규칙 위반이면 전부 롤백
- 대여 중인 회원은 SUSPENDED·WITHDRAWN으로 못 바꿈

---

## 7. 저장하지 않고 계산하는 값

| 값 | 계산 방법 |
|---|---|
| 대여소의 대여 가능 대수 | COUNT(bicycle) WHERE station_id = X AND status = 'AVAILABLE' |
| 대여소의 빈 거치대 수 | station_totaldocks − COUNT(bicycle) WHERE station_id = X (정비 중 포함) |
| 이용 요금 | rental 시작·종료 시각 → 프로그램이 계산해서 payment에 저장 |
| 탄소 절감량 | rental_distance × 210g (DB에 없음, 화면에서만) |
| 마일리지 사용 내역 | payment WHERE payment_discount > 0 |
| 대여 중 / 결제 대기 | 5장 표 |

반대로 **계산할 수 있는데 저장하는 값**은 user.user_mileage 하나뿐 (반정규화, 조회 속도 때문).

검증 쿼리 — 모든 회원의 잔액이 내역과 맞는지:

```sql
SELECT u.user_login_id, u.user_mileage,
       COALESCE(e.earned, 0) - COALESCE(s.spent, 0) AS calc
FROM `user` u
LEFT JOIN (SELECT r.rental_user_id uid, SUM(m.mileage_point) earned
           FROM mileage m JOIN rental r ON r.rental_id = m.mileage_rental_id
           GROUP BY r.rental_user_id) e ON e.uid = u.user_id
LEFT JOIN (SELECT r.rental_user_id uid, SUM(p.payment_discount) spent
           FROM payment p JOIN rental r ON r.rental_id = p.payment_rental_id
           GROUP BY r.rental_user_id) s ON s.uid = u.user_id
HAVING u.user_mileage <> calc;   -- 결과 0행이면 정상
```

---

## 8. 설계 의도 한 줄 답변 (왜 이렇게 했나)

| 질문 | 답 |
|---|---|
| 왜 대리키(AUTO_INCREMENT)? | 아이디·연락처는 바뀔 수 있음. 바뀌지 않는 번호로 FK를 잡아야 안전 |
| 왜 rental이 중심? | "누가·무엇을·어디서·어디로·얼마나"가 모두 대여 한 건에 모임 |
| 왜 payment를 rental과 분리? | 반납과 결제 시점이 다를 수 있음(결제 대기). 결제 정보가 없는 대여가 존재 |
| 왜 mileage를 rental과 분리? | 0P면 적립이 없고, 적립 내역만 따로 조회 |
| 왜 mileage가 user를 직접 안 가리키나? | rental에 이미 user가 있음. 중복 FK는 불일치 가능성만 만든다 |
| 왜 user_mileage를 따로 저장? | 매 화면마다 전체 내역 합산을 피하려고. 대신 트랜잭션으로 일관성 유지 |
| 왜 회원을 삭제 안 하나? | 대여·결제 이력이 FK RESTRICT로 묶여 있고, 이력은 남아야 함 |
| 왜 반납 3종을 CHECK로 묶었나? | 반납 시각만 있고 반납 대여소가 없는 등 반쪽 데이터를 DB가 원천 차단 |
| 왜 final_amount를 저장? | 계산 가능하지만 결제 당시 확정 금액을 기록으로 남기려고. CHECK로 계산 일치 보장 |
| 왜 ENUM? | 값이 몇 개로 정해진 상태·결제수단을 오타 없이 저장. 대신 값 추가 시 ALTER 필요 |
| 정규형은? | 3NF. 예외는 의도적인 user_mileage 하나 |

---

## 9. 자가 점검 문제 (답을 가리고 풀기)

### 기본 (구조)

1. 테이블 7개를 생성 순서대로 말하라.
2. FK는 몇 개이고, 그중 rental에 있는 것은?
3. CHECK 9개를 테이블별 개수로 말하라.
4. UNIQUE 5개를 모두 말하라.
5. NULL을 허용하는 컬럼 6개를 모두 말하라.
6. station과 rental 사이 선이 두 개인 이유는?
7. 관리자 연락처는 UNIQUE인가?
8. rental_distance의 타입과 DB상 최댓값은?
9. 결제수단 ENUM 값 3개는?
10. user_mileage의 기본값과 CHECK는?

### 관계·옵션

11. ON DELETE SET NULL인 FK 2개는? 왜 그 둘만?
12. ON UPDATE RESTRICT인 FK는?
13. rental : payment가 1:N이 아니라 1:0..1인 이유는?
14. mileage에서 이용자 이름을 얻으려면 어떤 JOIN 경로?
15. 대여 기록이 있는 대여소를 DELETE하면?
16. 관리자가 담당하는 대여소가 삭제되면 관리자 행은?

### 상태·흐름

17. 대여 중인지 어떻게 판단하나?
18. 결제 대기를 판단하는 SQL 조건은?
19. 대여할 때 바뀌는 테이블과 컬럼은?
20. 반납+결제 때 바뀌는 테이블 5개는?
21. 반납 UPDATE에서 세 컬럼을 동시에 넣어야 하는 이유는?
22. 결제 대기 대여에 mileage 행이 있나? 왜?
23. 대여 중인 자전거의 bicycle_status와 bicycle_station_id는?
24. 빈 거치대 수 계산에 정비 중 자전거가 포함되나?
25. 마일리지 사용 내역은 어느 테이블 어느 조건?
26. 탈퇴하면 어떤 SQL이 실행되나? DELETE인가?

### 응용

27. 보유 1,660P인 jang10이 1,000원 대여를 결제할 때 최대 할인은? 최종 금액은?
28. 95분 이용, 4.56km 이동, 200P 사용 → amount, discount, final, 적립 포인트, 결제 후 잔액 변화는?
29. payment에 (2000, 2500, -500, …)을 INSERT하면? 어떤 제약에 걸리나?
30. rental에 end_time만 넣고 return_station_id를 NULL로 UPDATE하면?
31. 두 사람이 같은 자전거를 동시에 빌리면 DB에서 어떻게 막히나?
32. 1인 1대 규칙을 DB 제약만으로 막으려면?
33. 시연 데이터에서 결제 대기인 회원 4명(hong1, park4, kwon16, ahn18) 중 지금 대여 중인 사람은?

<details>
<summary>정답 보기</summary>

1. station → adminstaff → bicycle → user → rental → payment → mileage
2. 8개. rental에 4개 (rental_user_id, rental_bicycle_id, start_station_id, return_station_id)
3. station 1, user 1, rental 3, payment 3, mileage 1
4. staff_login_id, user_login_id, user_phone, payment_rental_id, mileage_rental_id
5. station_contactnumber, staff_station_id, bicycle_station_id, rental_end_time, rental_distance, return_station_id
6. 출발 대여소(start_station_id)와 반납 대여소(return_station_id) FK 2개
7. 아니다. UNIQUE는 이용자 연락처만
8. DECIMAL(6,2), 9999.99 (앱은 99.99로 제한)
9. 카드, 계좌이체, 간편결제
10. 기본값 0, CHECK user_mileage >= 0
11. fk_staff_station, fk_bicycle_station. "현재 소속"이라 대여소가 없어지면 소속만 비우면 되고, 이력이 아님
12. fk_rental_return_station
13. payment_rental_id에 UNIQUE가 있어서 같은 대여 번호로 두 번 결제 행을 만들 수 없음
14. mileage.mileage_rental_id → rental.rental_id, rental.rental_user_id → `user`.user_id
15. fk_rental_start_station(또는 return) ON DELETE RESTRICT로 거부된다
16. staff_station_id가 NULL이 된다 (행은 남음)
17. rental_end_time IS NULL (반납 3종이 모두 NULL)
18. rental_end_time IS NOT NULL AND (LEFT JOIN한) payment_id IS NULL
19. bicycle (status = RENTED, station_id = NULL), rental (새 행 INSERT)
20. rental, bicycle, payment, mileage, user
21. chk_rental_return 때문. 셋 다 NULL이거나 셋 다 NOT NULL이어야 함
22. 없다. mileage는 결제 트랜잭션에서 생성되므로
23. RENTED, NULL
24. 포함된다. COUNT는 그 대여소의 모든 자전거 (정비 중도 거치대를 차지함)
25. payment, payment_discount > 0
26. UPDATE `user` SET user_status = 'WITHDRAWN'. DELETE 아님
27. min(1000, 1660) = 1,000P 할인, 최종 0원 (discount = amount라 CHECK 통과)
28. 초과 35분 → 2단위 → amount 2,000 / discount 200 / final 1,800 / 적립 456P / 잔액 +256 (−200 +456)
29. chk_payment_discount(할인 2,500 > 금액 2,000)에 걸려 거부. final은 2000 − 2500 = −500이라 chk_payment_final 자체는 통과한다는 점이 함정
30. chk_rental_return 위반으로 거부
31. 대여 트랜잭션이 bicycle 행을 SELECT … FOR UPDATE로 잠금. 두 번째 트랜잭션은 기다렸다가 status가 RENTED인 것을 보고 거부됨
32. 트리거로 INSERT 전 검사하거나, "end_time이 NULL일 때만 user_id 값을 갖는 생성 컬럼"을 만들고 UNIQUE 인덱스를 건다 (현재 DDL에는 없음, 프로그램으로 막음)
33. hong1(31번), park4(32번). kwon16·ahn18은 결제 대기만 있음

</details>

---

## 10. 최종 점검 체크리스트

- [ ] 화이트보드에 ERD를 안 보고 그릴 수 있다 (테이블 7개, 선 8개, 1:0..1 표시 2개)
- [ ] NULL 허용 컬럼 6개와 각각 NULL인 이유를 말할 수 있다
- [ ] CHECK 9개, UNIQUE 5개를 이름 없이라도 내용으로 말할 수 있다
- [ ] ON DELETE가 RESTRICT인 것과 SET NULL인 것을 구분하고 이유를 말할 수 있다
- [ ] 대여·반납·결제 때 바뀌는 테이블을 순서대로 말할 수 있다
- [ ] "대여 중", "결제 대기", "마일리지 사용"을 SQL 조건으로 말할 수 있다
- [ ] DB 제약이 못 막고 프로그램이 막는 규칙 3개 이상과 보완책을 말할 수 있다
- [ ] 반정규화 컬럼(user_mileage)의 장단점과 일관성 유지 방법을 말할 수 있다
