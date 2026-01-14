import os
from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine
import numpy as np


def create_demo_files():
    """Создание демонстрационных аудиофайлов"""

    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)

    print("🎵 Creating demo audio files...")

    # Русская речь (синусоида для имитации)
    print("Creating Russian sample...")
    ru_audio = Sine(220).to_audio_segment(duration=5000)  # 5 секунд
    ru_audio.export(demo_dir / "sample_ru.mp3", format="mp3")

    # Английская речь
    print("Creating English sample...")
    en_audio = Sine(440).to_audio_segment(duration=3000)  # 3 секунды
    en_audio.export(demo_dir / "sample_en.wav", format="wav")

    # Короткая речь
    print("Creating short speech sample...")
    short_audio = Sine(330).to_audio_segment(duration=1500)  # 1.5 секунды
    short_audio.export(demo_dir / "sample_speech.m4a", format="ipod")

    # Создаем текстовый файл с демо-транскрипциями
    demo_text = """Это демонстрационная транскрипция русской речи.

    Hello, this is a demo transcription of English speech.

    Short speech example for testing.
    """

    (demo_dir / "sample_transcriptions.txt").write_text(demo_text)

    print(f"✅ Created demo files in {demo_dir.absolute()}")
    print(f"   - sample_ru.mp3 (5s)")
    print(f"   - sample_en.wav (3s)")
    print(f"   - sample_speech.m4a (1.5s)")
    print(f"   - sample_transcriptions.txt")


if __name__ == "__main__":
    create_demo_files()