import asyncio
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import HTTPException

import main
from audio_loader import load_audio


class ChunkedUpload:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = iter(chunks)

    async def read(self, _size: int) -> bytes:
        return next(self.chunks, b"")


class UploadLimitTests(unittest.TestCase):
    def test_upload_stops_before_writing_a_chunk_that_exceeds_limit(self) -> None:
        original_limit = main.MAX_FILE_SIZE
        main.MAX_FILE_SIZE = 3
        try:
            with tempfile.TemporaryDirectory() as temporary_directory:
                destination = Path(temporary_directory) / "upload.wav"
                with self.assertRaises(HTTPException) as context:
                    asyncio.run(main.save_upload_limited(ChunkedUpload([b"abc", b"d"]), destination))

                self.assertEqual(context.exception.status_code, 413)
                self.assertEqual(destination.read_bytes(), b"abc")
        finally:
            main.MAX_FILE_SIZE = original_limit

    def test_audio_loader_rejects_audio_beyond_duration_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            audio_path = Path(temporary_directory) / "long.wav"
            sf.write(audio_path, np.zeros(22050, dtype=np.float32), 22050)

            with self.assertRaises(ValueError):
                load_audio(audio_path, max_duration=0.5)


if __name__ == "__main__":
    unittest.main()
