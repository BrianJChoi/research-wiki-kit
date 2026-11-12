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
import math
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

MIN_PAGE_CHARS = 30
GUTTER_BINS = 400
GUTTER_MIN = 0.01  # 단 사이 여백으로 볼 최소 폭(쪽 너비 비율)
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


def middle(line: dict) -> float:
    return (line["y0"] + line["y1"]) / 2


def by_rows(lines: list[dict]) -> list[dict]:
    """단이 없는 덩어리는 위에서 아래로, 높이가 겹치는 줄끼리는 왼쪽부터 읽는다."""
    rows: list[list[dict]] = []
    for line in sorted(lines, key=lambda item: item["y0"]):
        if rows:
            last = rows[-1]
            top, bottom = min(item["y0"] for item in last), max(item["y1"] for item in last)
            overlap = min(bottom, line["y1"]) - max(top, line["y0"])
            if overlap > 0.5 * min(bottom - top, line["y1"] - line["y0"]):
                last.append(line)
                continue
        rows.append([line])
    return [line for row in rows for line in sorted(row, key=lambda item: item["x0"])]


def find_gutter(lines: list[dict]) -> tuple[list[dict], list[dict], list[dict]] | None:
    """단 사이 세로 여백을 찾아 (왼쪽, 오른쪽, 여백을 가로지르는 줄)로 나눈다. 없으면 None.

    덩어리 폭 안에서 가장 적은 줄이 지나가는 세로 띠를 여백 후보로 본다. 제목·초록·그림 설명처럼
    단을 가로지르는 줄이 있으면 그 줄을 빼고도 양쪽에 단이 나란히 서 있을 때만 여백으로 인정한다.
    """
    left_edge = min(line["x0"] for line in lines)
    right_edge = max(line["x1"] for line in lines)
    step = (right_edge - left_edge) / GUTTER_BINS
    if step <= 0:
        return None
    cover = [0] * GUTTER_BINS
    for line in lines:
        first = max(int((line["x0"] - left_edge) / step), 0)
        last = min(math.ceil((line["x1"] - left_edge) / step) - 1, GUTTER_BINS - 1)
        for index in range(first, last + 1):
            cover[index] += 1
    # 가장자리는 짧은 줄 끝이나 들여쓰기 때문에 늘 비어 보이므로 안쪽에서만 찾는다.
    # 지나가는 줄이 같은 구간을 후보로 삼고, 지나가는 줄이 적은 후보부터 넓은 순서로 따져 본다.
    inner = range(GUTTER_BINS // 10, GUTTER_BINS - GUTTER_BINS // 10)
    runs, start = [], inner.start
    for index in range(inner.start + 1, inner.stop + 1):
        if index == inner.stop or cover[index] != cover[start]:
            runs.append((start, index - 1))
            start = index
    for first, last in sorted(runs, key=lambda run: (cover[run[0]], run[0] - run[1])):
        low, high = left_edge + first * step, left_edge + (last + 1) * step
        crossing = [line for line in lines if line["x0"] < high and line["x1"] > low]
        left = [line for line in lines if line["x1"] <= low]
        right = [line for line in lines if line["x0"] >= high]
        if not left or not right:
            continue
        if min(line["x0"] for line in right) - max(line["x1"] for line in left) < GUTTER_MIN:
            continue
        if crossing:
            # 한 단 글에서 짧은 줄이 우연히 여백처럼 보이는 경우를 막는다. 양쪽 단이 나란히 있어야 한다.
            side_by_side = min(max(line["y1"] for line in left), max(line["y1"] for line in right)) - max(
                min(line["y0"] for line in left), min(line["y0"] for line in right)
            )
            if len(left) < 2 or len(right) < 2 or side_by_side <= 0:
                continue
        return left, right, crossing
    return None


def reading_order(lines: list[dict]) -> list[dict]:
    """줄 상자 위치만 보고 사람이 읽는 순서로 줄을 정렬한다.

    엔진마다 줄을 돌려주는 순서가 다르다. RapidOCR는 위에서 아래로만 정렬해 2단의 좌우 줄이 섞이고,
    그 순서대로 글자 층을 쓰면 Zotero에서 왼쪽 단을 하이라이트할 때 오른쪽 단까지 잡힌다.
    단 사이 여백을 찾으면 왼쪽 단부터 읽고, 단을 가로지르는 줄은 그 위아래 덩어리 사이에 둔다.
    1단·2단·3단과 제목이 한 단인 쪽을 같은 방식으로 처리한다.
    """
    if len(lines) < 2:
        return list(lines)
    split = find_gutter(lines)
    if split is None:
        return by_rows(lines)
    left, right, crossing = split
    if not crossing:
        return reading_order(left) + reading_order(right)
    ordered, rest = [], left + right
    for line in sorted(crossing, key=middle):
        above = [item for item in rest if middle(item) < middle(line)]
        rest = [item for item in rest if middle(item) >= middle(line)]
        ordered += reading_order(above) + [line]
    return ordered + reading_order(rest)


def add_text_layer(page: pymupdf.Page, lines: list[dict], font_path: str) -> None:
    page.insert_font(fontname="ocrkr", fontfile=font_path)
    font = pymupdf.Font(fontfile=font_path)
    # 글자 상자는 글꼴의 위아래 높이로 정해지고 하이라이트 띠도 이 상자로 그려진다.
    # 글꼴 높이를 OCR이 본 줄 높이에 맞춰야 띠가 글자 위나 아래로 밀리지 않는다.
    ascender, descender = font.ascender, font.descender
    if ascender - descender <= 0:
        ascender, descender = 0.88, -0.12
    width, height = page.rect.width, page.rect.height
    for line in reading_order(lines):
        text = line["text"].strip()
        if not text:
            continue
        x = line["x0"] * width
        box_height = (line["y1"] - line["y0"]) * height
        size = max(box_height / (ascender - descender), 3)
        baseline = line["y1"] * height + descender * size
        text_width = font.text_length(text, fontsize=size) or 1
        scale = (line["x1"] - line["x0"]) * width / text_width
        point = pymupdf.Point(x, baseline)
        page.insert_text(
            point,
            text,
            fontname="ocrkr",
            fontsize=size,
            render_mode=3,
            morph=(point, pymupdf.Matrix(scale, 1)),
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
    if doc.needs_pass:
        print("암호가 걸렸거나 DRM으로 보호된 PDF라서 처리할 수 없습니다.", file=sys.stderr)
        return 1
    indexes = [i for i in range(doc.page_count) if len(doc[i].get_text().strip()) < MIN_PAGE_CHARS]
    if not indexes:
        print(json.dumps({"status": "skipped", "reason": "이미 글자 정보가 있습니다", "input": str(args.input)}, ensure_ascii=False))
        return 0

    # 회전이 지정된 스캔본은 보이는 모습을 유지한 채 회전을 풀어 좌표를 단순하게 맞춘다.
    for index in indexes:
        if doc[index].rotation:
            doc[index].remove_rotation()

    font_path = find_font()
    with tempfile.TemporaryDirectory() as folder:
        paths = render(doc, indexes, args.dpi, Path(folder))
        if engine == "vision":
            try:
                pages = ocr_vision(paths)
            except (subprocess.CalledProcessError, ValueError):
                # 맥의 swift는 Xcode 도구가 없으면 실행되지 않으므로 RapidOCR로 넘어간다.
                engine = "rapidocr"
        if engine == "rapidocr":
            pages = ocr_rapid(paths)

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
