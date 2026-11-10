# Stage 06 — Media and memory safeguards

- Reduced default maximum Telegram image download size from 18 MB to 10 MB (still configurable).
- Reduced default decoded pixel ceiling from 16 MP to 10 MP (still configurable).
- Image optimizer now raises `ImageLimitError` for images exceeding the configured pixel/decompression-bomb ceiling instead of silently returning the original oversized payload to the AI provider.
- Corrupt/unsupported image bytes retain the compatibility fallback behavior.
- Existing JPEG draft decoding, bounded thumbnail output, transparency compositing, and explicit Pillow image cleanup are retained.
- No new dependencies; no database/schema changes; no changes to TXT/DOCX output behavior.

Validation: pending execution in the target environment. Live Telegram download and 512 MB host profiling are not claimed.
