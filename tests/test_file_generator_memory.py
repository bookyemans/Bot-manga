from systems.translation_pipeline.models.page_data import PageData
from utils.file_generator import FileGenerator


def test_txt_generator_returns_rewound_utf8_bytesio() -> None:
    result = FileGenerator.generate_txt(
        [PageData(file_name="page-1.png")],
        session_note="ملاحظة اختبار",
    )
    try:
        assert result.tell() == 0
        content = result.read().decode("utf-8")
        assert "ملاحظة اختبار" in content
        assert "page-1.png" in content
    finally:
        result.close()
