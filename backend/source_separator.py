import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import librosa
import numpy as np
import soundfile as sf


def _demucs_available() -> bool:
    try:
        import demucs  # noqa: F401

        return True
    except ImportError:
        return False


def _demucs_environment() -> dict:
    """让 Windows 上通过 winget 安装的 shared FFmpeg 对 Demucs 子进程可见。"""
    environment = os.environ.copy()
    if shutil.which("ffmpeg"):
        return environment

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return environment

    package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    candidates = sorted(package_root.glob("Gyan.FFmpeg.Shared_*/*/bin/ffmpeg.exe"), reverse=True)
    if candidates:
        ffmpeg_bin = str(candidates[0].parent)
        environment["PATH"] = f"{ffmpeg_bin}{os.pathsep}{environment.get('PATH', '')}"
    return environment


def separate_harmonic_sources(input_path: Path) -> Tuple[Optional[Path], Optional[str]]:
    """尝试用 Demucs 分离音源，并把 bass + other 合成为分析轨。"""
    if not _demucs_available():
        return None, "未检测到 Demucs，已自动回退到快速模式。"

    output_root = Path(tempfile.mkdtemp(prefix="chordpilot_demucs_"))
    try:
        subprocess.run(
            [sys.executable, "-m", "demucs", "-o", str(output_root), str(input_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
            env=_demucs_environment(),
        )

        model_dirs = [path for path in output_root.iterdir() if path.is_dir()]
        if not model_dirs:
            raise RuntimeError("Demucs 未生成输出目录")
        song_dirs = [path for path in model_dirs[0].iterdir() if path.is_dir()]
        if not song_dirs:
            raise RuntimeError("Demucs 未生成分轨文件")

        song_dir = song_dirs[0]
        bass_path = song_dir / "bass.wav"
        other_path = song_dir / "other.wav"
        if not bass_path.exists() or not other_path.exists():
            raise RuntimeError("Demucs 输出中缺少 bass 或 other 分轨")

        bass, sr = librosa.load(str(bass_path), sr=None, mono=True)
        other, other_sr = librosa.load(str(other_path), sr=sr, mono=True)
        if other_sr != sr:
            raise RuntimeError("Demucs 分轨采样率不一致")

        length = min(len(bass), len(other))
        audio = bass[:length] + other[:length]
        peak = float(np.max(np.abs(audio))) if audio.size else 0
        if peak > 0:
            audio = audio / peak
        analysis_path = output_root / "analysis_mix.wav"
        sf.write(str(analysis_path), audio, sr)
        return analysis_path, None
    except subprocess.CalledProcessError as error:
        shutil.rmtree(output_root, ignore_errors=True)
        detail = (error.stderr or error.stdout or str(error)).strip().splitlines()
        reason = detail[-1] if detail else str(error)
        return None, f"干净模式处理失败，已回退到快速模式：{reason}"
    except (subprocess.SubprocessError, OSError, RuntimeError) as error:
        shutil.rmtree(output_root, ignore_errors=True)
        return None, f"干净模式处理失败，已回退到快速模式：{error}"


def cleanup_separated_file(file_path: Optional[Path]) -> None:
    if file_path:
        shutil.rmtree(file_path.parent, ignore_errors=True)
