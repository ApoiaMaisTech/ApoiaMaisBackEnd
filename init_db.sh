#!/bin/bash
# init_db.sh

echo "Iniciando criação das bases..."

# Executa cada um explicitamente
mysql -u root -p$MYSQL_ROOT_PASSWORD -e "CREATE DATABASE IF NOT EXISTS ApoiaMaisDB;"

# Lê os arquivos da pasta montada (ajuste os caminhos conforme sua estrutura)
mysql -u root -p$MYSQL_ROOT_PASSWORD ApoiaMaisDB < /docker-entrypoint-initdb.d/auth-db/schema.sql
mysql -u root -p$MYSQL_ROOT_PASSWORD ApoiaMaisDB < /docker-entrypoint-initdb.d/ludic-db/schema.sql
mysql -u root -p$MYSQL_ROOT_PASSWORD ApoiaMaisDB < /docker-entrypoint-initdb.d/notification-db/schema.sql
# ... adicione os outros ...

echo "Bases criadas com sucesso!"