from io import BytesIO

from PIL import Image

from utils.image_optimizer import ImageLimitError, optimize_image


def _image_bytes(size: tuple[int, int], image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=image_format)
    return buffer.getvalue()


def test_large_image_is_resized_and_encoded_as_jpeg() -> None:
    result = optimize_image(_image_bytes((1800, 900)), max_side=1280)
    with Image.open(BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.size == (1280, 640)


def test_small_image_keeps_its_dimensions() -> None:
    result = optimize_image(_image_bytes((100, 80)))
    with Image.open(BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.size == (100, 80)


def test_pixel_limit_rejects_image_before_full_decode() -> None:
    original = _image_bytes((100, 100))
    import pytest
    with pytest.raises(ImageLimitError):
        optimize_image(original, max_pixels=5_000)


def test_empty_input_is_returned_unchanged() -> None:
    assert optimize_image(b"") == b""


def test_transparent_png_is_composited_on_white() -> None:
    source = BytesIO()
    image = Image.new("RGBA", (16, 16), (255, 0, 0, 0))
    image.putpixel((0, 0), (255, 0, 0, 255))
    image.save(source, format="PNG")
    image.close()

    result = optimize_image(source.getvalue())
    with Image.open(BytesIO(result)) as optimized:
        assert optimized.mode == "RGB"
        # JPEG is lossy, but transparent pixel should remain near white.
        r, g, b = optimized.getpixel((15, 15))
        assert r > 245 and g > 245 and b > 245


def test_corrupt_image_falls_back_without_crashing() -> None:
    assert optimize_image(b"not-an-image") == b"not-an-image"
