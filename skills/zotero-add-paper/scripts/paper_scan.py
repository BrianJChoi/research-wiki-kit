# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24"]
# ///
"""PDF 논문을 훑어 글자 유무, 언어, DOI, Crossref 값을 JSON으로 정리한다.

사용법:
    uv run paper_scan.py <PDF 또는 폴더> [--out paper-scan.json] [--no-crossref]

같은 --out 파일로 다시 실행하면 이미 훑은 파일은 건너뛴다.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pymupdf

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)
DOI_LINE_RE = re.compile(r"10\.\d{4,9}/[^\n]{1,80}", re.IGNORECASE)
HANGUL_RE = re.compile(r"[가-힣]")
MIN_TEXT_CHARS = 200
SCAN_PAGES = 3


def find_pdfs(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*") if p.suffix.lower() == ".pdf" and not p.name.startswith("."))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_doi(raw: str) -> str:
    return raw.rstrip(".,;)")


def find_dois(doc: pymupdf.Document) -> list[str]:
    """DOI 후보를 찾는다. OCR이 끼워 넣은 공백을 지운 후보도 함께 낸다."""
    # 참고문헌의 다른 논문 DOI를 집지 않도록 파일 정보와 앞 2쪽만 본다.
    meta = doc.metadata or {}
    sources = [meta.get(key) or "" for key in ("subject", "keywords", "title")]
    sources += [doc[i].get_text() for i in range(min(2, doc.page_count))]
    found: list[str] = []
    for text in sources:
        strict = [clean_doi(m) for m in DOI_RE.findall(text)]
        joined = []
        for line in DOI_LINE_RE.findall(text):
            match = DOI_RE.match(re.sub(r"\s+", "", line))
            if match:
                joined.append(clean_doi(match.group(0)))
        for doi in strict + joined:
            if doi not in found:
                found.append(doi)
    return found


def crossref(doi: str) -> dict | None:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    request = urllib.request.Request(url, headers={"User-Agent": "research-wiki-kit/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            work = json.load(response)["message"]
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None
    first = lambda key: (work.get(key) or [None])[0]
    return {
        "type": work.get("type"),
        "title": first("title"),
        "original_title": first("original-title"),
        "journal": first("container-title"),
        "volume": work.get("volume"),
        "issue": work.get("issue"),
        "pages": work.get("page"),
        "date": ((work.get("issued") or {}).get("date-parts") or [[None]])[0],
        "issn": work.get("ISSN"),
        "language": work.get("language"),
        "publisher": work.get("publisher"),
        "authors": [
            {"family": a.get("family"), "given": a.get("given"), "name": a.get("name")}
            for a in work.get("author", [])
        ],
    }


def scan(path: Path, use_crossref: bool) -> dict:
    entry = {"path": str(path.resolve()), "name": path.name, "sha256": file_hash(path)}
    try:
        doc = pymupdf.open(path)
    except Exception as error:  # 손상된 PDF도 목록에는 남긴다
        entry.update(status="error", error=str(error))
        return entry
    with doc:
        sample = "".join(doc[i].get_text() for i in range(min(SCAN_PAGES, doc.page_count)))
        chars = len(sample.strip())
        entry.update(
            status="scanned",
            pages=doc.page_count,
            text_chars=chars,
            needs_ocr=chars < MIN_TEXT_CHARS,
            korean=len(HANGUL_RE.findall(sample)) > chars * 0.2 if chars else None,
            doi=None,
        )
        candidates = find_dois(doc)
    if candidates:
        entry["doi"] = candidates[0]
    if use_crossref:
        for doi in candidates[:4]:
            work = crossref(doi)
            time.sleep(0.2)
            if work:
                entry.update(doi=doi, crossref=work)
                break
    return entry


def route(entry: dict) -> str:
    if entry.get("status") == "error":
        return "실패"
    if entry["needs_ocr"]:
        return "OCR 필요"
    if entry["doi"] and entry.get("crossref") and entry["korean"] is False:
        return "자동 등록"
    return "Claude 판독"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--out", type=Path, default=Path("paper-scan.json"))
    parser.add_argument("--no-crossref", action="store_true")
    args = parser.parse_args()

    if not args.target.exists():
        print(f"찾을 수 없습니다: {args.target}", file=sys.stderr)
        return 1

    done = {}
    if args.out.exists():
        done = {e["sha256"]: e for e in json.loads(args.out.read_text(encoding="utf-8")).get("papers", [])}

    papers = []
    for path in find_pdfs(args.target):
        known = done.get(file_hash(path))
        entry = known if known and known.get("status") != "error" else scan(path, not args.no_crossref)
        entry["route"] = route(entry)
        papers.append(entry)
        args.out.write_text(json.dumps({"papers": papers}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{entry['route']}] {path.name} | DOI: {entry.get('doi') or '없음'}")

    counts: dict[str, int] = {}
    for entry in papers:
        counts[entry["route"]] = counts.get(entry["route"], 0) + 1
    print(f"\n총 {len(papers)}편: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"결과 파일: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
