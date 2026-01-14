import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import io
import tempfile
import json
import time
from datetime import datetime
from pathlib import Path
import requests
import base64
from pydub import AudioSegment
import librosa
import librosa.display
import matplotlib.pyplot as plt

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Audio Transcription Demo",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стили CSS для улучшенного интерфейса
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin: 10px 0;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        margin: 10px 0;
    }
    .stProgress > div > div > div > div {
        background-color: #1E88E5;
    }
    .audio-player {
        margin: 20px 0;
    }
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


class TranscriptionDemo:
    def __init__(self, api_url="http://transcription-service:8000"):
        self.api_url = api_url
        self.demo_files = {
            "Русская речь (пример)": "demo_data/sample_ru.mp3",
            "Английская речь (пример)": "demo_data/sample_en.wav",
            "Короткая речь (пример)": "demo_data/sample_speech.m4a"
        }

    def get_audio_duration(self, audio_bytes):
        """Получение длительности аудио"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            audio = AudioSegment.from_file(tmp.name)
            return len(audio) / 1000  # Конвертируем в секунды

    def create_audio_waveform(self, audio_bytes):
        """Создание визуализации аудио"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            y, sr = librosa.load(tmp.name)

            fig, ax = plt.subplots(figsize=(10, 3))
            librosa.display.waveshow(y, sr=sr, ax=ax, alpha=0.5)
            ax.set_title('Визуализация аудио', fontsize=14)
            ax.set_xlabel('Время (секунды)')
            ax.set_ylabel('Амплитуда')
            ax.grid(True, alpha=0.3)

            return fig

    def transcribe_audio(self, audio_bytes, language="ru", filename="audio.mp3"):
        """Отправка аудио на транскрипцию"""
        files = {'file': (filename, audio_bytes, 'audio/mpeg')}
        data = {'language': language}

        with st.spinner('🎤 Идет транскрипция...'):
            progress_bar = st.progress(0)

            for i in range(100):
                time.sleep(0.02)
                progress_bar.progress(i + 1)

            try:
                response = requests.post(
                    f"{self.api_url}/transcribe",
                    files=files,
                    data=data,
                    timeout=60
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    st.error(f"Ошибка транскрипции: {response.text}")
                    return None

            except Exception as e:
                st.error(f"Ошибка подключения к сервису: {str(e)}")
                return None

    def display_stats(self, result):
        """Отображение статистики транскрипции"""
        if not result:
            return

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Длина текста", f"{result.get('text_length', 0)} символов")

        with col2:
            st.metric("Статус", "✅ Успешно" if result.get('status') == 'success' else "❌ Ошибка")

        with col3:
            st.metric("Время", datetime.now().strftime("%H:%M:%S"))

        with col4:
            st.metric("ID транскрипции", result.get('transcription_id', 'N/A')[:8])

    def create_word_cloud_data(self, text):
        """Создание данных для облака слов"""
        words = text.lower().split()
        from collections import Counter
        word_counts = Counter(words)

        df = pd.DataFrame({
            'word': list(word_counts.keys()),
            'count': list(word_counts.values())
        })

        # Фильтруем короткие слова
        df = df[df['word'].str.len() > 2].head(20)

        fig = px.bar(df, x='count', y='word', orientation='h',
                     title='Частота слов в тексте',
                     color='count',
                     color_continuous_scale='viridis')
        fig.update_layout(height=400)
        return fig


def main():
    # Заголовок приложения
    st.markdown('<h1 class="main-header">🎤 Демо-стенд Транскрипции Аудио</h1>', unsafe_allow_html=True)

    # Сайдбар с информацией
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3161/3161837.png", width=100)
        st.markdown("### ℹ️ Информация")
        st.markdown("""
        **Демо-версия сервиса транскрипции аудио в текст**

        **Возможности:**
        - Загрузка аудиофайлов
        - Автоматическая транскрипция
        - Поддержка 10+ форматов
        - Визуализация результатов

        **Поддерживаемые форматы:**
        - MP3, WAV, M4A, FLAC
        - OGG, AAC, WMA
        - и другие...
        """)

        st.markdown("---")
        st.markdown("### ⚙️ Настройки")
        language = st.selectbox(
            "Язык транскрипции",
            ["ru", "en", "auto"],
            help="Выберите язык аудио или 'auto' для автоопределения"
        )

        st.markdown("---")
        st.markdown("### 📊 Статистика")
        st.info("""
        **Средняя точность:** 95%  
        **Макс. длительность:** 30 мин  
        **Поддержка языков:** 50+  
        **Время обработки:** 1-5 мин
        """)

    # Инициализация демо
    demo = TranscriptionDemo()

    # Основной контейнер
    tab1, tab2, tab3 = st.tabs(["📁 Загрузить файл", "🎧 Демо файлы", "📈 Аналитика"])

    with tab1:
        st.markdown('<h2 class="sub-header">Загрузка аудиофайла</h2>', unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Выберите аудиофайл",
                type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac'],
                help="Загрузите аудиофайл для транскрипции"
            )

            if uploaded_file is not None:
                # Показываем информацию о файле
                file_bytes = uploaded_file.getvalue()
                duration = demo.get_audio_duration(file_bytes)

                st.markdown(f"**Информация о файле:**")
                st.info(f"""
                📄 Имя файла: {uploaded_file.name}  
                📊 Размер: {len(file_bytes) / 1024:.1f} KB  
                ⏱️ Длительность: {duration:.1f} секунд  
                🎵 Тип: {uploaded_file.type}
                """)

                # Визуализация аудио
                st.markdown("**Визуализация аудио:**")
                waveform_fig = demo.create_audio_waveform(file_bytes)
                st.pyplot(waveform_fig)

                # Кнопка транскрипции
                if st.button("🚀 Начать транскрипцию", type="primary", use_container_width=True):
                    result = demo.transcribe_audio(
                        file_bytes,
                        language=language,
                        filename=uploaded_file.name
                    )

                    if result:
                        st.markdown('<div class="success-box">✅ Транскрипция завершена успешно!</div>',
                                    unsafe_allow_html=True)

                        # Отображение статистики
                        demo.display_stats(result)

                        # Отображение результата
                        st.markdown("### 📝 Результат транскрипции:")
                        st.text_area("Транскрибированный текст", result.get('text', ''), height=200)

                        # Дополнительная информация
                        with st.expander("📋 Детальная информация"):
                            st.json(result)

        with col2:
            st.markdown("### 📋 Инструкция")
            st.markdown("""
            1. **Загрузите** аудиофайл
            2. **Прослушайте** аудио
            3. **Нажмите** кнопку транскрипции
            4. **Получите** текст
            5. **Скачайте** результат
            """)

            st.markdown("---")
            st.markdown("### 🎧 Плеер")
            if uploaded_file is not None:
                st.audio(uploaded_file, format=uploaded_file.type)

    with tab2:
        st.markdown('<h2 class="sub-header">Демонстрационные файлы</h2>', unsafe_allow_html=True)

        st.markdown("""
        ### Попробуйте на демо-файлах:
        Выберите один из готовых примеров для быстрого тестирования сервиса.
        """)

        selected_demo = st.selectbox("Выберите демо-файл", list(demo.demo_files.keys()))

        if selected_demo:
            file_path = demo.demo_files[selected_demo]

            try:
                with open(file_path, 'rb') as f:
                    demo_bytes = f.read()

                # Информация о демо-файле
                col1, col2 = st.columns(2)

                with col1:
                    st.audio(demo_bytes, format='audio/mp3')

                with col2:
                    duration = demo.get_audio_duration(demo_bytes)
                    st.markdown(f"""
                    **Характеристики:**
                    - 📄 Файл: {Path(file_path).name}
                    - ⏱️ Длительность: {duration:.1f} сек
                    - 🎵 Формат: {Path(file_path).suffix}
                    """)

                # Визуализация
                st.markdown("**Волновая форма:**")
                waveform_fig = demo.create_audio_waveform(demo_bytes)
                st.pyplot(waveform_fig)

                # Кнопка для быстрой транскрипции
                if st.button(f"🎯 Транскрибировать '{selected_demo}'", type="primary"):
                    result = demo.transcribe_audio(
                        demo_bytes,
                        language=language,
                        filename=Path(file_path).name
                    )

                    if result:
                        st.markdown('<div class="success-box">✅ Демо-транскрипция завершена!</div>',
                                    unsafe_allow_html=True)

                        st.markdown("### 📝 Результат:")
                        st.text_area("Текст", result.get('text', ''), height=150)

                        # Облако слов
                        if result.get('text'):
                            word_fig = demo.create_word_cloud_data(result.get('text'))
                            st.plotly_chart(word_fig, use_container_width=True)

            except FileNotFoundError:
                st.warning("Демо-файл не найден. Убедитесь, что файлы находятся в папке demo_data/")

    with tab3:
        st.markdown('<h2 class="sub-header">Аналитика и метрики</h2>', unsafe_allow_html=True)

        # Создаем демо-данные для визуализации
        st.markdown("### 📊 Производительность системы")

        metrics_data = pd.DataFrame({
            'Дата': pd.date_range(start='2024-01-01', periods=30, freq='D'),
            'Транскрипции': np.random.randint(50, 200, 30),
            'Средняя точность': np.random.uniform(0.85, 0.98, 30),
            'Время обработки (сек)': np.random.uniform(1, 10, 30)
        })

        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.line(metrics_data, x='Дата', y='Транскрипции',
                           title='Количество транскрипций в день')
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(metrics_data, x='Дата', y='Средняя точность',
                          title='Точность транскрипции')
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🎯 Ключевые метрики")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="stats-card"><h3>1,250</h3><p>Всего транскрипций</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="stats-card"><h3>94.5%</h3><p>Средняя точность</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="stats-card"><h3>4.2 сек</h3><p>Среднее время</p></div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="stats-card"><h3>98.7%</h3><p>Доступность</p></div>', unsafe_allow_html=True)



if __name__ == "__main__":
    main()