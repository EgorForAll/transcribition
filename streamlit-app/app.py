import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Сервис аудио транскрибирования",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎤 Сервис аудио транскрибирования")

# Сайдбар с информацией
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3161/3161837.png", width=100)
    st.markdown("### ℹ️ Информация")
    st.markdown("""
    **Демо сервиса по транскрибированию текста**

    **Фичи:**
    - Загрузите аудио/видео файлы
    - Автоматическое транскрибирование текста
    - Поддержка более 20 форматов
    - Визуализированный результат
    - Статистика
    """)

    st.markdown("---")
    st.markdown("### ⚙️ Настройки")
    language = st.selectbox(
        "Параметры языка",
        ["ru", "en", "auto"],
        help="Выберите язык аудио"
    )

    st.markdown("---")
    st.markdown("### 🔗 Настройки API")
    api_url = st.text_input(
        "API URL",
        value="http://transcription-api:8000",
        help="Enter transcription API service URL"
    )

    if st.button("Тест соединения", key="test_connection"):
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Успешно!")
                health_data = response.json()
                st.info(f"Статус: {health_data.get('status', 'unknown')}")
            else:
                st.error(f"❌ Connection error: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Failed to connect: {str(e)}")

st.header("Загрузите Аудио/Видео файл")

uploaded_file = st.file_uploader(
    "Выберите аудио или видео файл",
    type=['mp3', 'wav', 'm4a', 'mp4', 'webm'],
    help="Загрузите аудио или видео файл для транскрибирования"
)

if uploaded_file:
    file_size = len(uploaded_file.getvalue())
    max_size = 50 * 1024 * 1024  # 50MB

    if file_size > max_size:
        st.error(f"⚠️ Файл слишком большой ({file_size / 1024 / 1024:.1f}MB). Макс. размер: {max_size / 1024 / 1024}MB")
    else:
        file_ext = Path(uploaded_file.name).suffix.lower()

        st.info(f"""
        📄 Имя файла: {uploaded_file.name}  
        📊 Размер: {file_size / 1024:.1f} KB  
        🎵 Тип: {'Видео' if file_ext in ['.mp4', '.webm'] else 'Аудио'}
        """)

        # Player
        if file_ext in ['.mp4', '.webm']:
            st.video(uploaded_file)
        else:
            st.audio(uploaded_file)

if uploaded_file and file_size <= max_size:
    if st.button("🚀 Начать транскрибирование...", type="primary", use_container_width=True):
        with st.spinner("Выполняется..."):
            try:
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), 'application/octet-stream')}
                data = {'language': language}

                response = requests.post(
                    f"{api_url}/transcribe",
                    files=files,
                    data=data,
                    timeout=300
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Транскрибирование завершено!")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Длина текста", f"{result.get('text_length', 0)} chars")
                    with col2:
                        st.metric("Статус", "✅ Успех" if result.get('status') == 'success' else "❌ Ошибка")
                    with col3:
                        st.metric("Время", datetime.now().strftime("%H:%M:%S"))

                    transcribed_text = ""
                    if result.get('download_url'):
                        try:
                            download_url = result['download_url']
                            if not download_url.startswith('http'):
                                base_url = api_url.rstrip('/')
                                if not download_url.startswith('/'):
                                    download_url = '/' + download_url
                                download_url = f"{base_url}{download_url}"

                            text_response = requests.get(download_url, timeout=10)
                            text_response.raise_for_status()
                            transcribed_text = text_response.text
                        except Exception as e:
                            st.error(f"Error getting text: {str(e)}")
                            transcribed_text = "Text unavailable"
                    else:
                        transcribed_text = result.get('text', result.get('transcription', ''))

                    st.text_area("Результат транскрибирования", transcribed_text, height=200)

                    with st.expander("📋 Детали"):
                        st.json(result)

                else:
                    st.error(f"❌ Transcription error: {response.status_code}")
                    if response.text:
                        st.error(f"Message: {response.text}")

            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")

st.header("📈 Аналитика")

try:
    response = requests.get(f"{api_url}/analytics/overview", timeout=10)

    if response.status_code == 200:
        analytics_data = response.json()

        if analytics_data.get('status') == 'success':
            data = analytics_data.get('data', {})

            # Проверяем, есть ли реальные данные
            total_stats = data.get('total_transcriptions', {})

            st.subheader("📊 Ключевые метрики")
            col1, col2, col3 = st.columns(3)

            with col1:
                total = total_stats.get('total', 0)
                st.metric("Всего транскрибирований", total)
            with col2:
                completed = total_stats.get('completed', 0)
                st.metric("Успешно", completed)
            with col3:
                failed = total_stats.get('failed', 0)
                st.metric("Ошибок", failed)

            # Процент успешных
            success_rate = data.get('success_rate', {})
            if success_rate.get('success_rate', 0) > 0:
                st.info(f"📈 **Процент успешных:** {success_rate.get('success_rate', 0)}%")

            # Производительность
            perf_metrics = data.get('performance_metrics', {})
            if perf_metrics:
                st.subheader("⏱️ Производительность")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Среднее время обработки",
                              f"{perf_metrics.get('avg_processing_time', 0):.1f} сек")
                with col2:
                    st.metric("Макс. время обработки",
                              f"{perf_metrics.get('max_processing_time', 0):.1f} сек")

            # Распределение по языкам
            lang_dist = data.get('language_distribution', {})
            if lang_dist:
                st.subheader("🌍 Распределение по языкам")
                for lang, count in lang_dist.items():
                    if count > 0:
                        st.write(f"- **{lang}:** {count} транскрипций")

            # Последние транскрипции
            recent = data.get('recent_transcriptions', [])
            if recent:
                st.subheader("🕐 Последние транскрипции")
                for rec in recent[:5]:
                    status_icon = "✅" if rec.get('status') == 'completed' else "❌"
                    st.write(f"{status_icon} {rec.get('filename')} ({rec.get('language')})")

            # Ежедневная статистика
            daily_stats = data.get('daily_stats', [])
            if daily_stats:
                st.subheader("📅 Статистика за последние 7 дней")
                df = pd.DataFrame(daily_stats)
                st.dataframe(df)
        else:
            st.warning("Ошибка при получении аналитики")
    else:
        st.info("Нет данных аналитики")

except Exception as e:
    st.error(f"Ошибка подключения к аналитике: {str(e)}")

if __name__ == "__main__":
    pass