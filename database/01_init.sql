CREATE DATABASE IF NOT EXISTS ApoiaMaisDB;
USE ApoiaMaisDB;

SOURCE /docker-entrypoint-initdb.d/auth-db/schema.sql;

SOURCE /docker-entrypoint-initdb.d/ludic-db/schema.sql;

SOURCE /docker-entrypoint-initdb.d/notification-db/schema.sql;
SOURCE /docker-entrypoint-initdb.d/file-db/schema.sql;

SOURCE /docker-entrypoint-initdb.d/audit-db/schema.sql;