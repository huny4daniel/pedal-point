-- =============================================================
-- PedalPoint · padal DB 스키마 (MySQL 8.0.16 이상)
-- 테이블 7개, FK 10개, 뷰 1개
--
-- 주의: 이 스크립트는 padal DB를 지우고 새로 만든다.
-- =============================================================

DROP DATABASE IF EXISTS padal;
CREATE DATABASE padal
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE padal;

-- -------------------------------------------------------------
-- user : 자전거 이용자
-- -------------------------------------------------------------
CREATE TABLE `user` (
  user_id          INT          NOT NULL AUTO_INCREMENT,
  user_name        VARCHAR(50)  NOT NULL,
  user_birth_date  DATE         NULL,
  user_phone       VARCHAR(20)  NOT NULL,
  user_address     VARCHAR(255) NULL,
  user_status      ENUM('ACTIVE', 'SUSPENDED', 'WITHDRAWN') NOT NULL DEFAULT 'ACTIVE',
  user_created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_user_phone (user_phone)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- station : 대여소
-- -------------------------------------------------------------
CREATE TABLE station (
  station_id             INT           NOT NULL AUTO_INCREMENT,
  station_name           VARCHAR(100)  NOT NULL,
  station_region         VARCHAR(50)   NOT NULL,
  station_address        VARCHAR(255)  NOT NULL,
  station_contactnumber  VARCHAR(20)   NULL,
  station_latitude       DECIMAL(10,7) NULL,
  station_longitude      DECIMAL(10,7) NULL,
  station_totaldocks     INT           NOT NULL,
  station_status         ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
  station_created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (station_id)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- bicycle : 공공자전거 (bicycle_station_id = 현재 대여소, 대여 중 NULL)
-- -------------------------------------------------------------
CREATE TABLE bicycle (
  bicycle_id             INT      NOT NULL AUTO_INCREMENT,
  bicycle_status         ENUM('AVAILABLE', 'RENTED', 'MAINTENANCE') NOT NULL DEFAULT 'AVAILABLE',
  bicycle_registered_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  bicycle_station_id     INT      NULL,
  PRIMARY KEY (bicycle_id),
  CONSTRAINT fk_bicycle_station
    FOREIGN KEY (bicycle_station_id) REFERENCES station (station_id)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- rental : 대여 기록
-- -------------------------------------------------------------
CREATE TABLE rental (
  rental_id          INT          NOT NULL AUTO_INCREMENT,
  rental_start_time  DATETIME     NOT NULL,
  rental_end_time    DATETIME     NULL,
  rental_status      ENUM('RENTING', 'RETURNED') NOT NULL DEFAULT 'RENTING',
  rental_distance    DECIMAL(6,2) NULL,
  start_station_id   INT          NOT NULL,
  return_station_id  INT          NULL,
  rental_bicycle_id  INT          NOT NULL,
  rental_user_id     INT          NOT NULL,
  PRIMARY KEY (rental_id),
  CONSTRAINT fk_rental_start_station
    FOREIGN KEY (start_station_id)  REFERENCES station (station_id),
  CONSTRAINT fk_rental_return_station
    FOREIGN KEY (return_station_id) REFERENCES station (station_id),
  CONSTRAINT fk_rental_bicycle
    FOREIGN KEY (rental_bicycle_id) REFERENCES bicycle (bicycle_id),
  CONSTRAINT fk_rental_user
    FOREIGN KEY (rental_user_id)    REFERENCES `user` (user_id),
  -- 이동거리는 0 이상
  CONSTRAINT ck_rental_distance
    CHECK (rental_distance IS NULL OR rental_distance >= 0),
  -- 반납 시간은 대여 시간 이후
  CONSTRAINT ck_rental_time
    CHECK (rental_end_time IS NULL OR rental_end_time >= rental_start_time)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- payment : 대여 1건의 결제
-- -------------------------------------------------------------
CREATE TABLE payment (
  payment_id            INT      NOT NULL AUTO_INCREMENT,
  payment_amount        INT      NOT NULL,
  payment_discount      INT      NOT NULL DEFAULT 0,
  payment_final_amount  INT      NOT NULL,
  payment_method        ENUM('CARD', 'MOBILE', 'TRANSFER') NOT NULL,
  payment_at            DATETIME NOT NULL,
  payment_rental_id     INT      NOT NULL,
  PRIMARY KEY (payment_id),
  UNIQUE KEY uq_payment_rental (payment_rental_id),
  CONSTRAINT fk_payment_rental
    FOREIGN KEY (payment_rental_id) REFERENCES rental (rental_id),
  -- 할인액은 0 이상 이용금액 이하
  CONSTRAINT ck_payment_discount
    CHECK (payment_discount >= 0 AND payment_discount <= payment_amount),
  -- 최종금액 = 이용금액 - 할인액
  CONSTRAINT ck_payment_final
    CHECK (payment_final_amount = payment_amount - payment_discount)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- mileage : 마일리지 적립(EARN)·사용(USE) 내역
-- -------------------------------------------------------------
CREATE TABLE mileage (
  mileage_id          INT      NOT NULL AUTO_INCREMENT,
  mileage_type        ENUM('EARN', 'USE') NOT NULL,
  mileage_point       INT      NOT NULL,
  mileage_created_at  DATETIME NOT NULL,
  mileage_user_id     INT      NOT NULL,
  mileage_rental_id   INT      NULL,
  mileage_payment_id  INT      NULL,
  PRIMARY KEY (mileage_id),
  UNIQUE KEY uq_mileage_rental  (mileage_rental_id),
  UNIQUE KEY uq_mileage_payment (mileage_payment_id),
  CONSTRAINT fk_mileage_user
    FOREIGN KEY (mileage_user_id)    REFERENCES `user` (user_id),
  CONSTRAINT fk_mileage_rental
    FOREIGN KEY (mileage_rental_id)  REFERENCES rental (rental_id),
  CONSTRAINT fk_mileage_payment
    FOREIGN KEY (mileage_payment_id) REFERENCES payment (payment_id),
  -- 포인트는 항상 양수
  CONSTRAINT ck_mileage_point
    CHECK (mileage_point > 0),
  -- 배타 관계: 적립(EARN)은 rental에만, 사용(USE)은 payment에만 연결
  CONSTRAINT ck_mileage_exclusive
    CHECK (
      (mileage_type = 'EARN' AND mileage_rental_id IS NOT NULL AND mileage_payment_id IS NULL)
      OR
      (mileage_type = 'USE'  AND mileage_payment_id IS NOT NULL AND mileage_rental_id IS NULL)
    )
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- adminstaff : 운영관리자
-- -------------------------------------------------------------
CREATE TABLE adminstaff (
  staff_id          INT         NOT NULL AUTO_INCREMENT,
  staff_name        VARCHAR(50) NOT NULL,
  staff_phone       VARCHAR(20) NOT NULL,
  staff_is_active   TINYINT(1)  NOT NULL DEFAULT 1,
  staff_created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  staff_station_id  INT         NULL,
  PRIMARY KEY (staff_id),
  UNIQUE KEY uq_staff_phone (staff_phone),
  CONSTRAINT fk_staff_station
    FOREIGN KEY (staff_station_id) REFERENCES station (station_id)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- v_user_mileage_balance : 사용자별 총 적립·총 사용·잔액
-- -------------------------------------------------------------
CREATE VIEW v_user_mileage_balance AS
SELECT
  u.user_id,
  u.user_name,
  CAST(COALESCE(SUM(CASE WHEN m.mileage_type = 'EARN' THEN m.mileage_point END), 0) AS SIGNED) AS total_earned,
  CAST(COALESCE(SUM(CASE WHEN m.mileage_type = 'USE'  THEN m.mileage_point END), 0) AS SIGNED) AS total_used,
  CAST(COALESCE(SUM(CASE WHEN m.mileage_type = 'EARN' THEN m.mileage_point
                         ELSE -m.mileage_point END), 0) AS SIGNED) AS balance
FROM `user` u
LEFT JOIN mileage m ON m.mileage_user_id = u.user_id
GROUP BY u.user_id, u.user_name;
