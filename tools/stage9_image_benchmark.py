"""Measure a representative single-image optimization pass.
Run: python tools/stage9_image_benchmark.py
"""
from __future__ import annotations

from io import BytesIO
import json
import resource
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from utils.image_optimizer import optimize_image


def main() -> None:
    buffer = BytesIO()
    image = Image.new("RGB", (3000, 3000), (120, 140, 160))
    image.save(buffer, format="PNG")
    image.close()
    source = buffer.getvalue()

    started = time.perf_counter()
    result = optimize_image(source, max_side=1280, max_pixels=16_000_000)
    elapsed = time.perf_counter() - started
    print(json.dumps({
        "input_dimensions": "3000x3000",
        "input_bytes": len(source),
        "output_bytes": len(result),
        "elapsed_seconds": round(elapsed, 4),
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "notes": "Single local Pillow optimization; process RSS includes Python and imported libraries.",
    }, indent=2))


if __name__ == "__main__":
    main()
