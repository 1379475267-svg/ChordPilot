from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import librosa
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, sosfiltfilt

ROOTS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

CHORD_INTERVALS: Dict[str, Sequence[int]] = {
    "": (0, 4, 7),
    "m": (0, 3, 7),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "6": (0, 4, 7, 9),
    "m6": (0, 3, 7, 9),
    "m7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9),
    "add9": (0, 2, 4, 7),
    "5": (0, 7),
}

BASIC_QUALITIES = ("", "m")
EXTENDED_QUALITIES = tuple(CHORD_INTERVALS.keys())

SIMPLIFIED_QUALITY = {
    "7": "",
    "maj7": "",
    "m7": "m",
    "dim": "m",
    "aug": "",
    "sus2": "",
    "sus4": "",
    "6": "",
    "m6": "m",
    "m7b5": "m",
    "dim7": "m",
    "add9": "",
    "5": "",
}

MAJOR_KEY_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=np.float32,
)
MINOR_KEY_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=np.float32,
)


@dataclass(frozen=True)
class ChordMatch:
    name: str
    confidence: float


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def _parse_chord(name: str) -> Tuple[int, str]:
    root_name = next(root for root in reversed(ROOTS) if name.startswith(root))
    return ROOTS.index(root_name), name[len(root_name):]


def build_templates(qualities: Iterable[str]) -> Dict[str, np.ndarray]:
    """构造 12 维和弦模板，根音和三音略微加权。"""
    templates: Dict[str, np.ndarray] = {}
    for root_index, root_name in enumerate(ROOTS):
        for quality in qualities:
            vector = np.zeros(12, dtype=np.float32)
            intervals = CHORD_INTERVALS[quality]
            for interval in intervals:
                vector[(root_index + interval) % 12] = 1.0
            vector[root_index] = 1.24
            if len(intervals) >= 3:
                vector[(root_index + intervals[1]) % 12] = 1.08
            templates[f"{root_name}{quality}"] = _normalize(vector)
    return templates


def _estimate_key(chroma: np.ndarray) -> Tuple[int, str, float]:
    average = _normalize(np.mean(chroma, axis=1))
    candidates: List[Tuple[float, int, str]] = []
    for root in range(12):
        candidates.append((float(np.dot(average, _normalize(np.roll(MAJOR_KEY_PROFILE, root)))), root, "major"))
        candidates.append((float(np.dot(average, _normalize(np.roll(MINOR_KEY_PROFILE, root)))), root, "minor"))
    best, second = sorted(candidates, reverse=True)[:2]
    return best[1], best[2], float(np.clip(best[0] - second[0] + 0.55, 0, 1))


def _key_chord_roots(key_root: int, mode: str) -> set[int]:
    intervals = (0, 2, 4, 5, 7, 9, 11) if mode == "major" else (0, 2, 3, 5, 7, 8, 10)
    return {(key_root + interval) % 12 for interval in intervals}


