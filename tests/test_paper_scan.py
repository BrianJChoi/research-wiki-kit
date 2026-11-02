"""paper_scan.py: 처리 경로, DOI 찾기, 폴더 훑기, 이어서 하기. Crossref는 가짜 응답만 쓴다."""

import io
import json
import shutil
import subprocess
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import helpers
import pymupdf
from helpers import PdfCase, call_main, image_pdf, load_script, rows, run_cli, text_pdf

KOREAN = ["생성형 인공지능을 활용한 대학 수업 사례를 살펴본 시험용 문장입니다."] * 8
ENGLISH = ["This generated sentence stands in for the text of an English paper."] * 8
CROSSREF_WORK = {
    "type": "journal-article",
    "title": ["A Generated Paper"],
    "original-title": [],
    "container-title": ["Journal of Fixtures"],
    "volume": "12",
    "issue": "3",
    "page": "45-67",
    "issued": {"date-parts": [[2024, 1, 31]]},
    "ISSN": ["1234-5678"],
    "language": "en",
    "publisher": "Fixture Press",
    "author": [{"family": "Hong", "given": "Gildong"}],
}


def crossref_response(*args, **kwargs):
    return io.BytesIO(json.dumps({"message": CROSSREF_WORK}).encode("utf-8"))


class ScanCase(PdfCase):
    def setUp(self):
        super().setUp()
        self.scan = load_script("paper_scan")
        self.out = self.dir / "scan.json"

    def run_scan(self, target: Path, *args) -> list[dict]:
        done = run_cli("paper_scan.py", target, "--out", self.out, "--no-crossref", *args)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(self.out.read_text(encoding="utf-8"))["papers"]

    def run_with_crossref(self, target: Path, urlopen) -> tuple[list[dict], mock.MagicMock]:
        patched = mock.MagicMock(side_effect=urlopen)
        with mock.patch("urllib.request.urlopen", patched), mock.patch("time.sleep"):
            code, _ = call_main(self.scan, target, "--out", self.out)
        self.assertEqual(code, 0)
        return json.loads(self.out.read_text(encoding="utf-8"))["papers"], patched


class RouteTest(ScanCase):
    def test_korean_text_goes_to_claude(self):
        entry = self.run_scan(text_pdf(self.dir / "ko.pdf", [rows(KOREAN)]))[0]
        self.assertEqual(entry["route"], "Claude 판독")
        self.assertEqual(entry["status"], "scanned")
        self.assertEqual(entry["pages"], 1)
        self.assertIs(entry["korean"], True)
        self.assertIs(entry["needs_ocr"], False)
        self.assertIsNone(entry["doi"])

    def test_image_pdf_needs_ocr(self):
        source = text_pdf(self.dir / "source.pdf", [rows(KOREAN)])
        entry = self.run_scan(image_pdf(source, self.dir / "image.pdf"))[0]
        self.assertEqual(entry["route"], "OCR 필요")
        self.assertEqual(entry["text_chars"], 0)
        self.assertIsNone(entry["korean"])

    def test_little_text_still_needs_ocr(self):
        few = self.run_scan(text_pdf(self.dir / "few.pdf", [rows(["쪽 번호와 머리글 정도의 글자"])]))[0]
        self.assertLess(few["text_chars"], self.scan.MIN_TEXT_CHARS)
        self.assertEqual(few["route"], "OCR 필요")

    def test_corrupt_file_fails_without_stopping(self):
        (self.dir / "broken.pdf").write_bytes(b"this is not a pdf")
        text_pdf(self.dir / "good.pdf", [rows(KOREAN)])
        papers = {entry["name"]: entry for entry in self.run_scan(self.dir)}
        self.assertEqual(papers["broken.pdf"]["route"], "실패")
        self.assertEqual(papers["broken.pdf"]["status"], "error")
        self.assertTrue(papers["broken.pdf"]["error"])
        self.assertEqual(papers["good.pdf"]["route"], "Claude 판독")

    def test_password_protected_pdf_fails_with_reason(self):
        path = text_pdf(
            self.dir / "locked.pdf",
            [rows(KOREAN)],
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="user",
            owner_pw="owner",
        )
        entry = self.run_scan(path)[0]
        self.assertEqual(entry["route"], "실패")
        self.assertIn("암호", entry["error"])

    def test_missing_target_reports_error(self):
        done = run_cli("paper_scan.py", self.dir / "none.pdf", "--out", self.out, "--no-crossref")
        self.assertEqual(done.returncode, 1)
        self.assertIn("찾을 수 없습니다", done.stderr)
        self.assertFalse(self.out.exists())

    def test_default_output_goes_to_current_folder(self):
        path = text_pdf(self.dir / "ko.pdf", [rows(KOREAN)])
        work = self.dir / "work"
        work.mkdir()
        done = run_cli("paper_scan.py", path, "--no-crossref", cwd=work)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((work / "paper-scan.json").exists())


