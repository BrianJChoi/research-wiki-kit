"""paper_ocr.py: 글자 층, 쪽 고르기, 회전, 엔진 전환, 원본 보호.

엔진이 필요 없는 시험은 read_as_ocr의 가짜 결과를 쓴다. 실제 엔진 시험은 RealEngineTest뿐이다.
"""

import json
import os
import platform
import random
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import helpers
import pymupdf
from helpers import (
    LEFT,
    TOP,
    PdfCase,
    call_main,
    image_pdf,
    last_json,
    load_script,
    mean_difference,
    page_text,
    read_as_ocr,
    rendered,
    rows,
    run_cli,
    sha256,
    text_pdf,
)

LINES = ["한글 시험 문장입니다", "Second line of generated text"]
LONG_LINES = ["생성형 인공지능을 활용한 수업 사례를 살펴본 시험용 문장입니다."] * 4
FAKE_RAPIDOCR = """\
from rapidocr.utils.download_file import DownloadFileException


class LangRec:
    KOREAN = "korean"


class ModelType:
    MOBILE = "mobile"


class OCRVersion:
    PPOCRV5 = "PP-OCRv5"


class RapidOCR:
    def __init__(self, params=None):
        pass

    def __call__(self, path):
        raise DownloadFileException("Failed to download korean_PP-OCRv5_rec_mobile.onnx")
"""


class OcrCase(PdfCase):
    def setUp(self):
        super().setUp()
        self.ocr = load_script("paper_ocr")
        self.source = text_pdf(self.dir / "source.pdf", [rows(LINES)])
        self.image = image_pdf(self.source, self.dir / "scan.pdf")

    def fake_ocr(self, path: Path, *args, pages: list | None = None) -> tuple[int, dict]:
        """OCR 엔진 자리에 정답을 넣고 나머지 과정을 그대로 돌린다."""
        answer = pages if pages is not None else read_as_ocr(self.source)
        with mock.patch.object(self.ocr, "ocr_vision", return_value=answer), mock.patch.object(
            self.ocr, "ocr_rapid", return_value=answer
        ):
            code, out = call_main(self.ocr, path, "--engine", "rapidocr", *args)
        return code, json.loads(out.strip().splitlines()[-1])


class TextLayerTest(OcrCase):
    def test_text_becomes_searchable(self):
        code, summary = self.fake_ocr(self.image)
        self.assertEqual(code, 0)
        self.assertEqual(summary["status"], "done")
        self.assertEqual(summary["ocr_pages"], 1)
        self.assertEqual(summary["pages"], 1)
        output = Path(summary["output"])
        self.assertEqual(output.name, "scan_ocr.pdf")
        text = page_text(output)
        for line in LINES:
            self.assertIn(line, text)
        self.assertEqual(summary["chars"], len(text.strip()))

    def test_page_looks_the_same(self):
        _, summary = self.fake_ocr(self.image)
        self.assertEqual(rendered(self.image), rendered(Path(summary["output"])))

    def test_words_sit_where_they_are_seen(self):
        _, summary = self.fake_ocr(self.image)
        with pymupdf.open(self.source) as doc:
            expected = doc[0].search_for("Second line")[0]
        with pymupdf.open(summary["output"]) as doc:
            actual = doc[0].search_for("Second line")[0]
        self.assertAlmostEqual(actual.x0, expected.x0, delta=2)
        self.assertAlmostEqual(actual.x1, expected.x1, delta=4)
        self.assertAlmostEqual((actual.y0 + actual.y1) / 2, (expected.y0 + expected.y1) / 2, delta=3)

    def test_font_is_embedded_in_the_copy(self):
        _, summary = self.fake_ocr(self.image)
        with pymupdf.open(summary["output"]) as doc:
            fonts = doc[0].get_fonts()
        self.assertTrue(fonts)
        self.assertTrue(all(font[1] != "n/a" for font in fonts), fonts)

    def test_only_pages_without_text_get_a_layer(self):
        typed = rows(LONG_LINES)
        mixed = text_pdf(self.dir / "mixed.pdf", [typed, []])
        with pymupdf.open(mixed) as doc:
            with pymupdf.open(self.image) as scan:
                doc.insert_pdf(scan)
            doc.delete_page(1)
            doc.saveIncr()
        code, summary = self.fake_ocr(mixed)
        self.assertEqual(code, 0)
        self.assertEqual(summary["ocr_pages"], 1)
        self.assertEqual(summary["pages"], 2)
        self.assertEqual(page_text(Path(summary["output"]), 0), page_text(mixed, 0))
        self.assertIn(LINES[0], page_text(Path(summary["output"]), 1))

    def test_blank_page_is_kept(self):
        blank = text_pdf(self.dir / "blank.pdf", [[]])
        code, summary = self.fake_ocr(blank, pages=[[]])
        self.assertEqual(code, 0)
        self.assertEqual(summary["chars"], 0)
        self.assertEqual(summary["pages"], 1)