def _low_pass(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    if audio.size < 64:
        return audio
    sos = butter(5, 245, btype="lowpass", fs=sample_rate, output="sos")
    return sosfiltfilt(sos, audio).astype(np.float32)


def _extract_chroma(audio: np.ndarray, sample_rate: int, hop_length: int) -> Tuple[np.ndarray, np.ndarray]:
    tuning = float(librosa.estimate_tuning(y=audio, sr=sample_rate, bins_per_octave=36))
    try:
        treble = librosa.feature.chroma_cqt(
            y=audio,
            sr=sample_rate,
            hop_length=hop_length,
            bins_per_octave=36,
            tuning=tuning,
            norm=2,
            threshold=0.0,
        )
        bass = librosa.feature.chroma_cqt(
            y=_low_pass(audio, sample_rate),
            sr=sample_rate,
            hop_length=hop_length,
            bins_per_octave=36,
            tuning=tuning,
            norm=2,
            threshold=0.0,
        )
    except (ValueError, librosa.util.exceptions.ParameterError):
        treble = librosa.feature.chroma_stft(
            y=audio, sr=sample_rate, hop_length=hop_length, n_fft=4096, tuning=tuning, norm=2
        )
        bass = librosa.feature.chroma_stft(
            y=_low_pass(audio, sample_rate),
            sr=sample_rate,
            hop_length=hop_length,
            n_fft=4096,
            tuning=tuning,
            norm=2,
        )

    frame_count = min(treble.shape[1], bass.shape[1])
    treble = np.nan_to_num(treble[:, :frame_count])
    bass = np.nan_to_num(bass[:, :frame_count])

    # 运行均值标准化近似 Chordino 的频谱白化，减少长期音色偏置。
    running_mean = gaussian_filter1d(treble, sigma=18, axis=1, mode="nearest")
    whitened = np.maximum(treble - 0.55 * running_mean, 0)
    whitened = gaussian_filter1d(whitened, sigma=1.1, axis=1, mode="nearest")
    bass = gaussian_filter1d(bass, sigma=1.0, axis=1, mode="nearest")
    return whitened, bass


def _window_boundaries(
    audio: np.ndarray,
    sample_rate: int,
    hop_length: int,
    frame_count: int,
    window_seconds: float,
) -> List[int]:
    """优先按节拍聚合；节拍不可靠时回退到固定时间窗。"""
    try:
        tempo, beats = librosa.beat.beat_track(y=audio, sr=sample_rate, hop_length=hop_length, trim=False)
        tempo_value = float(np.asarray(tempo).reshape(-1)[0])
        beats = np.unique(np.clip(beats, 0, frame_count))
        if 45 <= tempo_value <= 210 and len(beats) >= 5:
            median_gap = float(np.median(np.diff(beats))) * hop_length / sample_rate
            # 以 1–2 拍为单位保留和弦变化，再交给 Viterbi 合并稳定片段。
            group_size = min(2, max(1, int(round(window_seconds / max(median_gap, 0.2)))))
            selected = beats[::group_size].tolist()
            raw_boundaries = sorted(set(int(value) for value in [0, *selected, frame_count]))
            minimum_gap = max(4, int(0.28 * sample_rate / hop_length))
            boundaries = [raw_boundaries[0]]
            for value in raw_boundaries[1:-1]:
                if value - boundaries[-1] >= minimum_gap:
                    boundaries.append(value)
            if frame_count - boundaries[-1] < minimum_gap and len(boundaries) > 1:
                boundaries[-1] = frame_count
            else:
                boundaries.append(frame_count)
            return boundaries
    except (ValueError, librosa.util.exceptions.ParameterError):
        pass

    frames_per_window = max(1, int(round(window_seconds * sample_rate / hop_length)))
    boundaries = list(range(0, frame_count, frames_per_window))
    if boundaries and frame_count - boundaries[-1] < frames_per_window * 0.35:
        boundaries[-1] = frame_count
    else:
        boundaries.append(frame_count)
    return boundaries


def _emission_scores(
    chroma_vector: np.ndarray,
    bass_vector: np.ndarray,
    names: List[str],
    template_matrix: np.ndarray,
    key_roots: set[int],
    key_strength: float,
) -> np.ndarray:
    normalized = _normalize(np.maximum(chroma_vector, 0))
    normalized_bass = _normalize(np.maximum(bass_vector, 0))
    if not np.any(normalized):
        return np.full(len(names), 1e-6, dtype=np.float32)

    scores = template_matrix @ normalized
    for index, name in enumerate(names):
        root, quality = _parse_chord(name)
        root_energy = normalized[root]
        bass_root = normalized_bass[root]
        scores[index] += 0.10 * root_energy + 0.62 * bass_root
        if root in key_roots:
            scores[index] += 0.045 * key_strength
        if quality in {"dim7", "aug", "m7b5"}:
            scores[index] -= 0.025
    return np.clip(scores, 1e-6, None)


def _transition_matrix(names: List[str]) -> np.ndarray:
    count = len(names)
    matrix = np.full((count, count), -0.012, dtype=np.float32)
    parsed = [_parse_chord(name) for name in names]
    for previous in range(count):
        prev_root, prev_quality = parsed[previous]
        for current in range(count):
            root, quality = parsed[current]
            if previous == current:
                matrix[previous, current] = 0.0
            elif prev_root == root:
                matrix[previous, current] = -0.005
            elif (root - prev_root) % 12 in {5, 7}:
                matrix[previous, current] = -0.008
            elif prev_quality == quality:
                matrix[previous, current] = -0.01
    return matrix


def _viterbi(emissions: np.ndarray, transitions: np.ndarray) -> List[int]:
    time_steps, states = emissions.shape
    log_emissions = np.log(np.clip(emissions, 1e-7, None))
    scores = np.empty((time_steps, states), dtype=np.float32)
    paths = np.zeros((time_steps, states), dtype=np.int32)
    scores[0] = log_emissions[0]

    for time_index in range(1, time_steps):
        candidates = scores[time_index - 1][:, None] + transitions
        paths[time_index] = np.argmax(candidates, axis=0)
        scores[time_index] = candidates[paths[time_index], np.arange(states)] + log_emissions[time_index]

    sequence = [int(np.argmax(scores[-1]))]
    for time_index in range(time_steps - 1, 0, -1):
        sequence.append(int(paths[time_index, sequence[-1]]))
    return list(reversed(sequence))


def _simplify_extended(name: str, confidence: float, basic_scores: Dict[str, float]) -> ChordMatch:
    root, quality = _parse_chord(name)
    root_name = ROOTS[root]
    fallback_name = f"{root_name}{SIMPLIFIED_QUALITY.get(quality, quality)}"
    fallback_confidence = float(np.clip(basic_scores.get(fallback_name, 0) * 0.92, 0, 1))
    if confidence < 0.57 and fallback_confidence >= 0.48:
        return ChordMatch(fallback_name, fallback_confidence)
    if confidence < 0.42:
        return ChordMatch("Unknown", confidence)
    return ChordMatch(name, confidence)


def _merge_windows(
    matches: List[ChordMatch],
    boundaries: List[int],
    hop_length: int,
    sample_rate: int,
    duration: float,
) -> List[dict]:
    if not matches:
        return []

    segments: List[dict] = []
    start_index = 0
    for index in range(1, len(matches) + 1):
        boundary = index == len(matches) or matches[index].name != matches[start_index].name
        if not boundary:
            continue
        confidences = [match.confidence for match in matches[start_index:index]]
        start_seconds = boundaries[start_index] * hop_length / sample_rate
        end_seconds = boundaries[index] * hop_length / sample_rate
        segments.append(
            {
                "start": round(start_seconds, 2),
                "end": round(min(end_seconds, duration), 2),
                "chord": matches[start_index].name,
                "confidence": round(float(np.mean(confidences)), 2),
            }
        )
        start_index = index
    return segments


def detect_chords(
    audio: np.ndarray,
    sample_rate: int,
    chord_range: str = "basic",
    window_seconds: float = 2.0,
) -> Tuple[List[dict], float]:
    duration = float(librosa.get_duration(y=audio, sr=sample_rate))
    if duration <= 0:
        return [], 0.0

    hop_length = 512
    chroma, bass_chroma = _extract_chroma(audio, sample_rate, hop_length)
    if chroma.size == 0 or not np.any(chroma):
        return [{"start": 0.0, "end": round(duration, 2), "chord": "Unknown", "confidence": 0.0}], duration

    boundaries = _window_boundaries(
        audio, sample_rate, hop_length, chroma.shape[1], window_seconds
    )
    if len(boundaries) < 2:
        boundaries = [0, chroma.shape[1]]

    qualities = BASIC_QUALITIES if chord_range == "basic" else EXTENDED_QUALITIES
    templates = build_templates(qualities)
    basic_templates = build_templates(BASIC_QUALITIES)
    names = list(templates.keys())
    template_matrix = np.stack([templates[name] for name in names])
    key_root, key_mode, key_strength = _estimate_key(chroma)
    key_roots = _key_chord_roots(key_root, key_mode)

    emissions: List[np.ndarray] = []
    basic_score_windows: List[Dict[str, float]] = []
    for start_frame, end_frame in zip(boundaries[:-1], boundaries[1:]):
        window = chroma[:, start_frame:end_frame]
        bass_window = bass_chroma[:, start_frame:end_frame]
        if window.shape[1] == 0:
            continue
        energy = np.sum(window, axis=0)
        threshold = np.percentile(energy, 20)
        active = energy > threshold
        window_chroma = np.median(window[:, active], axis=1) if np.any(active) else np.median(window, axis=1)
        window_bass = (
            np.median(bass_window[:, active], axis=1)
            if np.any(active)
            else np.median(bass_window, axis=1)
        )
        emissions.append(
            _emission_scores(
                window_chroma,
                window_bass,
                names,
                template_matrix,
                key_roots,
                key_strength,
            )
        )
        normalized = _normalize(np.maximum(window_chroma, 0))
        basic_score_windows.append(
            {name: float(np.dot(normalized, template)) for name, template in basic_templates.items()}
        )

    if not emissions:
        return [{"start": 0.0, "end": round(duration, 2), "chord": "Unknown", "confidence": 0.0}], duration

    emission_matrix = np.stack(emissions)
    sequence = _viterbi(emission_matrix, _transition_matrix(names))
    matches: List[ChordMatch] = []
    for index, state in enumerate(sequence):
        row = emission_matrix[index]
        sorted_scores = np.sort(row)
        best_score = float(row[state])
        margin = best_score - float(sorted_scores[-2]) if len(row) > 1 else best_score
        confidence = float(np.clip((best_score / 1.7) * 0.72 + margin * 0.95, 0, 1))
        match = ChordMatch(names[state], confidence)
        if chord_range == "extended":
            match = _simplify_extended(match.name, match.confidence, basic_score_windows[index])
        elif match.confidence < 0.39:
            match = ChordMatch("Unknown", match.confidence)
        matches.append(match)

    return _merge_windows(matches, boundaries, hop_length, sample_rate, duration), duration
