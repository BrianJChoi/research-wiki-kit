"""paper_ocr.py: 글자 층, 쪽 고르기, 회전, 엔진 전환, 원본 보호.

엔진이 필요 없는 시험은 read_as_ocr의 가짜 결과를 쓴다. 실제 엔진 시험은 RealEngineTest뿐이다.
"""

import json
import os
import platform
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
    @unittest.expectedFailure
    def test_model_download_failure_stops_with_message(self):
        with mock.patch.object(self.ocr, "ocr_rapid", side_effect=ConnectionError("download failed")):
            code, _ = call_main(self.ocr, self.image, "--engine", "rapidocr")
        self.assertEqual(code, 1)


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
