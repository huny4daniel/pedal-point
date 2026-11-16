-- =============================================================
-- PedalPoint · padal 샘플 데이터 (schema.sql 실행 후 실행)
-- 시각은 실행 시점(@base) 기준 상대값이라 언제 넣어도 최근 데이터가 된다.
-- =============================================================
USE padal;
SET @base = NOW();

INSERT INTO station (station_name, station_region, station_address, station_contactnumber,
                     station_latitude, station_longitude, station_totaldocks, station_status, station_created_at) VALUES
  ('정왕역', '시흥시', '경기도 시흥시 정왕동 1799', '031-000-1001', 37.3517000, 126.7427000, 15, 'ACTIVE', @base - INTERVAL 120 DAY),
  ('한국공학대학교', '시흥시', '경기도 시흥시 산기대학로 237', '031-000-1002', 37.3403000, 126.7335000, 20, 'ACTIVE', @base - INTERVAL 120 DAY),
  ('시흥시청', '시흥시', '경기도 시흥시 시청로 20', '031-000-1003', 37.3800000, 126.8029000, 12, 'ACTIVE', @base - INTERVAL 120 DAY),
  ('배곧생명공원', '시흥시', '경기도 시흥시 배곧동 300', NULL, 37.3720000, 126.7280000, 10, 'ACTIVE', @base - INTERVAL 120 DAY),
  ('오이도역', '시흥시', '경기도 시흥시 정왕동 2077', NULL, 37.3622000, 126.7387000, 8, 'INACTIVE', @base - INTERVAL 120 DAY),
  ('안산 중앙역', '안산시', '경기도 안산시 단원구 고잔동 535', '031-000-2001', 37.3160000, 126.8385000, 15, 'ACTIVE', @base - INTERVAL 120 DAY),
  ('안산 고잔역', '안산시', '경기도 안산시 단원구 고잔동 720', '031-000-2002', 37.3170000, 126.8230000, 10, 'ACTIVE', @base - INTERVAL 120 DAY);

INSERT INTO `user` (user_name, user_birth_date, user_phone, user_address, user_status, user_created_at) VALUES
  ('김민준', '1999-03-14', '010-0000-0001', '경기도 시흥시 정왕동', 'ACTIVE', @base - INTERVAL 60 DAY),
  ('이서연', '2001-07-02', '010-0000-0002', '경기도 시흥시 배곧동', 'ACTIVE', @base - INTERVAL 57 DAY),
  ('박지호', '1995-11-23', '010-0000-0003', '경기도 안산시 단원구', 'ACTIVE', @base - INTERVAL 54 DAY),
  ('최수아', '2003-01-30', '010-0000-0004', NULL, 'ACTIVE', @base - INTERVAL 51 DAY),
  ('정도윤', '1988-05-17', '010-0000-0005', '경기도 시흥시 장곡동', 'ACTIVE', @base - INTERVAL 48 DAY),
  ('강하은', NULL, '010-0000-0006', '경기도 안산시 상록구', 'ACTIVE', @base - INTERVAL 45 DAY),
  ('윤재민', '1992-09-09', '010-0000-0007', '경기도 시흥시 은행동', 'SUSPENDED', @base - INTERVAL 42 DAY),
  ('한예린', '2000-12-25', '010-0000-0008', NULL, 'WITHDRAWN', @base - INTERVAL 39 DAY);

INSERT INTO adminstaff (staff_name, staff_phone, staff_is_active, staff_created_at, staff_station_id) VALUES
  ('오지훈', '010-0000-9001', 1, @base - INTERVAL 100 DAY, 1),
  ('문서진', '010-0000-9002', 1, @base - INTERVAL 100 DAY, 6),
  ('서준호', '010-0000-9003', 0, @base - INTERVAL 100 DAY, NULL);

