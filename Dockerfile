FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Копируем единый requirements
COPY requirements.txt .

# Устанавливаем все зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p uploads outputs demo_data

# Создаем скрипт запуска
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Открываем порты
EXPOSE 8000 8501

# Определяем точку входа
ENTRYPOINT ["./docker-entrypoint.sh"]