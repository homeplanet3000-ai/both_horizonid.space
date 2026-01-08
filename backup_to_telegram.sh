#!/bin/bash

# --- НАСТРОЙКИ ---
# Подгружаем переменные из .env (там лежат пароли от базы и токен бота)
source /opt/marzban/.env

# ВАШ TELEGRAM ID (куда отправлять файл)
CHAT_ID="1375385135"

# Токен бота берем из конфига (или можно вписать вручную)
TG_TOKEN="$BOT_TOKEN"

# Папка для временного создания архива
BACKUP_DIR="/root/backups_temp"
mkdir -p $BACKUP_DIR

# Имя файла: Full_Backup_Дата_Время.zip
DATE=$(date +"%Y-%m-%d_%H-%M")
ARCHIVE_NAME="Full_Server_Backup_$DATE.zip"
ARCHIVE_PATH="$BACKUP_DIR/$ARCHIVE_NAME"

# Функция отправки в Telegram
send_telegram() {
    FILE=$1
    CAPTION=$2
    curl -s -F chat_id=$CHAT_ID \
         -F document=@$FILE \
         -F caption="$CAPTION" \
         https://api.telegram.org/bot$TG_TOKEN/sendDocument > /dev/null
}

echo "⏳ [1/3] Создаю дамп базы данных..."
# Выгружаем базу в файл внутри папки проекта, чтобы он попал в архив
docker exec marzban-mariadb mysqldump -u marzban -p"$DB_PASSWORD" marzban > /opt/marzban/marzban_db_dump.sql

echo "📦 [2/3] Архивирую все файлы сервера..."
# Мы сохраняем структуру папок.
# Исключаем тяжелые логи и сырые файлы базы (так как у нас есть дамп)
zip -r $ARCHIVE_PATH \
    /opt/marzban \
    /var/lib/marzban \
    -x "/opt/marzban/mysql_data/*" \
    -x "*.log" \
    -x "*/__pycache__/*" \
    -x "*/.git/*"

echo "📤 [3/3] Отправляю архив в Telegram..."
send_telegram "$ARCHIVE_PATH" "📦 Полный бэкап сервера (Файлы + База) от $DATE"

# --- ОЧИСТКА ---
# Удаляем временный дамп базы
rm /opt/marzban/marzban_db_dump.sql
# Удаляем сам архив с диска (он уже в телеграме)
rm $ARCHIVE_PATH
# Удаляем временную папку
rmdir $BACKUP_DIR

echo "✅ Бэкап успешно отправлен в Telegram!"