-- 자전거: 과거 대여를 반영한 현재 위치·상태
INSERT INTO bicycle (bicycle_status, bicycle_registered_at, bicycle_station_id) VALUES
  ('RENTED', @base - INTERVAL 110 DAY, NULL),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1),
  ('MAINTENANCE', @base - INTERVAL 110 DAY, 1),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 2),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 2),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 2),
  ('RENTED', @base - INTERVAL 110 DAY, NULL),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 2),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 7),
  ('MAINTENANCE', @base - INTERVAL 110 DAY, 3),
  ('RENTED', @base - INTERVAL 110 DAY, NULL),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 3),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 2),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 2),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 4),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 5),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 5),
  ('MAINTENANCE', @base - INTERVAL 110 DAY, 6),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 6),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 4),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 6),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 6),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 7),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 7),
  ('AVAILABLE', @base - INTERVAL 110 DAY, 1);

INSERT INTO rental (rental_start_time, rental_end_time, rental_status, rental_distance,
                    start_station_id, return_station_id, rental_bicycle_id, rental_user_id) VALUES
  (@base - INTERVAL 20640 MINUTE, @base - INTERVAL 20600 MINUTE, 'RETURNED', '4.20', 6, 3, 25, 1),
  (@base - INTERVAL 19220 MINUTE, @base - INTERVAL 19195 MINUTE, 'RETURNED', '3.10', 2, 7, 13, 2),
  (@base - INTERVAL 18380 MINUTE, @base - INTERVAL 18310 MINUTE, 'RETURNED', '9.80', 6, 6, 26, 3),
  (@base - INTERVAL 16370 MINUTE, @base - INTERVAL 16335 MINUTE, 'RETURNED', '4.60', 3, 2, 17, 2),
  (@base - INTERVAL 14820 MINUTE, @base - INTERVAL 14765 MINUTE, 'RETURNED', '6.30', 2, 1, 7, 5),
  (@base - INTERVAL 13660 MINUTE, @base - INTERVAL 13645 MINUTE, 'RETURNED', '1.80', 4, 2, 18, 4),
  (@base - INTERVAL 13960 MINUTE, @base - INTERVAL 13875 MINUTE, 'RETURNED', '12.40', 4, 1, 20, 7),
  (@base - INTERVAL 12160 MINUTE, @base - INTERVAL 12098 MINUTE, 'RETURNED', '8.05', 2, 1, 9, 3),
  (@base - INTERVAL 10980 MINUTE, @base - INTERVAL 10950 MINUTE, 'RETURNED', '3.70', 3, 3, 16, 6),
  (@base - INTERVAL 10380 MINUTE, @base - INTERVAL 10360 MINUTE, 'RETURNED', '2.20', 7, 4, 30, 8),
  (@base - INTERVAL 9160 MINUTE, @base - INTERVAL 9112 MINUTE, 'RETURNED', '5.50', 4, 1, 30, 2),
  (@base - INTERVAL 7630 MINUTE, @base - INTERVAL 7540 MINUTE, 'RETURNED', '15.25', 3, 4, 25, 5),
  (@base - INTERVAL 6470 MINUTE, @base - INTERVAL 6462 MINUTE, 'RETURNED', '0.03', 1, 1, 1, 4),
  (@base - INTERVAL 5400 MINUTE, @base - INTERVAL 5367 MINUTE, 'RETURNED', '4.00', 1, 2, 7, 3),
  (@base - INTERVAL 3760 MINUTE, @base - INTERVAL 3694 MINUTE, 'RETURNED', '7.70', 2, 6, 8, 6),
  (@base - INTERVAL 1840 MINUTE, @base - INTERVAL 1812 MINUTE, 'RETURNED', '3.35', 6, 2, 8, 5),
  (@base - INTERVAL 75 MINUTE, NULL, 'RENTING', NULL, 3, NULL, 15, 1),
  (@base - INTERVAL 40 MINUTE, NULL, 'RENTING', NULL, 2, NULL, 11, 2),
  (@base - INTERVAL 130 MINUTE, NULL, 'RENTING', NULL, 1, NULL, 1, 3);

