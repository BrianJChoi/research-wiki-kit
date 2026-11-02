"""paper_link.py: 링크 위치, 번호 해석, 참고문헌 찾기, 건너뛰는 경우, 원본 보호."""

import unittest
from pathlib import Path

import pymupdf
from helpers import (
    INDENT,
    LEFT,
    LINE_GAP,
    TOP,
    WIDTH,
    PdfCase,
    goto_links,
    image_pdf,
    last_json,
    paper_pdf,
    reference_rows,
    rows,
    run_cli,
    sha256,
    text_pdf,
)


class LinkCase(PdfCase):
    def link(self, path: Path, *args) -> dict:
        done = run_cli("paper_link.py", path, *args)
        self.assertEqual(done.returncode, 0, done.stderr)
        return last_json(done)

    def linked_paper(self, body: list[str], references: int = 4) -> tuple[dict, list[dict]]:
        path = paper_pdf(self.dir / "paper.pdf", body, references)
        summary = self.link(path)
        self.assertEqual(summary["status"], "done", summary)
        return summary, goto_links(self.dir / "paper_linked.pdf")


class LinkPlacementTest(LinkCase):
    def test_body_number_jumps_to_its_reference(self):
        summary, links = self.linked_paper(["선행연구[2]에 따르면 효과가 있었다."])
        self.assertEqual(summary["citation_links"], 1)
        forward = next(item for item in links if item["source"] == 0)
        self.assertEqual(forward["number"], "2")
        self.assertEqual(forward["page"], 1)
        # 숫자 하나도 누를 수 있는 너비를 유지한다
        self.assertGreaterEqual(forward["rect"][2] - forward["rect"][0], 8)
        # 참고문헌 2번 첫 줄(2쪽 위에서 세 번째 줄 높이) 바로 위로 간다
        with pymupdf.open(self.dir / "paper_linked.pdf") as doc:
            entry = doc[1].search_for("[2]")[0]
        self.assertAlmostEqual(forward["to"][0], entry.x0, delta=1)
        self.assertAlmostEqual(forward["to"][1], entry.y0 - 6, delta=3)

    def test_reference_number_jumps_back_to_first_citation(self):
        summary, links = self.linked_paper(["첫 인용[3]입니다.", "두 번째 인용[3]입니다."])
        self.assertEqual(summary["citation_links"], 2)
        self.assertEqual(summary["back_links"], 1)
        back = next(item for item in links if item["source"] == 1)
        self.assertEqual(back["page"], 0)
        self.assertTrue(back["text"].startswith("[3]"))
        with pymupdf.open(self.dir / "paper_linked.pdf") as doc:
            first_line = doc[0].search_for("첫 인용")[0]
        self.assertAlmostEqual(back["to"][1], first_line.y0 - 6, delta=3)

    def test_summary_lists_references_without_citation(self):
        summary, _ = self.linked_paper(["인용[1]과 인용[2]만 있다."])
        self.assertEqual(summary["references"], 4)
        self.assertEqual(summary["references_never_cited"], [3, 4])
        self.assertEqual(summary["number_agreement"], 1.0)

    def test_adjacent_brackets_get_their_own_rectangles(self):
        _, links = self.linked_paper(["연속 인용[1][2]입니다."])
        forward = [item for item in links if item["source"] == 0]
        self.assertEqual([item["number"] for item in forward], ["1", "2"])
        self.assertLess(forward[0]["rect"][0], forward[1]["rect"][0])


