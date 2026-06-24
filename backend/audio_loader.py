import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np

TARGET_SAMPLE_RATE = 22050


def _load_with_bundled_ffmpeg(file_path: Path, sample_rate: int) -> Tuple[np.ndarray, int]:
    """当系统音频库无法解码时，使用项目依赖提供的便携 FFmpeg 转码。"""
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise RuntimeError("缺少可用的音频解码器，请安装 imageio-ffmpeg 或系统 FFmpeg") from error

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="chordpilot_decode_") as temp_dir:
        wav_path = Path(temp_dir) / "decoded.wav"
        subprocess.run(
            [
                ffmpeg_path,
                "-v",
                "error",
                "-y",
                "-i",
                str(file_path),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                str(wav_path),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
        return librosa.load(str(wav_path), sr=sample_rate, mono=True)


def load_audio(file_path: Path, sample_rate: int = TARGET_SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """读取音频、转为单声道，并统一采样率与幅度。"""
    try:
        audio, sr = librosa.load(str(file_path), sr=sample_rate, mono=True)
    except Exception:
        audio, sr = _load_with_bundled_ffmpeg(file_path, sample_rate)
    if audio.size == 0:
        raise ValueError("音频文件中没有可分析的内容")

    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio = audio / peak
    return audio.astype(np.float32), sr


def extract_harmonic_audio(audio: np.ndarray) -> np.ndarray:
    """弱化鼓点等瞬态成分，使和声色度更稳定。"""
    if audio.size < 2048:
        return audio
    harmonic = librosa.effects.harmonic(audio, margin=2.0)
    # 某些电子乐或强压缩音频经过 HPSS 后会几乎无声，此时保留原始音频更可靠。
    original_rms = float(np.sqrt(np.mean(np.square(audio))))
    harmonic_rms = float(np.sqrt(np.mean(np.square(harmonic))))
    if original_rms > 0 and harmonic_rms < original_rms * 0.08:
        return audio
    return harmonic
