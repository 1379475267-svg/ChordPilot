import asyncio
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from audio_loader import extract_harmonic_audio, load_audio
from chord_detector import detect_chords
from schemas import AnalysisResponse
from source_separator import cleanup_separated_file, separate_harmonic_sources

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".mp3", ".wav"}
MAX_FILE_SIZE = 50 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024
MAX_ANALYSIS_DURATION_SECONDS = 15 * 60
ANALYSIS_CONCURRENCY = 1
analysis_slots = asyncio.Semaphore(ANALYSIS_CONCURRENCY)

app = FastAPI(title="ChordPilot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


async def save_upload_limited(file: UploadFile, destination: Path) -> None:
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="文件不能超过 50 MB")
            output.write(chunk)


def analyze_file(
    input_path: Path, analysis_mode: str, chord_range: str
) -> Tuple[List[dict], float, Optional[str]]:
    separated_path = None
    warning = None
    try:
        analysis_path = input_path
        if analysis_mode == "clean":
            separated_path, warning = separate_harmonic_sources(input_path)
            if separated_path:
                analysis_path = separated_path

        audio, sample_rate = load_audio(
            analysis_path,
            max_duration=MAX_ANALYSIS_DURATION_SECONDS,
        )
        harmonic_audio = extract_harmonic_audio(audio)
        chords, duration = detect_chords(harmonic_audio, sample_rate, chord_range)
        return chords, duration, warning
    finally:
        cleanup_separated_file(separated_path)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    analysis_mode: str = Form("fast"),
    chord_range: str = Form("basic"),
) -> AnalysisResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 MP3 或 WAV 音频")
    if analysis_mode not in {"fast", "clean"}:
        raise HTTPException(status_code=400, detail="无效的分析模式")
    if chord_range not in {"basic", "extended"}:
        raise HTTPException(status_code=400, detail="无效的和弦范围")

    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"

    try:
        await save_upload_limited(file, upload_path)

        async with analysis_slots:
            chords, duration, warning = await run_in_threadpool(
                analyze_file, upload_path, analysis_mode, chord_range
            )

        return AnalysisResponse(
            filename=file.filename or upload_path.name,
            duration=round(duration, 2),
            analysis_mode=analysis_mode,
            chord_range=chord_range,
            chords=chords,
            warning=warning,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"音频分析失败：{error}") from error
    finally:
        await file.close()
        upload_path.unlink(missing_ok=True)