class RotationTest(OcrCase):
    def test_rotated_scan_keeps_look_and_text_position(self):
        sideways = image_pdf(self.source, self.dir / "sideways.pdf", sideways=True)
        with pymupdf.open(sideways) as doc:
            self.assertEqual(doc[0].rotation, 90)
        code, summary = self.fake_ocr(sideways)
        self.assertEqual(code, 0)
        with pymupdf.open(summary["output"]) as doc:
            self.assertEqual(doc[0].rotation, 0)
            actual = doc[0].search_for("Second line")[0]
        with pymupdf.open(self.source) as doc:
            expected = doc[0].search_for("Second line")[0]
        self.assertAlmostEqual(actual.x0, expected.x0, delta=2)
        self.assertAlmostEqual(actual.y0, expected.y0, delta=4)
        self.assertLess(mean_difference(rendered(sideways), rendered(Path(summary["output"]))), 2)


def column(x: float, y: float, label: str, count: int) -> list[tuple]:
    return [(x, y + index * LINE_GAP_LAYOUT, f"{label} {index + 1}번째 줄입니다") for index in range(count)]


LINE_GAP_LAYOUT = 15
TITLE = "생성형 인공지능의 교육적 활용에 관한 시험용 논문 제목을 길게 적은 줄입니다"
ABSTRACT = "초록 문장은 두 단을 가로질러 한 줄로 길게 이어지는 경우가 많아서 따로 확인합니다"
CAPTION = "그림 일 설명은 본문 가운데에서 두 단을 가로지르는 줄로 들어가는 경우를 봅니다"


