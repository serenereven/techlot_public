#!/bin/bash
BACKUP_DIR="/opt/techlot/db_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p $BACKUP_DIR

docker compose exec -T db pg_dump -U techlot_user techlot_db > "$BACKUP_DIR/backup_$TIMESTAMP.sql"
echo "Бэкап сохранён: $BACKUP_DIR/backup_$TIMESTAMP.sql"