# utils/image_optimizer.py
from __future__ import annotations

import io
import logging
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)


class ImageLimitError(ValueError):
    """Raised when an image exceeds configured safety limits."""


def optimize_image(
    image_bytes: bytes,
    max_side: int = 1280,
    max_pixels: int = 16_000_000,
) -> bytes:
    """Resize an image for AI processing while bounding decode dimensions.

    Pillow decodes lazily. We inspect dimensions before forcing a full decode,
    use JPEG draft decoding where supported, and close all temporary objects.
    On invalid/oversized input, retain the original bytes for compatibility.
    """
    if not image_bytes:
        return image_bytes

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as source:
                width, height = source.size
                if width <= 0 or height <= 0 or width * height > max_pixels:
                    raise ImageLimitError(
                        f"Image dimensions {width}x{height} exceed the configured limit of {max_pixels} pixels."
                    )

                # JPEG can decode directly at a reduced size, lowering peak RAM.
                if source.format == "JPEG" and max(width, height) > max_side:
                    source.draft("RGB", (max_side, max_side))

                # Avoid full-resolution copies on the common RGB/no-rotation path.
                # ImageOps.exif_transpose() copies even when no orientation tag exists,
                # so only create an oriented image when EXIF actually requires it.
                orientation = source.getexif().get(274)
                owns_oriented = orientation in (2, 3, 4, 5, 6, 7, 8)
                oriented = ImageOps.exif_transpose(source) if owns_oriented else source
                owns_converted = False
                try:
                    if oriented.mode in ("RGBA", "LA") or (
                        oriented.mode == "P" and "transparency" in oriented.info
                    ):
                        rgba = oriented.convert("RGBA")
                        try:
                            # Composite transparent pixels on white to preserve their
                            # intended appearance in the JPEG sent to the AI provider.
                            background = Image.new("RGB", rgba.size, (255, 255, 255))
                            try:
                                background.paste(rgba, mask=rgba.getchannel("A"))
                                converted = background.copy()
                                owns_converted = True
                            finally:
                                background.close()
                        finally:
                            rgba.close()
                    elif oriented.mode != "RGB":
                        converted = oriented.convert("RGB")
                        owns_converted = True
                    else:
                        # Safe to resize the decoded source in place: it is private to
                        # this call and is closed by Image.open's context manager.
                        converted = oriented

                    try:
                        converted.thumbnail(
                            (max_side, max_side),
                            Image.Resampling.LANCZOS,
                        )
                        output = io.BytesIO()
                        converted.save(output, format="JPEG", quality=85, optimize=True)
                        return output.getvalue()
                    finally:
                        if owns_converted:
                            converted.close()
                finally:
                    if owns_oriented:
                        oriented.close()
    except ImageLimitError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageLimitError("Image rejected by Pillow decompression-bomb protection.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("Image optimization failed, using original: %s", exc)
        return image_bytes
    except Exception as exc:
        logger.warning("Unexpected image optimization failure, using original: %s", exc)
        return image_bytes