class MarkerTest(LinkCase):
    def test_comma_list_links_each_number(self):
        summary, links = self.linked_paper(["여러 인용[1,3]입니다."])
        self.assertEqual(summary["citation_links"], 2)
        self.assertEqual([item["number"] for item in links if item["source"] == 0], ["1", "3"])

    def test_range_links_ends_and_counts_middle_as_cited(self):
        for marker in ("[1-4]", "[1–4]", "[1~4]"):
            with self.subTest(marker=marker):
                path = paper_pdf(self.dir / "range.pdf", [f"범위 인용{marker}입니다."])
                summary = self.link(path, "--force")
                self.assertEqual(summary["citation_links"], 2)
                self.assertEqual(summary["back_links"], 4)
                self.assertEqual(summary["references_never_cited"], [])

    def test_number_outside_references_is_left_alone(self):
        summary, links = self.linked_paper(["연도 표기[2024]와 정상 인용[1]입니다."])
        self.assertEqual(summary["citation_links"], 1)
        self.assertEqual(summary["unresolved_markers"], ["[2024]"])
        self.assertEqual([item["number"] for item in links if item["source"] == 0], ["1"])

    def test_ocr_letters_are_read_as_digits(self):
        summary, links = self.linked_paper(["글자로 읽힌 번호[l]입니다."])
        self.assertEqual(summary["citation_links"], 1)
        self.assertEqual(summary["back_links"], 1)
        self.assertEqual([item["page"] for item in links if item["source"] == 0], [1])

    def test_ocr_bracket_read_as_one_is_repaired_and_reported(self):
        summary, _ = self.linked_paper(["닫는 괄호를 놓친 번호[31 입니다."])
        self.assertEqual(summary["citation_links"], 1)
        self.assertEqual(summary["repaired_markers"], ["[31 -> [3]"])

    def test_ocr_bracket_between_numbers_is_repaired(self):
        summary, _ = self.linked_paper(["번호 사이[2113]입니다."])
        self.assertEqual(summary["citation_links"], 2)
        self.assertEqual(summary["references_never_cited"], [1, 4])
        self.assertEqual(summary["repaired_markers"], ["[2113] -> [2, 3]"])

    # 알려진 문제: 대괄호 안 공백을 만나면 뒤 번호를 놓치고 unresolved에도 남지 않는다.
    @unittest.expectedFailure
    def test_comma_list_with_space_links_each_number(self):
        summary, _ = self.linked_paper(["공백이 있는 인용[1, 3]입니다."])
        self.assertEqual(summary["citation_links"], 2)
        self.assertEqual(summary["references_never_cited"], [2, 4])


class ReferenceSectionTest(LinkCase):
    def test_last_heading_wins_over_table_of_contents(self):
        pages = [
            rows(["목차", "참고문헌", "본문 인용[1]과 인용[2]입니다."]),
            [(LEFT, TOP - 20, "참고문헌"), *reference_rows(3)],
        ]
        summary = self.link(text_pdf(self.dir / "toc.pdf", pages))
        self.assertEqual(summary["status"], "done", summary)
        self.assertEqual(summary["references"], 3)
        self.assertEqual(summary["citation_links"], 2)

    def test_references_after_body_on_same_page(self):
        lines = [*rows(["본문 인용[2]입니다."]), (LEFT, TOP + 40, "References"), *reference_rows(3, y=TOP + 60)]
        summary = self.link(text_pdf(self.dir / "same.pdf", [lines]))
        self.assertEqual(summary["references"], 3)
        self.assertEqual(summary["citation_links"], 1)

    def test_two_columns_read_in_order(self):
        right = WIDTH / 2 + 10
        # 왼쪽 단 인용이 오른쪽 단 제목보다 아래에 있어도 본문으로 읽어야 한다
        pages = [
            [
                *rows([*["왼쪽 단 본문입니다."] * 8, "왼쪽 단 인용[3]입니다."]),
                (right, TOP, "참고문헌"),
                *reference_rows(4, x=right, y=TOP + 20),
            ]
        ]
        summary = self.link(text_pdf(self.dir / "columns.pdf", pages))
        self.assertEqual(summary["status"], "done", summary)
        self.assertEqual(summary["references"], 4)
        self.assertEqual(summary["citation_links"], 1)
        forward = next(item for item in goto_links(self.dir / "columns_linked.pdf") if item["number"] == "3")
        self.assertAlmostEqual(forward["to"][0], right, delta=2)

    def test_references_continue_on_next_page(self):
        pages = [
            rows(["본문 인용[6]입니다."]),
            [(LEFT, TOP - 20, "참고문헌"), *reference_rows(3)],
            reference_rows(3, first=4),
        ]
        summary = self.link(text_pdf(self.dir / "pages.pdf", pages))
        self.assertEqual(summary["references"], 6)
        forward = next(item for item in goto_links(self.dir / "pages_linked.pdf") if item["source"] == 0)
        self.assertEqual(forward["page"], 2)

    def test_running_header_is_not_a_reference(self):
        pages = [
            rows(["본문 인용[1]입니다."]),
            [(LEFT, 40, "시험학회지 제1권"), (LEFT, TOP - 20, "참고문헌"), *reference_rows(3)],
            [(LEFT, 40, "시험학회지 제1권"), *reference_rows(2, first=4)],
        ]
        summary = self.link(text_pdf(self.dir / "header.pdf", pages))
        self.assertEqual(summary["references"], 5)
        self.assertEqual(summary["number_agreement"], 1.0)

    def test_author_biography_ends_references(self):
        tail = TOP + 3 * 2 * LINE_GAP
        lines = [(LEFT, TOP - 20, "참고문헌"), *reference_rows(3), (LEFT, tail, "저자 소개"), (LEFT, tail + 16, "홍길동")]
        summary = self.link(text_pdf(self.dir / "bio.pdf", [rows(["본문 인용[1]입니다."]), lines]))
        self.assertEqual(summary["references"], 3)

    def test_dot_numbered_references(self):
        pages = [rows(["본문 인용[2]입니다."]), [(LEFT, TOP - 20, "References"), *reference_rows(3, style="{}.")]]
        summary = self.link(text_pdf(self.dir / "dot.pdf", pages))
        self.assertEqual(summary["references"], 3)
        self.assertEqual(summary["citation_links"], 1)

    def test_single_line_references_use_their_numbers(self):
        for style in ("[{}]", "{}."):
            with self.subTest(style=style):
                entries = [(LEFT, TOP + index * LINE_GAP, f"{style.format(index + 1)} 홍길동, 시험 논문.") for index in range(3)]
                pages = [rows(["본문 인용[3]입니다."]), [(LEFT, TOP - 20, "참고문헌"), *entries]]
                summary = self.link(text_pdf(self.dir / "single.pdf", pages), "--force")
                self.assertEqual(summary.get("references"), 3, summary)
                self.assertEqual(summary["citation_links"], 1)

    def test_unreadable_heading_falls_back_to_first_entry(self):
        pages = [
            rows(["본문 인용[2]입니다.", *["다음 줄입니다."] * 10]),
            [(LEFT, TOP - 20, "6. 참고문헌"), *reference_rows(3)],
        ]
        summary = self.link(text_pdf(self.dir / "numbered.pdf", pages))
        self.assertEqual(summary["status"], "done", summary)
        self.assertEqual(summary["references"], 3)


