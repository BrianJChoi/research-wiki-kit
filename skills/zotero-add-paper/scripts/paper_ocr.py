# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["pymupdf>=1.24", "rapidocr>=3.10", "onnxruntime>=1.20"]
# ///
"""이미지 PDF에 보이지 않는 글자를 얹어 검색 가능한 사본을 만든다.

원본은 고치지 않는다. 화면은 그대로이고 글자 정보만 추가된다.

사용법:
    uv run paper_ocr.py <입력.pdf> [--output 출력.pdf] [--engine auto|rapidocr|vision]

auto는 맥에서 Apple Vision, 그 외에는 RapidOCR를 쓴다.
"""

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

MIN_PAGE_CHARS = 30
FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def find_font() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise SystemExit("한글 글꼴을 찾지 못했습니다.")


def default_output(path: Path) -> Path:
    stem = re.sub(r"(\.pdf)+$", "", path.name, flags=re.IGNORECASE)
    return path.with_name(f"{stem}_ocr.pdf")


def render(doc: pymupdf.Document, indexes: list[int], dpi: int, folder: Path) -> list[Path]:
    paths = []
    for index in indexes:
        path = folder / f"page-{index + 1:04d}.png"
        doc[index].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False).save(path)
        paths.append(path)
    return paths


def ocr_rapid(paths: list[Path]) -> list[list[dict]]:
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

    engine = RapidOCR(
        params={
            "Rec.lang_type": LangRec.KOREAN,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
            "Rec.model_type": ModelType.MOBILE,
            "Global.text_score": 0.3,
        }
    )
    pages = []
    for path in paths:
        pixmap = pymupdf.Pixmap(str(path))
        width, height = pixmap.width, pixmap.height
        result = engine(str(path))
        lines = []
        if result.boxes is not None:
            for box, text in zip(result.boxes, result.txts):
                xs = [float(point[0]) for point in box]
                ys = [float(point[1]) for point in box]
                lines.append(
                    {"text": text, "x0": min(xs) / width, "y0": min(ys) / height, "x1": max(xs) / width, "y1": max(ys) / height}
                )
        pages.append(lines)
    return pages


def ocr_vision(paths: list[Path]) -> list[list[dict]]:
    swift = Path(__file__).with_name("vision_ocr.swift")
    done = subprocess.run(
        ["swift", str(swift), *[str(p) for p in paths]], capture_output=True, text=True, check=True
    )
    pages = []
    for page in json.loads(done.stdout):
        pages.append(
            [
                {
                    "text": line["text"],
                    "x0": line["x"],
                    "y0": 1 - line["y"] - line["h"],
                    "x1": line["x"] + line["w"],
                    "y1": 1 - line["y"],
                }
                for line in page["lines"]
            ]
        )
    return pages


def add_text_layer(page: pymupdf.Page, lines: list[dict], font_path: str) -> None:
    page.insert_font(fontname="ocrkr", fontfile=font_path)
    font = pymupdf.Font(fontfile=font_path)
    width, height = page.rect.width, page.rect.height
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        x = line["x0"] * width
        box_height = (line["y1"] - line["y0"]) * height
        size = max(box_height * 0.9, 3)
        baseline = line["y1"] * height - box_height * 0.2
        text_width = font.text_length(text, fontsize=size) or 1
        scale = (line["x1"] - line["x0"]) * width / text_width
        page.insert_text(
            (x, baseline),
            text,
            fontname="ocrkr",
            fontsize=size,
            render_mode=3,
            morph=(pymupdf.Point(x, baseline), pymupdf.Matrix(scale, 1)),
        )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--engine", choices=["auto", "rapidocr", "vision"], default="auto")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--force", action="store_true", help="이미 있는 출력 파일을 덮어쓴다")
    args = parser.parse_args()

    output = args.output or default_output(args.input)
    if output.resolve() == args.input.resolve():
        print("원본과 같은 경로에는 저장할 수 없습니다.", file=sys.stderr)
        return 1
    if output.exists() and not args.force:
        print(f"이미 있습니다: {output}", file=sys.stderr)
        return 1

    engine = args.engine
    if engine == "auto":
        engine = "vision" if platform.system() == "Darwin" and shutil.which("swift") else "rapidocr"

    doc = pymupdf.open(args.input)
    indexes = [i for i in range(doc.page_count) if len(doc[i].get_text().strip()) < MIN_PAGE_CHARS]
    if not indexes:
        print(json.dumps({"status": "skipped", "reason": "이미 글자 정보가 있습니다", "input": str(args.input)}, ensure_ascii=False))
        return 0

    font_path = find_font()
    with tempfile.TemporaryDirectory() as folder:
        paths = render(doc, indexes, args.dpi, Path(folder))
        pages = ocr_vision(paths) if engine == "vision" else ocr_rapid(paths)

    for index, lines in zip(indexes, pages):
        add_text_layer(doc[index], lines, font_path)
    doc.subset_fonts()
    doc.save(output, garbage=3, deflate=True)
    doc.close()

    check = pymupdf.open(output)
    chars = sum(len(page.get_text().strip()) for page in check)
    print(
        json.dumps(
            {
                "status": "done",
                "engine": engine,
                "input": str(args.input),
                "output": str(output),
                "pages": check.page_count,
                "ocr_pages": len(indexes),
                "chars": chars,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
