"""Browser viewport video recorder producing genuine playable MP4 recordings."""

import io
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import imageio.v2 as imageio
import numpy as np
from PIL import Image
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from automation.config import RECORDINGS_DIR
from automation.utils.logger import get_logger

logger = get_logger("payflow.recorder")


class BrowserVideoRecorder:
    """Captures real browser frames via WebDriver and encodes an MP4 video with ffmpeg."""

    def __init__(self, driver: WebDriver, test_name: str, fps: int = 4) -> None:
        self.driver = driver
        safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in test_name)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.output_path: Path = RECORDINGS_DIR / f"{ts}_{safe}.mp4"
        self.fps = fps
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame_size: Optional[tuple[int, int]] = None
        self.frame_count = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        logger.info("Started video recording -> %s", self.output_path)

    def _record_loop(self) -> None:
        writer = None
        interval = 1.0 / max(1, self.fps)
        try:
            writer = imageio.get_writer(
                str(self.output_path),
                fps=self.fps,
                codec="libx264",
                pixelformat="yuv420p",
                macro_block_size=16,
            )
        except Exception as exc:
            logger.warning("Failed to initialize libx264 writer (%s), trying mpeg4 fallback", exc)
            try:
                writer = imageio.get_writer(str(self.output_path), fps=self.fps, codec="mpeg4")
            except Exception as exc2:
                logger.error("Video writer unavailable: %s", exc2)
                return

        try:
            while not self._stop_event.is_set():
                try:
                    png_bytes = self.driver.get_screenshot_as_png()
                    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                    # Ensure dimensions are multiples of 16 (required by libx264 macro_block_size=16)
                    w, h = img.size
                    if self._frame_size is None:
                        even_w = max(16, w - (w % 16))
                        even_h = max(16, h - (h % 16))
                        self._frame_size = (even_w, even_h)
                    if img.size != self._frame_size:
                        img = img.resize(self._frame_size, Image.Resampling.BILINEAR)
                    writer.append_data(np.asarray(img))
                    self.frame_count += 1
                except WebDriverException:
                    # Window might be transitioning across popups/redirects
                    pass
                except Exception as exc:
                    logger.debug("Frame capture skipped: %s", exc)
                self._stop_event.wait(interval)
        finally:
            if writer is not None:
                writer.close()

    def stop(self) -> Optional[Path]:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=8)
        if self.frame_count == 0 and self.output_path.exists():
            self.output_path.unlink(missing_ok=True)
            return None
        logger.info("Saved video recording (%d frames): %s", self.frame_count, self.output_path)
        return self.output_path if self.output_path.exists() else None