class LayoutTest(OcrCase):
    """엔진이 어떤 순서로 줄을 돌려주든 글자 층은 사람이 읽는 순서로 들어가야 한다.

    Zotero에서 왼쪽 단을 끌어 하이라이트할 때 오른쪽 단이 섞이지 않으려면 글자 층 순서가 단 순서여야 한다.
    RapidOCR는 줄을 위에서 아래로만 정렬해서 2단의 좌우 줄을 번갈아 돌려준다.
    """

    def layout(self, lines: list[tuple]) -> tuple[Path, list[dict]]:
        source = text_pdf(self.dir / "layout.pdf", [lines])
        image = image_pdf(source, self.dir / "layout_scan.pdf")
        return image, read_as_ocr(source)[0]

    def stream_order(self, path: Path) -> list[str]:
        with pymupdf.open(path) as doc:
            blocks = doc[0].get_text("dict", sort=False)["blocks"]
        return ["".join(span["text"] for span in line["spans"]).strip() for block in blocks for line in block.get("lines", [])]

    def assert_order(self, lines: list[tuple], expected: list[str]) -> None:
        image, answer = self.layout(lines)
        rapid_style = sorted(answer, key=lambda line: (round(line["y0"], 2), line["x0"]))
        shuffled = list(answer)
        random.Random(7).shuffle(shuffled)
        for name, given in (("RapidOCR식 위아래 정렬", rapid_style), ("뒤섞인 순서", shuffled)):
            with self.subTest(engine_order=name):
                code, summary = self.fake_ocr(image, "--force", pages=[given])
                self.assertEqual(code, 0)
                self.assertEqual(self.stream_order(Path(summary["output"])), expected)

    def test_two_columns_read_left_column_first(self):
        left = column(60, 120, "왼쪽 단", 8)
        right = column(320, 120, "오른쪽 단", 8)
        self.assert_order(left + right, [text for _, _, text in left + right])

    def test_title_and_abstract_span_above_two_columns(self):
        top = [(60, 80, TITLE), (60, 98, ABSTRACT)]
        left = column(60, 140, "왼쪽 단", 6)
        right = column(320, 140, "오른쪽 단", 6)
        self.assert_order(top + right + left, [text for _, _, text in top + left + right])

    def test_full_width_line_between_two_column_blocks(self):
        upper_left, upper_right = column(60, 100, "위 왼쪽", 5), column(320, 100, "위 오른쪽", 5)
        caption = [(60, 200, CAPTION)]
        lower_left, lower_right = column(60, 240, "아래 왼쪽", 5), column(320, 240, "아래 오른쪽", 5)
        expected = upper_left + upper_right + caption + lower_left + lower_right
        self.assert_order(lower_right + caption + upper_right + lower_left + upper_left, [text for _, _, text in expected])

    def test_three_columns(self):
        columns = [column(x, 120, f"{name} 단", 6) for x, name in ((40, "첫째"), (225, "둘째"), (410, "셋째"))]
        lines = [line for group in columns for line in group]
        self.assert_order(lines, [text for _, _, text in lines])

    def test_single_column_stays_top_to_bottom(self):
        lines = [
            (LEFT, TOP, LONG_LINES[0]),
            (LEFT + 20, TOP + 16, "들여쓴 줄도 위에서 아래 순서를 지킵니다 길게 적어 둡니다"),
            (LEFT, TOP + 32, "짧은 줄"),
            (LEFT, TOP + 48, LONG_LINES[1]),
        ]
        self.assert_order(lines, [text for _, _, text in lines])

    def order_of(self, lines: list[dict]) -> list[str]:
        return [line["text"] for line in self.ocr.reading_order(lines)]

    def test_gutter_edge_on_a_bin_boundary_is_kept(self):
        """단 끝이 칸 경계와 소수점 끝자리까지 겹쳐도 빈 여백으로 본다 (리뷰어 재현값)."""
        for left_end in (0.46, 0.46 - 1e-5, 0.46 + 1e-5):
            with self.subTest(left_end=left_end):
                lines = []
                for row in range(3):
                    top = 0.2 + row * 0.03
                    lines.append({"text": f"L{row}", "x0": 0.1, "y0": top, "x1": left_end, "y1": top + 0.02})
                    lines.append({"text": f"R{row}", "x0": 0.54, "y0": top, "x1": 0.9, "y1": top + 0.02})
                self.assertEqual(self.order_of(lines), ["L0", "L1", "L2", "R0", "R1", "R2"])

    def test_blocks_that_are_not_side_by_side_are_not_columns(self):
        """오른쪽 위 짧은 제목과 왼쪽 아래 본문은 나란한 두 단이 아니므로 위에서 아래로 읽는다."""
        lines = [
            {"text": "본문 1", "x0": 0.1, "y0": 0.50, "x1": 0.45, "y1": 0.52},
            {"text": "본문 2", "x0": 0.1, "y0": 0.53, "x1": 0.45, "y1": 0.55},
            {"text": "제목", "x0": 0.55, "y0": 0.10, "x1": 0.9, "y1": 0.12},
        ]
        self.assertEqual(self.order_of(lines), ["제목", "본문 1", "본문 2"])

    def test_highlight_box_matches_the_seen_line(self):
        """하이라이트 띠는 글자 층의 줄 상자로 그려지므로 OCR이 본 줄 상자와 같아야 한다."""
        left = column(60, 120, "왼쪽 단", 3)
        image, answer = self.layout(left)
        code, summary = self.fake_ocr(image, "--force", pages=[answer])
        self.assertEqual(code, 0)
        with pymupdf.open(summary["output"]) as doc:
            page = doc[0]
            boxes = [line["bbox"] for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])]
            width, height = page.rect.width, page.rect.height
        self.assertEqual(len(boxes), len(answer))
        for seen, (x0, y0, x1, y1) in zip(sorted(answer, key=lambda line: line["y0"]), sorted(boxes, key=lambda box: box[1])):
            self.assertAlmostEqual(y0, seen["y0"] * height, delta=0.5)
            self.assertAlmostEqual(y1, seen["y1"] * height, delta=0.5)
            self.assertAlmostEqual(x0, seen["x0"] * width, delta=1)
            self.assertAlmostEqual(x1, seen["x1"] * width, delta=1)


