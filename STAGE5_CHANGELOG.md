# Stage 5 — Image & File Processing Optimization

## Implemented

- Added a configurable maximum image download size (`MANGA_BOT_IMAGE_MAX_DOWNLOAD_BYTES`, default 18 MB). The Telegram file metadata is checked before download when available, and the downloaded payload is checked again before processing.
- Reduced the default decoded-image pixel ceiling from 40 MP to 16 MP to better fit the 512 MB deployment target.
- Improved transparent PNG/palette image handling by compositing transparency onto white before JPEG encoding, avoiding black/incorrect transparent regions in AI input.
- Kept image decoding bounded by pixel checks, JPEG draft decoding, thumbnail resizing, and explicit closure of intermediate Pillow objects.
- Changed built-in TXT exporters to write UTF-8 directly into `BytesIO` through `TextIOWrapper`, avoiding the previous full-size intermediate Unicode string and second full-size encoded copy.
- Applied the TXT export memory change to the default, Nabil, and Panel personas.

## Configuration

- `MANGA_BOT_IMAGE_MAX_SIDE=1280`
- `MANGA_BOT_IMAGE_MAX_PIXELS=16000000`
- `MANGA_BOT_IMAGE_MAX_DOWNLOAD_BYTES=18000000`

All settings can be adjusted in `.env` without changing source code.

## Verification

- `python -m compileall -q .` — passed.
- `pytest -q` — 17 passed.
- Image tests cover resize, dimension preservation, pixel-limit behavior, empty input, and transparent PNG compositing.
- TXT export test verifies UTF-8 output and stream position.
- No live Telegram download, Gemini request, or 512 MB host stress test was performed.