class SkipTest(LinkCase):
    def assert_skipped(self, path: Path, reason: str) -> dict:
        summary = self.link(path)
        self.assertEqual(summary["status"], "skipped", summary)
        self.assertIn(reason, summary["reason"])
        self.assertFalse(path.with_name(f"{path.stem}_linked.pdf").exists())
        return summary

    def with_links(self, count: int) -> Path:
        path = paper_pdf(self.dir / "publisher.pdf", ["본문 인용[1]입니다."])
        with pymupdf.open(path) as doc:
            for index in range(count):
                rect = pymupdf.Rect(LEFT, 200 + index * 20, LEFT + 50, 215 + index * 20)
                doc[0].insert_link({"kind": pymupdf.LINK_GOTO, "from": rect, "page": 1, "to": pymupdf.Point(0, 0), "zoom": 0})
            doc.saveIncr()
        return path

    def test_publisher_links_are_kept(self):
        self.assert_skipped(self.with_links(6), "이미 내부 링크가 6개")

    def test_few_existing_links_do_not_stop_linking(self):
        self.assertEqual(self.link(self.with_links(5))["status"], "done")

    def test_rotated_pdf_is_sent_to_ocr(self):
        path = paper_pdf(self.dir / "rotated.pdf", ["본문 인용[1]입니다."])
        with pymupdf.open(path) as doc:
            doc[0].set_rotation(90)
            doc.saveIncr()
        self.assert_skipped(path, "회전이 지정된 PDF")

    def test_image_pdf_is_sent_to_ocr(self):
        source = paper_pdf(self.dir / "source.pdf", ["본문 인용[1]입니다."])
        self.assert_skipped(image_pdf(source, self.dir / "image.pdf"), "글자 정보가 없습니다")

    def test_paper_without_references(self):
        self.assert_skipped(text_pdf(self.dir / "none.pdf", [rows(["참고문헌이 없는 문서입니다."] * 3)]), "참고문헌 위치")

    def test_author_year_references(self):
        entries = []
        for index in range(3):
            entries.append((LEFT, TOP + index * 2 * LINE_GAP, f"Hong, G. ({2020 + index}). A generated title,"))
            entries.append((LEFT + INDENT, TOP + index * 2 * LINE_GAP + LINE_GAP, "Journal of Fixtures, 1, 1-2."))
        pages = [rows(["Prior work (Hong, 2020) is cited here."]), [(LEFT, TOP - 20, "References"), *entries]]
        summary = self.link(text_pdf(self.dir / "apa.pdf", pages))
        self.assertEqual(summary["status"], "skipped", summary)
        self.assertFalse((self.dir / "apa_linked.pdf").exists())

    def test_untrustworthy_numbers(self):
        lines = [(LEFT, TOP - 20, "참고문헌")]
        for index, number in enumerate((7, 3, 9, 8)):
            lines += reference_rows(1, y=TOP + index * 2 * LINE_GAP, first=number)
        summary = self.assert_skipped(text_pdf(self.dir / "bad.pdf", [rows(["본문 인용[1]입니다."]), lines]), "믿을 수 없어")
        self.assertEqual(summary["references"], 4)

    def test_no_citation_in_body(self):
        summary = self.assert_skipped(paper_pdf(self.dir / "plain.pdf", ["인용이 없는 본문입니다."]), "번호 인용을 찾지 못했습니다")
        self.assertEqual(summary["references"], 4)


