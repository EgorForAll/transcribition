#!/bin/bash

set -e

echo "🚀 Starting Transcription Service..."

# Создаем демо-данные, если их нет
if [ ! -f "demo_data/sample_ru.mp3" ] && [ -f "app/demo/create_demo_files.py" ]; then
    echo "📁 Creating demo files..."
    python app/demo/create_demo_files.py
fi

# Функция для запуска API
start_api() {
    echo "🌐 Starting FastAPI server on port 8000..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    API_PID=$!
    echo "✅ API started (PID: $API_PID)"
}

# Функция для запуска демо
start_demo() {
    echo "🎪 Starting Streamlit demo on port 8501..."
    # Ждем запуска API
    sleep 2

    # Проверяем, доступен ли API
    echo "⏳ Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ API is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "⚠️ API is not responding, but starting demo anyway"
        fi
        sleep 1
    done

    streamlit run app/demo/streamlit_app.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --theme.base="light" \
        --theme.primaryColor="#1E88E5" \
        --theme.secondaryBackgroundColor="#F0F2F6" \
        --theme.textColor="#262730" \
        --browser.serverAddress="0.0.0.0" &
    DEMO_PID=$!
    echo "✅ Demo started (PID: $DEMO_PID)"
}

# Функция остановки
stop_services() {
    echo "🛑 Stopping services..."
    kill $API_PID $DEMO_PID 2>/dev/null || true
    wait
    echo "👋 Services stopped"
    exit 0
}

# Обработка сигналов
trap stop_services SIGINT SIGTERM

# Определение режима запуска
MODE="${RUN_MODE:-all}"

case $MODE in
    "api")
        echo "🔧 Mode: API only"
        start_api
        ;;
    "demo")
        echo "🔧 Mode: Demo only"
        if [ -z "$API_URL" ]; then
            echo "⚠️ API_URL not set, using default"
            export API_URL="http://localhost:8000"
        fi
        start_demo
        ;;
    "all")
        echo "🔧 Mode: Full stack (API + Demo)"
        start_api
        start_demo
        ;;
    *)
        echo "❌ Unknown mode: $MODE. Use 'api', 'demo', or 'all'"
        exit 1
        ;;
esac

# Информация о доступных сервисах
echo ""
echo "========================================="
echo "🚀 Services are running!"
echo ""

if [ "$MODE" = "api" ] || [ "$MODE" = "all" ]; then
    echo "🌐 API Documentation: http://localhost:8000/docs"
    echo "🌐 API Health check: http://localhost:8000/health"
fi

if [ "$MODE" = "demo" ] || [ "$MODE" = "all" ]; then
    echo "🎪 Demo Dashboard: http://localhost:8501"
fi

echo ""
echo "📝 Logs are shown below. Press Ctrl+C to stop."
echo "========================================="

# Ждем завершения процессов
wait $API_PID $DEMO_PID 2>/dev/null || true