INSERT INTO payment (payment_amount, payment_discount, payment_final_amount, payment_method,
                     payment_at, payment_rental_id) VALUES
  (1000, 0, 1000, 'TRANSFER', @base - INTERVAL 20600 MINUTE, 1),
  (1000, 0, 1000, 'TRANSFER', @base - INTERVAL 19195 MINUTE, 2),
  (1400, 0, 1400, 'CARD', @base - INTERVAL 18310 MINUTE, 3),
  (1000, 32, 968, 'CARD', @base - INTERVAL 16335 MINUTE, 4),
  (1000, 0, 1000, 'MOBILE', @base - INTERVAL 14765 MINUTE, 5),
  (1000, 0, 1000, 'MOBILE', @base - INTERVAL 13645 MINUTE, 6),
  (2000, 0, 2000, 'TRANSFER', @base - INTERVAL 13875 MINUTE, 7),
  (1200, 102, 1098, 'CARD', @base - INTERVAL 12098 MINUTE, 8),
  (1000, 0, 1000, 'CARD', @base - INTERVAL 10950 MINUTE, 9),
  (1000, 0, 1000, 'CARD', @base - INTERVAL 10360 MINUTE, 10),
  (1000, 0, 1000, 'TRANSFER', @base - INTERVAL 9112 MINUTE, 11),
  (2200, 0, 2200, 'CARD', @base - INTERVAL 7540 MINUTE, 12),
  (1000, 0, 1000, 'CARD', @base - INTERVAL 6462 MINUTE, 13),
  (1000, 272, 728, 'MOBILE', @base - INTERVAL 5367 MINUTE, 14),
  (1400, 38, 1362, 'TRANSFER', @base - INTERVAL 3694 MINUTE, 15),
  (1000, 226, 774, 'CARD', @base - INTERVAL 1812 MINUTE, 16);

INSERT INTO mileage (mileage_type, mileage_point, mileage_created_at, mileage_user_id,
                     mileage_rental_id, mileage_payment_id) VALUES
  ('EARN', 88, @base - INTERVAL 20600 MINUTE, 1, 1, NULL),
  ('EARN', 65, @base - INTERVAL 19195 MINUTE, 2, 2, NULL),
  ('EARN', 205, @base - INTERVAL 18310 MINUTE, 3, 3, NULL),
  ('EARN', 96, @base - INTERVAL 16335 MINUTE, 2, 4, NULL),
  ('USE', 32, @base - INTERVAL 16335 MINUTE, 2, NULL, 4),
  ('EARN', 132, @base - INTERVAL 14765 MINUTE, 5, 5, NULL),
  ('EARN', 37, @base - INTERVAL 13645 MINUTE, 4, 6, NULL),
  ('EARN', 260, @base - INTERVAL 13875 MINUTE, 7, 7, NULL),
  ('EARN', 169, @base - INTERVAL 12098 MINUTE, 3, 8, NULL),
  ('USE', 102, @base - INTERVAL 12098 MINUTE, 3, NULL, 8),
  ('EARN', 77, @base - INTERVAL 10950 MINUTE, 6, 9, NULL),
  ('EARN', 46, @base - INTERVAL 10360 MINUTE, 8, 10, NULL),
  ('EARN', 115, @base - INTERVAL 9112 MINUTE, 2, 11, NULL),
  ('EARN', 320, @base - INTERVAL 7540 MINUTE, 5, 12, NULL),
  ('EARN', 84, @base - INTERVAL 5367 MINUTE, 3, 14, NULL),
  ('USE', 272, @base - INTERVAL 5367 MINUTE, 3, NULL, 14),
  ('EARN', 161, @base - INTERVAL 3694 MINUTE, 6, 15, NULL),
  ('USE', 38, @base - INTERVAL 3694 MINUTE, 6, NULL, 15),
  ('EARN', 70, @base - INTERVAL 1812 MINUTE, 5, 16, NULL),
  ('USE', 226, @base - INTERVAL 1812 MINUTE, 5, NULL, 16);