class SafetyTest(LinkCase):
    BODY = ["본문 인용[1]입니다."]

    def test_original_is_not_changed(self):
        path = paper_pdf(self.dir / "paper.pdf", self.BODY)
        before = sha256(path)
        self.link(path)
        self.assertEqual(sha256(path), before)
        self.assertEqual(goto_links(path), [])

    def test_dry_run_reports_same_counts_without_a_file(self):
        path = paper_pdf(self.dir / "paper.pdf", self.BODY)
        planned = self.link(path, "--dry-run")
        self.assertEqual(planned["status"], "dry-run")
        self.assertFalse((self.dir / "paper_linked.pdf").exists())
        done = self.link(path)
        for key in ("references", "citation_links", "back_links"):
            self.assertEqual(planned[key], done[key])

    def test_existing_output_is_kept_without_force(self):
        path = paper_pdf(self.dir / "paper.pdf", self.BODY)
        output = self.dir / "paper_linked.pdf"
        output.write_bytes(b"keep me")
        done = run_cli("paper_link.py", path)
        self.assertEqual(done.returncode, 1)
        self.assertIn("이미 있습니다", done.stderr)
        self.assertEqual(output.read_bytes(), b"keep me")
        self.link(path, "--force")
        self.assertTrue(goto_links(output))

    def test_output_cannot_be_the_input(self):
        path = paper_pdf(self.dir / "paper.pdf", self.BODY)
        before = sha256(path)
        done = run_cli("paper_link.py", path, "--output", path, "--force")
        self.assertEqual(done.returncode, 1)
        self.assertIn("같은 경로", done.stderr)
        self.assertEqual(sha256(path), before)

    def test_password_protected_pdf_is_refused(self):
        path = paper_pdf(
            self.dir / "locked.pdf", self.BODY, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="user", owner_pw="owner"
        )
        done = run_cli("paper_link.py", path)
        self.assertEqual(done.returncode, 1)
        self.assertIn("암호", done.stderr)

    def test_missing_input_fails(self):
        self.assertNotEqual(run_cli("paper_link.py", self.dir / "none.pdf").returncode, 0)

    def test_default_name_handles_upper_case_and_double_extension(self):
        for name, expected in (("UPPER.PDF", "UPPER_linked.pdf"), ("twice.pdf.pdf", "twice_linked.pdf")):
            with self.subTest(name=name):
                summary = self.link(paper_pdf(self.dir / name, self.BODY))
                self.assertEqual(Path(summary["output"]).name, expected)

    def test_korean_path_with_spaces(self):
        folder = self.dir / "한글 사용자"
        folder.mkdir()
        summary = self.link(paper_pdf(folder / "시험 논문.pdf", self.BODY))
        self.assertEqual(summary["status"], "done", summary)
        self.assertTrue((folder / "시험 논문_linked.pdf").exists())


if __name__ == "__main__":
    unittest.main()
