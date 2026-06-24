# ChordPilot

<p align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

ChordPilot is a local music-tech web app that turns MP3 or WAV audio into a chord timeline. It extracts chroma features, matches them against chord templates, and produces a practical draft for learning, practice, and music transcription.

> The goal of v0.1 is to generate a useful chord draft—not to replace careful listening or professional notation.

## Interface Preview

### Music Studio Home and Player

![ChordPilot home and audio player](docs/images/chordpilot-hero.png)

### Playback-Synced Chord Timeline

![ChordPilot chord timeline](docs/images/chordpilot-timeline.png)

### Upload, Analysis, and Loading State

![ChordPilot upload and analysis interface](docs/images/chordpilot-analysis.png)

### Copy and Export Chord Progressions

![ChordPilot export panel](docs/images/chordpilot-export.png)

## Features

- Upload `.mp3` and `.wav` audio files up to 50 MB
- Fast mode for direct harmonic analysis
- Clean mode with optional Demucs separation and graceful fallback
- Basic chords: major and minor triads for all 12 roots
- Extended chords: 7, maj7, m7, dim, aug, sus2, sus4, 6, m6, m7b5, dim7, add9, and power chords
- HTML5 audio playback
- A horizontal chord timeline that follows playback, highlights the active chord, and supports click-to-seek
- PrimeVue analysis detail table
- Copy chord progressions and export TXT or JSON

## Tech Stack

- Frontend: Vue 3, Vite, PrimeVue, PrimeIcons, Phosphor Icons, Clipboard API
- Backend: Python, FastAPI, Uvicorn, librosa, NumPy, SciPy
- Optional: FFmpeg and Demucs

## Project Structure

```text
ChordPilot/
├── frontend/
│   ├── src/components/
│   ├── src/App.vue
│   ├── src/main.js
│   └── package.json
├── backend/
│   ├── main.py
│   ├── audio_loader.py
│   ├── chord_detector.py
│   ├── source_separator.py
│   ├── schemas.py
│   └── requirements.txt
├── README.md
└── README_EN.md
```

## Run the Backend

Python 3.9–3.12 is recommended.

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/api/health`. It should return:

```json
{"status":"ok"}
```

## Run the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`.

Vite proxies `/api` requests to `http://localhost:8000`, and the backend also permits local CORS requests from port 5173.

## One-Click Start on Windows

After installing dependencies once, run this command from the project root:

```powershell
.\start.ps1
```

The script launches both services and opens `http://localhost:5173`. Upload audio after the status indicator says that the analysis service is connected.

## Audio Dependencies

WAV and common MP3 files can normally be read directly through `soundfile`. The project also includes `imageio-ffmpeg` as a portable decoding fallback, so Fast mode does not require a system FFmpeg installation.

For Demucs on Windows, install a shared FFmpeg build:

```powershell
winget install --id Gyan.FFmpeg.Shared --exact
ffmpeg -version
```

Restart the terminal and backend after installation.

## Demucs Clean Mode

Demucs is **optional**. Fast mode works without it, and Clean mode automatically falls back to Fast mode with a warning when separation is unavailable.

Install the optional dependencies with:

```powershell
python -m pip install -r requirements-clean.txt
```

Demucs requires shared FFmpeg and may download a model on first use. It is substantially slower than Fast mode. ChordPilot performs four-stem separation, combines `bass + other` for analysis, and removes temporary files after each request.

## Tests

Run the backend regression tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

Run the frontend timeline tests:

```powershell
cd frontend
npm test
```

## Algorithm Overview

1. Convert audio to mono and resample it to 22050 Hz
2. Normalize amplitude and extract harmonic content
3. Estimate tuning offset and calculate 12-bin CQT chroma
4. Reduce timbral, melodic, and noise bias with running-mean whitening and neighborhood filtering
5. Extract additional low-frequency chroma to strengthen bass-root estimation
6. Prefer beat-synchronous aggregation, with fixed windows as a fallback
7. Compare normalized chroma against manually constructed chord templates
8. Estimate the global key and apply a lightweight in-key prior
9. Decode the temporal sequence with HMM/Viterbi smoothing
10. Simplify uncertain extended chords to major or minor triads, then return `Unknown` when confidence remains too low

The design is informed by Chordino / NNLS Chroma, Essentia, and established automatic chord estimation pipelines. ChordPilot uses its own lightweight Python implementation and does not copy their source code or require them at runtime.

Related open-source projects:

- [Chordino / NNLS Chroma](https://github.com/c4dm/nnls-chroma)
- [Essentia](https://github.com/MTG/essentia)
- [librosa](https://github.com/librosa/librosa)

The interface uses open-source [Phosphor Icons](https://github.com/phosphor-icons/core). Its record artwork, textures, and decorative graphics are generated locally with SVG and CSS.

## Current Limitations

- Dense arrangements, strong percussion, chord inversions, and tuning drift can reduce accuracy
- Beat estimation can be unstable for some songs, and the timeline is not yet grouped into measures
- Chroma templates cannot reliably distinguish every advanced chord in context
- No login, database, or cloud storage
- v0.1 does not display piano notation or guitar tablature

## Roadmap

- v0.1 Upload audio and generate a chord timeline
- v0.2 Add beat detection and measure segmentation
- v0.3 Integrate Basic Pitch for audio-to-MIDI conversion
- v0.4 Add a piano-roll view
- v0.5 Generate simplified piano staff notation
- v0.6 Generate simplified guitar tablature
- v1.0 Support manual correction and MIDI / MusicXML / TXT export
