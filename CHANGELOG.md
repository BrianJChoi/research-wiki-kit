# 변경 기록

## 0.3.1

- 스캔본 OCR 사본에서 하이라이트가 다른 단으로 넘어가던 문제를 고쳤습니다. 줄 위치로 단과 덩어리를 찾아 사람이 읽는 순서로 글자 층을 씁니다. 1·2·3단과 제목·초록·그림 설명이 단을 가로지르는 쪽을 처리합니다. Apple Vision과 RapidOCR에 같이 적용됩니다.
- 하이라이트 띠가 글자보다 위로 뜨던 문제를 고쳤습니다. 숨은 글자의 높이를 OCR이 본 줄 높이에 맞춥니다.
- 0.3.0까지 만든 `_ocr.pdf` 사본은 그대로입니다. 다시 만들어야 고쳐집니다.
- 생성 PDF 회귀 시험을 함께 넣었습니다. `uv run tests/run.py`로 전체 시험을 돌립니다.

## 0.3.0

- paper-note, research-search, storm-perspectives를 추가했습니다.
- wiki-setup, ingest, query로 연구 위키의 생성·반영·질문을 지원합니다.
- manuscript-draft, cite-check, manuscript-export로 아웃라인→근거 확인→Word 흐름을 지원합니다.
- kit-update는 최신 정식 릴리스만 확인하며 백업 후 교체합니다.
- 공용 폴더 규칙, APA CSL, Obsidian 인용 필터와 Word 일반 양식 세 개를 추가했습니다.
- 기존 zotero-add-paper의 실행 코드는 유지합니다. Windows 실기 시험 여부와 Mac 시험 범위는 릴리스 시험 기록을 확인합니다.
