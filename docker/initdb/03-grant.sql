-- Docker only.
--
-- The brief creates 'clinic_user'@'localhost'. Inside Docker each service
-- connects from a different container, so the host is never "localhost" and
-- that account would be rejected with "Access denied".
--
-- This adds the same limited account for any host. It grants no extra
-- privileges: still SELECT, INSERT, UPDATE only, and still no DELETE.
-- It is not used when running the services directly on the machine.

CREATE DATABASE IF NOT EXISTS clinic_system;

CREATE USER IF NOT EXISTS 'clinic_user'@'%' IDENTIFIED BY 'choose_a_password';
GRANT SELECT, INSERT, UPDATE ON clinic_system.* TO 'clinic_user'@'%';
FLUSH PRIVILEGES;