class EngineTest(OcrCase):
    def test_vision_failure_falls_back_to_rapidocr(self):
        answer = read_as_ocr(self.source)
        broken = subprocess.CalledProcessError(1, "swift")
        with mock.patch.object(self.ocr, "ocr_vision", side_effect=broken), mock.patch.object(
            self.ocr, "ocr_rapid", return_value=answer
        ) as rapid:
            code, out = call_main(self.ocr, self.image, "--engine", "vision")
        self.assertEqual(code, 0)
        rapid.assert_called_once()
        self.assertEqual(json.loads(out)["engine"], "rapidocr")

    def test_vision_bad_output_falls_back_to_rapidocr(self):
        answer = read_as_ocr(self.source)
        done = subprocess.CompletedProcess([], 0, stdout="not json", stderr="")
        with mock.patch.object(self.ocr.subprocess, "run", return_value=done), mock.patch.object(
            self.ocr, "ocr_rapid", return_value=answer
        ):
            code, out = call_main(self.ocr, self.image, "--engine", "vision")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["engine"], "rapidocr")

    def test_auto_picks_engine_by_platform(self):
        answer = read_as_ocr(self.source)
        cases = (("Darwin", "/usr/bin/swift", "vision"), ("Darwin", None, "rapidocr"), ("Windows", None, "rapidocr"))
        for system, swift, expected in cases:
            with self.subTest(system=system, swift=swift):
                with mock.patch.object(self.ocr.platform, "system", return_value=system), mock.patch.object(
                    self.ocr.shutil, "which", return_value=swift
                ), mock.patch.object(self.ocr, "ocr_vision", return_value=answer), mock.patch.object(
                    self.ocr, "ocr_rapid", return_value=answer
                ):
                    code, out = call_main(self.ocr, self.image, "--force")
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(out)["engine"], expected)

    def test_vision_coordinates_are_flipped_to_top_down(self):
        output = json.dumps([{"lines": [{"text": "a", "x": 0.1, "y": 0.7, "w": 0.2, "h": 0.1}]}])
        done = subprocess.CompletedProcess([], 0, stdout=output, stderr="")
        with mock.patch.object(self.ocr.subprocess, "run", return_value=done):
            line = self.ocr.ocr_vision([Path("page.png")])[0][0]
        self.assertAlmostEqual(line["y0"], 0.2)
        self.assertAlmostEqual(line["y1"], 0.3)
        self.assertAlmostEqual(line["x1"], 0.3)

    def test_missing_korean_font_stops_with_message(self):
        with mock.patch.object(self.ocr, "FONT_CANDIDATES", []):
            with self.assertRaises(SystemExit) as stopped:
                self.fake_ocr(self.image)
        self.assertIn("글꼴", str(stopped.exception))
        self.assertFalse((self.dir / "scan_ocr.pdf").exists())

    # 알려진 문제: 첫 실행에 한국어 모델을 내려받지 못하면 쉬운 안내 없이 traceback으로 멈춘다.
    # 실제 출력을 보려고 별도 프로세스로 돌리고, 내려받기에 실패하는 가짜 rapidocr 패키지를 쓴다.
    @unittest.expectedFailure
    def test_model_download_failure_stops_with_message(self):
        package = self.dir / "fake" / "rapidocr"
        (package / "utils").mkdir(parents=True)
        (package / "__init__.py").write_text(FAKE_RAPIDOCR, encoding="utf-8")
        (package / "utils" / "__init__.py").write_text("", encoding="utf-8")
        (package / "utils" / "download_file.py").write_text(
            "class DownloadFileException(Exception):\n    pass\n", encoding="utf-8"
        )
        done = run_cli("paper_ocr.py", self.image, "--engine", "rapidocr", env={"PYTHONPATH": str(package.parent)})
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("Traceback", done.stdout + done.stderr)
        self.assertRegex(done.stderr, "모델|내려받|다운로드")
        self.assertFalse((self.dir / "scan_ocr.pdf").exists())


