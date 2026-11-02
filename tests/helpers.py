"""시험용 PDF를 코드로 만들고 스크립트를 실행한다. 실제 논문과 개인 정보는 쓰지 않는다."""

import contextlib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pymupdf

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "zotero-add-paper" / "scripts"
FONT = pymupdf.Font("cjk")
WIDTH, HEIGHT = 595, 842
LEFT = 72
TOP = 100
LINE_GAP = 16
INDENT = 20
FONT_SIZE = 10


def rows(texts: list[str], x: float = LEFT, y: float = TOP) -> list[tuple]:
    return [(x, y + index * LINE_GAP, text) for index, text in enumerate(texts)]


def reference_rows(count: int, x: float = LEFT, y: float = TOP, style: str = "[{}]", first: int = 1) -> list[tuple]:
    """번호가 붙은 참고문헌을 항목마다 두 줄(내어쓰기)로 만든다."""
    lines = []
    for index in range(count):
        number = first + index
        top = y + index * 2 * LINE_GAP
        lines.append((x, top, f"{style.format(number)} 홍길동{number}, 시험 논문 제목 {number}, 시험학회지,"))
        lines.append((x + INDENT, top + LINE_GAP, f"제{number}권, 2024."))
    return lines


def write_lines(page: pymupdf.Page, lines: list[tuple]) -> None:
    page.insert_font(fontname="kr", fontbuffer=FONT.buffer)
    for x, y, text in lines:
        page.insert_text((x, y), text, fontname="kr", fontsize=FONT_SIZE)


def text_pdf(path: Path, pages: list[list[tuple]], metadata: dict | None = None, **save_options) -> Path:
    with pymupdf.open() as doc:
        for lines in pages:
            write_lines(doc.new_page(width=WIDTH, height=HEIGHT), lines)
        if metadata:
            doc.set_metadata(metadata)
        doc.save(path, **save_options)
    return path


def paper_pdf(path: Path, body: list[str], references: int = 4, **options) -> Path:
    """1쪽 본문, 2쪽 참고문헌으로 된 번호 인용 논문을 만든다."""
    return text_pdf(path, [rows(body), [(LEFT, TOP - 20, "참고문헌"), *reference_rows(references)]], **options)


def image_pdf(source: Path, path: Path, dpi: int = 150, sideways: bool = False) -> Path:
    """글자 PDF를 쪽 이미지로 바꾼다. sideways면 /Rotate 값으로 바로 세워 보이는 스캔본을 만든다."""
    with pymupdf.open(source) as original, pymupdf.open() as doc:
        for page in original:
            matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
            if sideways:
                pixmap = page.get_pixmap(matrix=matrix.prerotate(270), alpha=False)
                scanned = doc.new_page(width=page.rect.height, height=page.rect.width)
            else:
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                scanned = doc.new_page(width=page.rect.width, height=page.rect.height)
            scanned.insert_image(scanned.rect, pixmap=pixmap)
            if sideways:
                scanned.set_rotation(90)
        doc.save(path)
    return path


def read_as_ocr(source: Path) -> list[list[dict]]:
    """글자 PDF의 줄을 OCR 엔진이 낸 결과처럼 돌려준다. 엔진 없이 뒤 단계를 시험할 때 쓴다."""
    pages = []
    with pymupdf.open(source) as doc:
        for page in doc:
            lines = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    x0, y0, x1, y1 = line["bbox"]
                    text = "".join(span["text"] for span in line["spans"])
                    lines.append(
                        {
                            "text": text,
                            "x0": x0 / page.rect.width,
                            "y0": y0 / page.rect.height,
                            "x1": x1 / page.rect.width,
                            "y1": y1 / page.rect.height,
                        }
                    )
            pages.append(lines)
    return pages


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page_text(path: Path, index: int = 0) -> str:
    with pymupdf.open(path) as doc:
        return doc[index].get_text()


def rendered(path: Path, index: int = 0, dpi: int = 72) -> tuple:
    with pymupdf.open(path) as doc:
        pixmap = doc[index].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
        return pixmap.width, pixmap.height, pixmap.samples


def mean_difference(left: tuple, right: tuple) -> float:
    assert left[:2] == right[:2], "쪽 크기가 다릅니다"
    return sum(abs(a - b) for a, b in zip(left[2], right[2])) / len(left[2])


def goto_links(path: Path) -> list[dict]:
    found = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc):
            for item in page.get_links():
                if item.get("kind") == pymupdf.LINK_GOTO:
                    text = page.get_textbox(item["from"]).strip()
                    found.append(
                        {
                            "source": index,
                            "text": text,
                            "number": re.sub(r"\D", "", text),
                            "rect": tuple(item["from"]),
                            "page": item["page"],
                            "to": tuple(item["to"]),
                        }
                    )
    return found


def run_cli(script: str, *args, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """사용자가 실행하듯 스크립트를 별도 프로세스로 돌린다."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *[str(arg) for arg in args]],
        capture_output=True,
        encoding="utf-8",
        cwd=cwd,
    )


def last_json(done: subprocess.CompletedProcess) -> dict:
    return json.loads(done.stdout.strip().splitlines()[-1])


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(f"rwk_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_main(module, *args) -> tuple[int, str]:
    """외부 호출을 가짜로 바꿔야 하는 시험은 같은 프로세스에서 main을 부른다."""
    stdout = io.StringIO()
    with mock.patch.object(sys, "argv", ["script", *[str(arg) for arg in args]]), contextlib.redirect_stdout(stdout):
        code = module.main()
    return code, stdout.getvalue()


class PdfCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.dir = Path(folder.name)
