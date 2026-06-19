echo "Iniciando criação das bases..."


mysql -u root -p$MYSQL_ROOT_PASSWORD -e "CREATE DATABASE IF NOT EXISTS ApoiaMaisDB;"


mysql -u root -p$MYSQL_ROOT_PASSWORD ApoiaMaisDB < /docker-entrypoint-initdb.d/auth-db/schema.sql
mysql -u root -p$MYSQL_ROOT_PASSWORD ApoiaMaisDB < /docker-entrypoint-initdb.d/ludic-db/schema.sql
mysql -u root -p$MYSQL_ROOT_PASSWORD ApoiaMaisDB < /docker-entrypoint-initdb.d/notification-db/schema.sql


echo "Bases criadas com sucesso!"