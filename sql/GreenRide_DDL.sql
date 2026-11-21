DROP DATABASE IF EXISTS pedal;
CREATE DATABASE pedal DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE pedal;

-- 1. station (대여소)
CREATE TABLE station (
    station_id            INT           NOT NULL AUTO_INCREMENT,
    station_name          VARCHAR(100)  NOT NULL,
    station_address       VARCHAR(255)  NOT NULL,
    station_contactnumber VARCHAR(20)   NULL,
    station_totaldocks    INT           NOT NULL,
    station_status        ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    PRIMARY KEY (station_id),
    CONSTRAINT chk_station_docks CHECK (station_totaldocks > 0)
) ENGINE=InnoDB;

-- 2. adminstaff (관리자)
CREATE TABLE adminstaff (
    staff_id          INT          NOT NULL AUTO_INCREMENT,
    staff_login_id    VARCHAR(50)  NOT NULL,
    staff_password    VARCHAR(255) NOT NULL,
    staff_name        VARCHAR(50)  NOT NULL,
    staff_phone       VARCHAR(20)  NOT NULL,
    staff_is_active   TINYINT      NOT NULL DEFAULT 1,
    staff_station_id  INT          NULL,
    PRIMARY KEY (staff_id),
    CONSTRAINT uq_staff_login_id UNIQUE (staff_login_id),
    CONSTRAINT fk_staff_station FOREIGN KEY (staff_station_id)
        REFERENCES station (station_id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- 3. bicycle (자전거)
CREATE TABLE bicycle (
    bicycle_id             INT       NOT NULL AUTO_INCREMENT,
    bicycle_status         ENUM('AVAILABLE','RENTED','MAINTENANCE') NOT NULL DEFAULT 'AVAILABLE',
    bicycle_registered_at  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    bicycle_station_id     INT       NULL,
    PRIMARY KEY (bicycle_id),
    CONSTRAINT fk_bicycle_station FOREIGN KEY (bicycle_station_id)
        REFERENCES station (station_id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- 4. user (이용자)
CREATE TABLE `user` (
    user_id          INT           NOT NULL AUTO_INCREMENT,
    user_login_id    VARCHAR(50)   NOT NULL,
    user_password    VARCHAR(255)  NOT NULL,
    user_name        VARCHAR(50)   NOT NULL,
    user_phone       VARCHAR(20)   NOT NULL,
    user_mileage     INT           NOT NULL DEFAULT 0,
    user_status      ENUM('ACTIVE','SUSPENDED','WITHDRAWN') NOT NULL DEFAULT 'ACTIVE',
    user_created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT uq_user_login_id UNIQUE (user_login_id),
    CONSTRAINT uq_user_phone UNIQUE (user_phone),
    CONSTRAINT chk_user_mileage CHECK (user_mileage >= 0)
) ENGINE=InnoDB;

-- 5. rental (대여)
CREATE TABLE rental (
    rental_id          INT           NOT NULL AUTO_INCREMENT,
    rental_start_time  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rental_end_time    DATETIME      NULL,
    rental_distance    DECIMAL(6,2)  NULL,
    rental_user_id     INT           NOT NULL,
    rental_bicycle_id  INT           NOT NULL,
    start_station_id   INT           NOT NULL,
    return_station_id  INT           NULL,
    PRIMARY KEY (rental_id),
    CONSTRAINT fk_rental_user FOREIGN KEY (rental_user_id)
        REFERENCES `user` (user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_rental_bicycle FOREIGN KEY (rental_bicycle_id)
        REFERENCES bicycle (bicycle_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_rental_start_station FOREIGN KEY (start_station_id)
        REFERENCES station (station_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_rental_return_station FOREIGN KEY (return_station_id)
        REFERENCES station (station_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT chk_rental_time CHECK (rental_end_time IS NULL OR rental_end_time >= rental_start_time),
    CONSTRAINT chk_rental_distance CHECK (rental_distance IS NULL OR rental_distance >= 0),
    CONSTRAINT chk_rental_return CHECK (
        (rental_end_time IS NULL AND return_station_id IS NULL AND rental_distance IS NULL) OR
        (rental_end_time IS NOT NULL AND return_station_id IS NOT NULL AND rental_distance IS NOT NULL)
    )
) ENGINE=InnoDB;

-- 6. payment (결제)
CREATE TABLE payment (
    payment_id            INT       NOT NULL AUTO_INCREMENT,
    payment_amount        INT       NOT NULL,
    payment_discount      INT       NOT NULL DEFAULT 0,
    payment_final_amount  INT       NOT NULL,
    payment_method        ENUM('카드','계좌이체','간편결제') NOT NULL,
    payment_at            DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_rental_id     INT       NOT NULL,
    PRIMARY KEY (payment_id),
    CONSTRAINT uq_payment_rental UNIQUE (payment_rental_id),
    CONSTRAINT fk_payment_rental FOREIGN KEY (payment_rental_id)
        REFERENCES rental (rental_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_payment_amount CHECK (payment_amount >= 0),
    CONSTRAINT chk_payment_discount CHECK (payment_discount >= 0 AND payment_discount <= payment_amount),
    CONSTRAINT chk_payment_final CHECK (payment_final_amount = payment_amount - payment_discount)
) ENGINE=InnoDB;

-- 7. mileage (적립 내역)
CREATE TABLE mileage (
    mileage_id          INT       NOT NULL AUTO_INCREMENT,
    mileage_point       INT       NOT NULL,
    mileage_created_at  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mileage_rental_id   INT       NOT NULL,
    PRIMARY KEY (mileage_id),
    CONSTRAINT uq_mileage_rental UNIQUE (mileage_rental_id),
    CONSTRAINT fk_mileage_rental FOREIGN KEY (mileage_rental_id)
        REFERENCES rental (rental_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_mileage_point CHECK (mileage_point >= 0)
) ENGINE=InnoDB;