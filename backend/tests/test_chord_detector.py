import unittest

import librosa
import numpy as np

from audio_loader import extract_harmonic_audio
from chord_detector import BASIC_QUALITIES, EXTENDED_QUALITIES, ROOTS, build_templates, detect_chords

SAMPLE_RATE = 22050
NOTE_FREQUENCIES = {
    0: 261.63,
    1: 277.18,
    2: 293.66,
    3: 311.13,
    4: 329.63,
    5: 349.23,
    6: 369.99,
    7: 392.00,
    8: 415.30,
    9: 440.00,
    10: 466.16,
    11: 493.88,
}


def synthesize_chord(notes: list[int], duration: float = 2.0) -> np.ndarray:
    time = np.arange(int(SAMPLE_RATE * duration)) / SAMPLE_RATE
    envelope = np.minimum(1, time * 8) * np.minimum(1, (duration - time) * 8)
    signal = np.zeros_like(time)
    for note in notes:
        frequency = NOTE_FREQUENCIES[note % 12]
        signal += np.sin(2 * np.pi * frequency * time)
        signal += 0.25 * np.sin(2 * np.pi * frequency * 2 * time)
    # 加入低八度根音，模拟真实编曲中的贝斯声部。
    root_frequency = NOTE_FREQUENCIES[notes[0] % 12] / 2
    signal += 0.65 * np.sin(2 * np.pi * root_frequency * time)
    return (signal / (len(notes) * 1.25) * envelope).astype(np.float32)


class ChordDetectorTests(unittest.TestCase):
    def test_template_counts_and_normalization(self) -> None:
        basic = build_templates(BASIC_QUALITIES)
        extended = build_templates(EXTENDED_QUALITIES)

        self.assertEqual(len(basic), len(ROOTS) * 2)
        self.assertEqual(len(extended), len(ROOTS) * 15)
        for template in extended.values():
            self.assertAlmostEqual(float(np.linalg.norm(template)), 1.0, places=5)

    def test_c_g_am_f_progression(self) -> None:
        progression = np.concatenate(
            [
                synthesize_chord([0, 4, 7]),
                synthesize_chord([7, 11, 2]),
                synthesize_chord([9, 0, 4]),
                synthesize_chord([5, 9, 0]),
            ]
        )
        chords, duration = detect_chords(
            extract_harmonic_audio(progression),
            SAMPLE_RATE,
            chord_range="basic",
        )

        self.assertAlmostEqual(duration, 8.0, places=1)
        self.assertEqual([segment["chord"] for segment in chords], ["C", "G", "Am", "F"])
        self.assertTrue(all(segment["confidence"] >= 0.85 for segment in chords))

    def test_extended_chord_detection(self) -> None:
        c_major_seven = synthesize_chord([0, 4, 7, 11])
        chords, _ = detect_chords(
            extract_harmonic_audio(c_major_seven),
            SAMPLE_RATE,
            chord_range="extended",
        )

        self.assertEqual(chords[0]["chord"], "Cmaj7")
        self.assertGreaterEqual(chords[0]["confidence"], 0.75)

    def test_detuned_noisy_audio_stays_on_chord(self) -> None:
        audio = synthesize_chord([2, 6, 9], duration=3.5)
        audio = librosa.effects.pitch_shift(audio, sr=SAMPLE_RATE, n_steps=0.24)
        noise = np.random.default_rng(7).standard_normal(audio.size).astype(np.float32)
        audio = audio + noise * 0.012

        chords, _ = detect_chords(
            extract_harmonic_audio(audio),
            SAMPLE_RATE,
            chord_range="basic",
        )

        self.assertEqual(chords[0]["chord"], "D")
        self.assertGreaterEqual(chords[0]["confidence"], 0.65)


if __name__ == "__main__":
    unittest.main()
