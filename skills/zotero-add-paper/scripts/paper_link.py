# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24"]
# ///
"""본문의 [1] 같은 인용 번호와 참고문헌을 PDF 내부 링크로 잇는다.

본문 번호를 누르면 참고문헌으로 가고, 참고문헌 번호를 누르면 처음 인용한 곳으로 돌아온다.
번호 인용 방식만 지원한다. 원본은 고치지 않고 사본을 만든다.

사용법:
    uv run paper_link.py <입력.pdf> [--output 출력.pdf] [--dry-run]
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

HEADING_RE = re.compile(r"^\s*(참\s*고\s*문\s*헌|references?|bibliography|literature\s+cited)\s*$", re.IGNORECASE)
END_RE = re.compile(r"^\s*(저\s*자\s*소\s*개|about the authors?|author biograph)", re.IGNORECASE)
RUN_RE = re.compile(r"\[[0-9lIOo\[\]\)\}\-–~,;]{1,24}")
ENTRY_NUMBER_RE = re.compile(r"^\s*[\[\(]?\s*([0-9lIOoㅣ기]{1,4})")
ENTRY_DOT_RE = re.compile(r"^\s*(\d{1,3})\.\s+\S")
OCR_CHARS = str.maketrans({"l": "1", "I": "1", "ㅣ": "1", "O": "0", "o": "0", "기": "7", ")": "]", "}": "]"})
HEADER_ZONE = 0.09
MIN_INDENT = 6
MIN_AGREEMENT = 0.7
MAX_EXISTING_LINKS = 5


@dataclass
class Line:
    page: int
    column: int
    text: str
    bbox: tuple
    height: float
    chars: list = field(default_factory=list)

    @property
    def order(self) -> tuple:
        return (self.page, self.column, self.bbox[1])


def read_lines(doc: pymupdf.Document) -> list[Line]:
    lines: list[Line] = []
    for index, page in enumerate(doc):
        middle = page.rect.width / 2
        for block in page.get_text("rawdict")["blocks"]:
            for raw in block.get("lines", []):
                chars = [c for span in raw["spans"] for c in span["chars"]]
                text = "".join(c["c"] for c in chars)
                if not text.strip():
                    continue
                bbox = tuple(raw["bbox"])
                width = bbox[2] - bbox[0]
                column = 1 if bbox[0] >= middle - 5 and width < middle else 0
                lines.append(Line(index, column, text, bbox, page.rect.height, chars))
    lines.sort(key=lambda line: line.order)
    return lines


def find_heading(lines: list[Line]) -> int | None:
    for position in range(len(lines) - 1, -1, -1):
        if HEADING_RE.match(lines[position].text):
            return position
    return None


def find_start(lines: list[Line]) -> int | None:
    """제목을 읽지 못했을 때 [1]로 시작하는 줄을 참고문헌 시작으로 본다."""
    for position in range(int(len(lines) * 0.5), len(lines)):
        if lines[position].text.lstrip().startswith("[1]"):
            return position - 1
    return None


def entry_area(lines: list[Line], start: int) -> list[Line]:
    area = []
    for line in lines[start + 1 :]:
        if END_RE.match(line.text):
            break
        if line.bbox[1] >= line.height * HEADER_ZONE:
            area.append(line)
    return area


def hanging_starts(area: list[Line]) -> list[Line]:
    """내어쓰기 위치로 항목의 첫 줄을 찾는다. OCR이 번호를 틀려도 위치는 남는다."""
    groups: dict[tuple, list[Line]] = {}
    for line in area:
        groups.setdefault((line.page, line.column), []).append(line)
    starts: list[Line] = []
    indented = 0
    for key in sorted(groups):
        left = min(line.bbox[0] for line in groups[key])
        for line in groups[key]:
            if line.bbox[0] - left < MIN_INDENT:
                starts.append(line)
            else:
                indented += 1
    return starts if indented >= len(starts) * 0.5 else []


def number_matches(line: Line, number: int) -> bool | None:
    """첫 줄 번호가 순서와 맞는지 본다. 번호를 읽을 수 없는 줄은 None이다."""
    match = ENTRY_NUMBER_RE.match(line.text)
    if not match:
        return None
    digits = match.group(1).translate(OCR_CHARS)
    if not digits.isdigit():
        return None
    # OCR이 여는 괄호를 1로 읽는 경우가 있어 뒤쪽 숫자까지 인정한다 (15] -> 5, 181 -> 8)
    return str(number) in digits


def collect_entries(lines: list[Line], start: int) -> tuple[dict[int, Line], float]:
    area = entry_area(lines, start)
    starts = hanging_starts(area)
    if not starts:
        starts = [line for line in area if ENTRY_DOT_RE.match(line.text) or line.text.lstrip().startswith("[")]
    entries = {index + 1: line for index, line in enumerate(starts)}
    checks = [number_matches(line, number) for number, line in entries.items()]
    readable = [check for check in checks if check is not None]
    if len(readable) < len(entries) * 0.5:
        return entries, 0.0
    return entries, sum(readable) / len(readable)


def rect_of(line: Line, begin: int, end: int) -> pymupdf.Rect:
    boxes = [line.chars[i]["bbox"] for i in range(begin, min(end, len(line.chars)))]
    rect = pymupdf.Rect(min(b[0] for b in boxes), line.bbox[1], max(b[2] for b in boxes), line.bbox[3])
    if rect.width < 8:
        rect.x0 -= (8 - rect.width) / 2
        rect.x1 = rect.x0 + 8
    return rect


def valid(body: str, total: int) -> list[tuple] | None:
    """쉼표나 범위로 이어진 번호가 모두 참고문헌 범위 안이면 (번호, 시작, 끝) 목록을 낸다."""
    if not re.fullmatch(r"\d+([,;\-–~]\d+)*", body):
        return None
    tokens = [(int(m.group(0)), m.start(), m.end()) for m in re.finditer(r"\d+", body)]
    return tokens if all(1 <= number <= total for number, _, _ in tokens) else None


def repair(body: str, total: int, closed: bool) -> tuple[list[tuple], bool] | None:
    """OCR이 괄호를 숫자 1로 읽은 경우를 참고문헌 개수 안에서만 되돌린다."""
    tokens = valid(body, total)
    if tokens:
        return tokens, False
    if not closed and body.endswith("1") and len(body) > 1:
        fixed = repair(body[:-1], total, True)
        if fixed:
            return fixed[0], True
    for separator in ("11", "1"):
        position = body.find(separator, 1)
        while position != -1:
            left = valid(body[:position], total)
            right_start = position + len(separator)
            right = valid(body[right_start:], total)
            if left and right:
                shifted = [(n, s + right_start, e + right_start) for n, s, e in right]
                return left + shifted, True
            position = body.find(separator, position + 1)
    return None


def collect_citations(lines: list[Line], stop: int, total: int) -> tuple[list[dict], list[str], list[str]]:
    citations: list[dict] = []
    repaired: list[str] = []
    unresolved: list[str] = []
    for line in lines[:stop]:
        for run in RUN_RE.finditer(line.text):
            normal = run.group(0).translate(OCR_CHARS)
            cursor = 0
            for segment in re.finditer(r"\[([^\[]*)", normal):
                raw = segment.group(1)
                closed = "]" in raw
                body = raw.split("]")[0].rstrip(",;-–~")
                if not body:
                    continue
                result = repair(body, total, closed)
                if result is None:
                    unresolved.append(run.group(0))
                    continue
                tokens, fixed = result
                if fixed:
                    repaired.append(f"{run.group(0)} -> {[n for n, _, _ in tokens]}")
                origin = run.start() + segment.start(1)
                for index, (number, begin, end) in enumerate(tokens):
                    rect = rect_of(line, origin + begin, origin + end)
                    citations.append({"number": number, "line": line, "rect": rect})
                    if index + 1 < len(tokens) and re.search(r"[-–~]", body[end : tokens[index + 1][1]]):
                        for middle in range(number + 1, tokens[index + 1][0]):
                            citations.append({"number": middle, "line": line, "rect": None})
    return citations, repaired, unresolved


def link(page: pymupdf.Page, rect: pymupdf.Rect, target: int, point: pymupdf.Point) -> None:
    page.insert_link({"kind": pymupdf.LINK_GOTO, "from": rect, "page": target, "to": point, "zoom": 0})


def default_output(path: Path) -> Path:
    stem = re.sub(r"(\.pdf)+$", "", path.name, flags=re.IGNORECASE)
    return path.with_name(f"{stem}_linked.pdf")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="파일을 만들지 않고 결과만 보여 준다")
    parser.add_argument("--force", action="store_true", help="이미 있는 출력 파일을 덮어쓴다")
    args = parser.parse_args()

    output = args.output or default_output(args.input)
    if output.resolve() == args.input.resolve():
        print("원본과 같은 경로에는 저장할 수 없습니다.", file=sys.stderr)
        return 1
    if output.exists() and not (args.force or args.dry_run):
        print(f"이미 있습니다: {output}", file=sys.stderr)
        return 1

    doc = pymupdf.open(args.input)
    if doc.needs_pass:
        print("암호가 걸렸거나 DRM으로 보호된 PDF라서 처리할 수 없습니다.", file=sys.stderr)
        return 1

    existing = sum(1 for page in doc for item in page.get_links() if item.get("kind") == pymupdf.LINK_GOTO)
    if existing > MAX_EXISTING_LINKS:
        print(json.dumps({"status": "skipped", "reason": f"이미 내부 링크가 {existing}개 있습니다"}, ensure_ascii=False))
        return 0
    if any(page.rotation for page in doc):
        print(json.dumps({"status": "skipped", "reason": "회전이 지정된 PDF입니다. paper_ocr.py를 먼저 실행해 주세요"}, ensure_ascii=False))
        return 0

    lines = read_lines(doc)
    if not any(len(line.text.strip()) > 5 for line in lines):
        print(json.dumps({"status": "skipped", "reason": "글자 정보가 없습니다. paper_ocr.py를 먼저 실행해 주세요"}, ensure_ascii=False))
        return 0

    start = find_heading(lines)
    if start is None:
        start = find_start(lines)
    if start is None:
        print(json.dumps({"status": "skipped", "reason": "참고문헌 위치를 찾지 못했습니다"}, ensure_ascii=False))
        return 0

    entries, agreement = collect_entries(lines, start)
    if len(entries) < 2:
        print(json.dumps({"status": "skipped", "reason": "번호가 붙은 참고문헌을 찾지 못했습니다. 저자-연도 방식일 수 있습니다"}, ensure_ascii=False))
        return 0

    if agreement < MIN_AGREEMENT:
        print(
            json.dumps(
                {"status": "skipped", "reason": "참고문헌 번호를 믿을 수 없어 링크를 만들지 않았습니다", "references": len(entries), "agreement": round(agreement, 2)},
                ensure_ascii=False,
            )
        )
        return 0

    citations, repaired, unresolved = collect_citations(lines, start, max(entries))
    if not citations:
        print(json.dumps({"status": "skipped", "reason": "본문에서 번호 인용을 찾지 못했습니다", "references": len(entries)}, ensure_ascii=False))
        return 0

    first_seen: dict[int, dict] = {}
    forward = 0
    for citation in citations:
        first_seen.setdefault(citation["number"], citation)
        entry = entries.get(citation["number"])
        if entry is None or citation["rect"] is None:
            continue
        forward += 1
        if not args.dry_run:
            point = pymupdf.Point(entry.bbox[0], max(entry.bbox[1] - 6, 0))
            link(doc[citation["line"].page], citation["rect"], entry.page, point)

    back = 0
    for number, entry in entries.items():
        citation = first_seen.get(number)
        if citation is None:
            continue
        back += 1
        if not args.dry_run:
            head = re.match(r"\s*\S{1,5}", entry.text)
            end = head.end() if head else 3
            point = pymupdf.Point(citation["line"].bbox[0], max(citation["line"].bbox[1] - 6, 0))
            link(doc[entry.page], rect_of(entry, 0, end), citation["line"].page, point)

    summary = {
        "status": "dry-run" if args.dry_run else "done",
        "references": len(entries),
        "citation_links": forward,
        "back_links": back,
        "cited_without_reference": sorted({c["number"] for c in citations} - set(entries)),
        "references_never_cited": sorted(set(entries) - {c["number"] for c in citations}),
        "number_agreement": round(agreement, 2),
        "repaired_markers": repaired,
        "unresolved_markers": unresolved,
    }
    if not args.dry_run:
        doc.save(output, garbage=3, deflate=True)
        summary["output"] = str(output)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
