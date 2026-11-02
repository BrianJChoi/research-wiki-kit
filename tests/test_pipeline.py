"""스캔본이 훑기, 글자 입히기, 다시 훑기, 링크까지 SKILL.md 순서대로 이어지는지 본다."""

import json
import platform
import shutil
import unittest
from pathlib import Path
from unittest import mock

import pymupdf
from helpers import (
    LEFT,
    PdfCase,
    call_main,
    goto_links,
    image_pdf,
    last_json,
    load_script,
    paper_pdf,
    read_as_ocr,
    run_cli,
)

BODY = ["선행연구[1]에 따르면 수업 효과가 있었다.", "다른 연구[2,3]도 같은 결과를 보였다.", "최근 연구[4]는 다른 결론을 냈다."] * 8
STAMP = "Generated stamp printed on every page of this fixture"


class PipelineTest(PdfCase):
    def setUp(self):
        super().setUp()
        self.ocr = load_script("paper_ocr")
        self.source = paper_pdf(self.dir / "source.pdf", BODY)

    def scan(self, path: Path) -> dict:
        out = self.dir / "scan.json"
        done = run_cli("paper_scan.py", path, "--out", out, "--no-crossref")
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(out.read_text(encoding="utf-8"))["papers"][0]

    def fake_ocr(self, path: Path) -> dict:
        with mock.patch.object(self.ocr, "ocr_rapid", return_value=read_as_ocr(self.source)):
            code, out = call_main(self.ocr, path, "--engine", "rapidocr")
        self.assertEqual(code, 0)
        return json.loads(out)

    def test_scan_then_ocr_then_link(self):
        scanned = image_pdf(self.source, self.dir / "paper.pdf")
        self.assertEqual(self.scan(scanned)["route"], "OCR 필요")

        searchable = Path(self.fake_ocr(scanned)["output"])
        self.assertEqual(self.scan(searchable)["route"], "Claude 판독")

        done = run_cli("paper_link.py", searchable)
        self.assertEqual(done.returncode, 0, done.stderr)
        summary = last_json(done)
        self.assertEqual(summary["status"], "done", summary)
        self.assertEqual(summary["references"], 4)
        self.assertEqual(summary["references_never_cited"], [])
        self.assertEqual(summary["citation_links"], 32)
        self.assertEqual(summary["back_links"], 4)

        linked = Path(summary["output"])
        self.assertEqual(linked.name, "paper_ocr_linked.pdf")
        self.assertEqual({item["page"] for item in goto_links(linked) if item["source"] == 0}, {1})
        # 폴더를 다시 훑으면 가장 많이 처리된 사본만 남는다
        out = self.dir / "folder.json"
        self.assertEqual(run_cli("paper_scan.py", self.dir, "--out", out, "--no-crossref").returncode, 0)
        names = [entry["name"] for entry in json.loads(out.read_text(encoding="utf-8"))["papers"]]
        self.assertEqual(names, ["paper_ocr_linked.pdf", "source.pdf"])

    def test_rotated_scan_can_be_linked_after_ocr(self):
        sideways = image_pdf(self.source, self.dir / "paper.pdf", sideways=True)
        self.assertEqual(last_json(run_cli("paper_link.py", sideways))["status"], "skipped")
        summary = last_json(run_cli("paper_link.py", self.fake_ocr(sideways)["output"]))
        self.assertEqual(summary["status"], "done", summary)
        self.assertEqual(summary["citation_links"], 32)

    @unittest.skipUnless(platform.system() == "Darwin" and shutil.which("swift"), "Apple Vision은 swift가 있는 맥에서만 돈다")
    def test_apple_vision_output_can_be_linked(self):
        scanned = image_pdf(self.source, self.dir / "paper.pdf", dpi=300)
        done = run_cli("paper_ocr.py", scanned, "--engine", "vision")
        self.assertEqual(done.returncode, 0, done.stderr)
        summary = last_json(run_cli("paper_link.py", last_json(done)["output"]))
        self.assertEqual(summary["status"], "done", summary)
        self.assertEqual(summary["references"], 4)
        self.assertEqual(summary["references_never_cited"], [])

    # 알려진 문제: 스캔본 쪽마다 글자가 찍혀 있으면 paper_scan은 OCR이 필요하다고 하고
    # paper_ocr은 글자가 있다며 건너뛴다. 사본이 생기지 않아 다음 단계로 갈 수 없다.
    @unittest.expectedFailure
    def test_scan_with_stamp_on_each_page_can_be_ocred(self):
        scanned = image_pdf(self.source, self.dir / "stamped.pdf")
        with pymupdf.open(scanned) as doc:
            for page in doc:
                page.insert_text((LEFT, 820), STAMP, fontname="helv", fontsize=6)
            doc.saveIncr()
        self.assertEqual(self.scan(scanned)["route"], "OCR 필요")
        self.assertEqual(self.fake_ocr(scanned).get("status"), "done")

    # 알려진 문제: 글자가 있는 PDF에 회전된 쪽이 있으면 paper_link는 paper_ocr을 먼저 돌리라 하고
    # paper_ocr은 글자가 있다며 건너뛴다. 어느 쪽을 돌려도 링크가 생기지 않는다.
    @unittest.expectedFailure
    def test_text_pdf_with_rotated_page_is_not_a_dead_end(self):
        path = paper_pdf(self.dir / "landscape.pdf", BODY)
        with pymupdf.open(path) as doc:
            doc[0].set_rotation(90)
            doc.saveIncr()
        told_to_ocr = "paper_ocr" in last_json(run_cli("paper_link.py", path)).get("reason", "")
        ocr_skipped = last_json(run_cli("paper_ocr.py", path)).get("status") == "skipped"
        self.assertFalse(told_to_ocr and ocr_skipped)


if __name__ == "__main__":
    unittest.main()
