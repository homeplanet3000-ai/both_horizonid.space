# Используем Python
FROM python:3.10-slim

# Рабочая папка внутри контейнера
WORKDIR /app

# Сначала копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# !!! ВОТ ЭТОЙ СТРОКИ НЕ ХВАТАЛО !!!
# Копируем сам скрипт и базу данных внутрь контейнера
COPY . .

# Команда запуска
CMD ["python", "limit_service.py"]