class SafetyTest(OcrCase):
    def test_original_is_not_changed(self):
        before = sha256(self.image)
        self.fake_ocr(self.image)
        self.assertEqual(sha256(self.image), before)
        self.assertEqual(page_text(self.image).strip(), "")

    def test_pdf_with_text_is_skipped(self):
        typed = text_pdf(self.dir / "typed.pdf", [rows(LONG_LINES)])
        done = run_cli("paper_ocr.py", typed)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(last_json(done)["status"], "skipped")
        self.assertFalse((self.dir / "typed_ocr.pdf").exists())

    def test_existing_output_is_kept_without_force(self):
        output = self.dir / "scan_ocr.pdf"
        output.write_bytes(b"keep me")
        done = run_cli("paper_ocr.py", self.image)
        self.assertEqual(done.returncode, 1)
        self.assertIn("이미 있습니다", done.stderr)
        self.assertEqual(output.read_bytes(), b"keep me")
        code, _ = self.fake_ocr(self.image, "--force")
        self.assertEqual(code, 0)
        self.assertIn(LINES[0], page_text(output))

    def test_output_cannot_be_the_input(self):
        before = sha256(self.image)
        done = run_cli("paper_ocr.py", self.image, "--output", self.image, "--force")
        self.assertEqual(done.returncode, 1)
        self.assertIn("같은 경로", done.stderr)
        self.assertEqual(sha256(self.image), before)

    def test_password_protected_pdf_is_refused(self):
        path = text_pdf(
            self.dir / "locked.pdf", [rows(LINES)], encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="user", owner_pw="owner"
        )
        done = run_cli("paper_ocr.py", path)
        self.assertEqual(done.returncode, 1)
        self.assertIn("암호", done.stderr)

    def test_missing_input_fails(self):
        self.assertNotEqual(run_cli("paper_ocr.py", self.dir / "none.pdf").returncode, 0)

    def test_default_name_handles_upper_case_and_double_extension(self):
        self.assertEqual(self.ocr.default_output(Path("UPPER.PDF")).name, "UPPER_ocr.pdf")
        self.assertEqual(self.ocr.default_output(Path("twice.pdf.pdf")).name, "twice_ocr.pdf")

    def test_korean_path_with_spaces(self):
        folder = self.dir / "한글 사용자"
        folder.mkdir()
        scan = image_pdf(self.source, folder / "시험 논문.pdf")
        code, summary = self.fake_ocr(scan)
        self.assertEqual(code, 0)
        self.assertEqual(Path(summary["output"]).name, "시험 논문_ocr.pdf")
        self.assertIn(LINES[0], page_text(Path(summary["output"])))


class RealEngineTest(PdfCase):
    TEXT = ["Regression test for scanned pages", "한글 문장을 읽는지 확인합니다"]

    def setUp(self):
        super().setUp()
        source = text_pdf(self.dir / "source.pdf", [[(LEFT, TOP + i * 40, line) for i, line in enumerate(self.TEXT)]])
        # 작은 글자도 읽도록 크게 그린 이미지를 쓴다.
        self.image = image_pdf(source, self.dir / "scan.pdf", dpi=300)

    def assert_read(self, done: subprocess.CompletedProcess, engine: str) -> None:
        self.assertEqual(done.returncode, 0, done.stderr)
        summary = last_json(done)
        self.assertEqual(summary["engine"], engine)
        text = page_text(Path(summary["output"]))
        self.assertIn("Regression", text)
        self.assertIn("한글", text)

    @unittest.skipUnless(platform.system() == "Darwin" and shutil.which("swift"), "Apple Vision은 swift가 있는 맥에서만 돈다")
    def test_apple_vision_reads_generated_scan(self):
        self.assert_read(run_cli("paper_ocr.py", self.image, "--engine", "vision"), "vision")

    @unittest.skipUnless(os.environ.get("RWK_TEST_RAPIDOCR") == "1", "RapidOCR는 RWK_TEST_RAPIDOCR=1일 때만 돈다 (모델 내려받기)")
    def test_rapidocr_reads_generated_scan(self):
        script = helpers.SCRIPTS / "paper_ocr.py"
        done = subprocess.run(
            ["uv", "run", str(script), str(self.image), "--engine", "rapidocr"], capture_output=True, encoding="utf-8"
        )
        self.assert_read(done, "rapidocr")


if __name__ == "__main__":
    unittest.main()