class CrossrefTest(ScanCase):
    """모두 가짜 응답이다. 실제 Crossref API의 응답 형식은 여기서 확인하지 않는다."""

    def english_with_doi(self) -> Path:
        return text_pdf(self.dir / "en.pdf", [rows(["DOI 10.1234/fixture.2024.1", *ENGLISH])])

    def test_english_with_crossref_is_automatic(self):
        papers, urlopen = self.run_with_crossref(self.english_with_doi(), crossref_response)
        entry = papers[0]
        self.assertEqual(entry["route"], "자동 등록")
        self.assertEqual(entry["crossref"]["title"], "A Generated Paper")
        self.assertEqual(entry["crossref"]["journal"], "Journal of Fixtures")
        self.assertEqual(entry["crossref"]["date"], [2024, 1, 31])
        self.assertEqual(entry["crossref"]["authors"][0]["family"], "Hong")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.crossref.org/works/10.1234/fixture.2024.1")

    def test_korean_with_crossref_still_goes_to_claude(self):
        path = text_pdf(self.dir / "ko.pdf", [rows(["DOI 10.1234/fixture.2024.2", *KOREAN])])
        papers, _ = self.run_with_crossref(path, crossref_response)
        self.assertEqual(papers[0]["route"], "Claude 판독")
        self.assertIn("crossref", papers[0])

    def test_unreachable_crossref_keeps_doi_and_goes_to_claude(self):
        papers, urlopen = self.run_with_crossref(self.english_with_doi(), urllib.error.URLError("offline"))
        self.assertEqual(papers[0]["route"], "Claude 판독")
        self.assertEqual(papers[0]["doi"], "10.1234/fixture.2024.1")
        self.assertNotIn("crossref", papers[0])
        self.assertTrue(urlopen.called)

    def test_second_candidate_used_when_first_is_unknown(self):
        def answer(request, timeout):
            if "fixture.good" in request.full_url:
                return crossref_response()
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

        path = text_pdf(self.dir / "en.pdf", [rows(["10.1234/fixture.bad", "10.1234/fixture.good", *ENGLISH])])
        papers, _ = self.run_with_crossref(path, answer)
        self.assertEqual(papers[0]["doi"], "10.1234/fixture.good")
        self.assertEqual(papers[0]["route"], "자동 등록")

    def test_no_crossref_flag_makes_no_request(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            code, _ = call_main(self.scan, self.english_with_doi(), "--out", self.out, "--no-crossref")
        self.assertEqual(code, 0)
        urlopen.assert_not_called()
        self.assertEqual(json.loads(self.out.read_text(encoding="utf-8"))["papers"][0]["route"], "Claude 판독")


class DoiTest(ScanCase):
    def doi_of(self, pages: list[list[tuple]], metadata: dict | None = None) -> str | None:
        return self.run_scan(text_pdf(self.dir / "doi.pdf", pages, metadata))[0]["doi"]

    def test_trailing_punctuation_is_removed(self):
        self.assertEqual(self.doi_of([rows(["https://doi.org/10.1234/abc-def.5).", *KOREAN])]), "10.1234/abc-def.5")

    def test_found_in_file_metadata(self):
        self.assertEqual(self.doi_of([rows(KOREAN)], {"subject": "doi:10.1234/meta.1"}), "10.1234/meta.1")

    def test_found_on_second_page(self):
        self.assertEqual(self.doi_of([rows(KOREAN), rows(["10.1234/second.2"])]), "10.1234/second.2")

    def test_reference_doi_on_third_page_is_ignored(self):
        pages = [rows(KOREAN), rows(KOREAN), rows(["[1] 10.1234/someone.else"])]
        self.assertIsNone(self.doi_of(pages))

    def test_space_inserted_by_ocr_is_removed(self):
        found = self.scan.find_dois(self.open_doc([rows(["10.1234/ abc.2024"])]))
        self.assertIn("10.1234/abc.2024", found)

    def open_doc(self, pages: list[list[tuple]]) -> pymupdf.Document:
        doc = pymupdf.open(text_pdf(self.dir / "space.pdf", pages))
        self.addCleanup(doc.close)
        return doc


class FolderTest(ScanCase):
    def test_keeps_most_processed_copy(self):
        for name in ("a.pdf", "a_ocr.pdf", "a_linked.pdf", "a_ocr_linked.pdf", "b.pdf", "b_ocr.pdf"):
            text_pdf(self.dir / name, [rows(KOREAN)])
        names = sorted(entry["name"] for entry in self.run_scan(self.dir))
        self.assertEqual(names, ["a_ocr_linked.pdf", "b_ocr.pdf"])

    def test_scans_subfolders_and_keeps_same_name_apart(self):
        (self.dir / "x").mkdir()
        (self.dir / "y").mkdir()
        text_pdf(self.dir / "x" / "same.pdf", [rows(KOREAN)])
        text_pdf(self.dir / "y" / "same.PDF", [rows(KOREAN)])
        self.assertEqual(len(self.run_scan(self.dir)), 2)

    def test_hidden_and_other_files_are_skipped(self):
        text_pdf(self.dir / "paper.pdf", [rows(KOREAN)])
        text_pdf(self.dir / ".hidden.pdf", [rows(KOREAN)])
        (self.dir / "notes.txt").write_text("메모", encoding="utf-8")
        self.assertEqual([entry["name"] for entry in self.run_scan(self.dir)], ["paper.pdf"])

    def test_korean_path_with_spaces(self):
        folder = self.dir / "한글 사용자" / "논문 폴더"
        folder.mkdir(parents=True)
        text_pdf(folder / "시험 논문.pdf", [rows(KOREAN)])
        entry = self.run_scan(folder)[0]
        self.assertEqual(entry["name"], "시험 논문.pdf")
        self.assertEqual(entry["route"], "Claude 판독")
        self.assertEqual(Path(entry["path"]).resolve(), (folder / "시험 논문.pdf").resolve())


class ResumeTest(ScanCase):
    def mark_scanned(self, marker: str) -> None:
        data = json.loads(self.out.read_text(encoding="utf-8"))
        data["papers"][0]["marker"] = marker
        self.out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_scanned_file_is_not_scanned_again(self):
        path = text_pdf(self.dir / "ko.pdf", [rows(KOREAN)])
        self.run_scan(path)
        self.mark_scanned("kept")
        self.assertEqual(self.run_scan(path)[0]["marker"], "kept")

    def test_changed_file_is_scanned_again(self):
        path = text_pdf(self.dir / "ko.pdf", [rows(KOREAN)])
        self.run_scan(path)
        self.mark_scanned("old")
        text_pdf(path, [rows(ENGLISH)])
        entry = self.run_scan(path)[0]
        self.assertNotIn("marker", entry)
        self.assertIs(entry["korean"], False)

    def test_failed_file_is_tried_again(self):
        path = self.dir / "broken.pdf"
        path.write_bytes(b"this is not a pdf")
        self.run_scan(path)
        self.mark_scanned("old")
        self.assertNotIn("marker", self.run_scan(path)[0])


class HeaderSmokeTest(PdfCase):
    def test_uv_reads_inline_dependencies(self):
        if not shutil.which("uv"):
            self.skipTest("uv가 없어 인라인 의존성을 확인하지 못했습니다")
        for script in ("paper_scan.py", "paper_link.py"):
            done = subprocess.run(
                ["uv", "run", str(helpers.SCRIPTS / script), "--help"], capture_output=True, encoding="utf-8"
            )
            self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
