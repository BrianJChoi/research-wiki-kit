---
name: zotero-add-paper
description: PDF 논문을 읽어 바로 인용할 수 있는 Zotero 항목으로 등록한다. 한국어 논문, DOI가 없는 논문, 스캔본, 메타데이터 없이 PDF만 들어온 항목을 처리하고 폴더 일괄 등록도 한다. 사용자가 "이 논문 Zotero에 넣어줘", "논문 등록해줘", "메타데이터 채워줘", "PDF만 들어왔어", "이 폴더 논문 다 넣어줘", "인용할 수 있게 넣어줘", "스캔본 검색되게 해줘"라고 하거나 PDF를 Zotero에 추가하려 하면 반드시 이 스킬을 쓴다.
---

# zotero-add-paper

PDF를 저자, 연도, 제목, 학술지, 권호, 쪽, 인용 키가 갖춰진 Zotero 항목으로 만든다. 이 값들이 정확해야 인용 키, 참고문헌, 인용 검증이 작동한다.

## 시작 전 확인

1. Zotero MCP 도구(`zotero_*`)가 있는지 본다. 없으면 수강 자료의 Zotero MCP 연결 안내를 따르게 하고 멈춘다.
2. Zotero 앱이 켜져 있어야 한다. 꺼져 있으면 켜 달라고 요청한다.
3. `zotero_write_capabilities`로 쓰기 방식을 확인한다. 쓰기가 불가능하면 Zotero 창으로 전환하라고 안내한 뒤 `zotero_authorize_local_writes`를 호출하고, 사용자에게 "Always Allow"를 누르게 한다.

## 대상 나누기

- **PDF 파일이나 폴더**: 새로 등록한다.
- **이미 Zotero에 단독 PDF로 들어온 항목**: `zotero_get_recent`로 첨부 키를 찾는다. PDF를 다시 올리지 않고 새 항목의 하위로 옮긴다.

## 1. 훑기

```text
uv run "${CLAUDE_SKILL_DIR}/scripts/paper_scan.py" "<PDF 또는 폴더>" --out "<작업 폴더>/paper-scan.json"
```

파일마다 글자 유무, 언어, DOI, Crossref 값과 처리 경로가 나온다. 같은 `--out`으로 다시 실행하면 끝난 파일은 건너뛴다.

| 경로 | 뜻 | 다음 단계 |
|---|---|---|
| OCR 필요 | 글자 정보가 없는 이미지 PDF | 2단계 후 다시 훑기 |
| 자동 등록 | 영어 논문, DOI와 Crossref 값 있음 | `zotero_add_item(source=<PDF 경로>, source_type="file", if_exists="file")` |
| Claude 판독 | 한국어이거나 DOI가 없음 | 3단계 |
| 실패 | PDF를 열 수 없음 | 건너뛰고 보고 |

여러 편이면 표를 먼저 보여 주고, **3편까지 등록해 결과를 확인받은 뒤** 나머지를 진행한다. 일괄 등록은 잘못되면 되돌릴 일이 많기 때문이다.

## 2. 글자 입히기

이미지 PDF는 본문 검색이 안 되고 프로그램이 DOI도 읽지 못한다.

```text
uv run "${CLAUDE_SKILL_DIR}/scripts/paper_ocr.py" "<입력.pdf>"
```

원본 옆에 `<이름>_ocr.pdf` 사본이 생긴다. 맥은 Apple Vision, Windows는 RapidOCR를 쓴다. 첫 실행은 모델을 내려받아 오래 걸린다.

- 새 파일은 사본을 등록에 쓴다.
- 이미 Zotero에 연결된 PDF를 교체하는 일은 **사용자 승인을 받은 뒤** 원본을 백업하고 진행한다. 교체 후에는 Zotero에서 이 PDF의 다시 색인(Reindex)을 누르게 안내한다.
- OCR은 틀릴 수 있다. 서지 값은 OCR 글자보다 쪽 이미지를 직접 읽어 확인한다.

## 3. 서지 정보 읽기

앞 2쪽을 읽는다. 머리글과 꼬리글에 학술지명, 권호, 쪽이 있는 경우가 많으므로 3쪽의 머리글과 마지막 쪽도 본다. 글자 정보가 없으면 쪽 이미지를 읽는다.

DOI가 있으면 Crossref 값과 PDF를 대조한다. 한국 학술지는 Crossref에 영문 제목과 로마자 저자만 있고 언어가 `en`으로 잘못 등록된 경우가 있다. 이때 Crossref 값을 그대로 쓰지 말고 아래 규칙을 따른다.

| 필드 | 규칙 |
|---|---|
| 제목 | 본문 언어의 제목. 다른 언어 제목은 `original-title` |
| 저자 | 한국 이름은 `family`에 성, `given`에 이름. 복성은 영문 표기로 판단. 기관 저자는 `literal`. 로마자 표기는 `original-author` |
| 학술지 | 본문 언어의 학술지명. 영문명은 `original-container-title` |
| 날짜 | 근거가 있는 만큼만. 월이나 일이 없으면 넣지 않는다 |
| 권, 호, 쪽 | 숫자만. 쪽은 `428-437` 형식 |
| 언어 | 한국어 논문은 반드시 `ko`. 없으면 인용 스타일이 제목의 `AI`를 `Ai`로 바꾼다 |
| 유형 | `article-journal`, `thesis`, `report`, `paper-conference` 중 선택 |
| 초록 | PDF의 본문 언어 초록을 그대로 |

**없는 값은 비워 둔다.** 근거 없이 채운 메타데이터는 그대로 인용 오류가 된다.

## 4. 등록

파일로 먼저 등록하지 않는다. 파일 이름이 제목인 항목이 생기고 Better BibTeX가 그때 인용 키를 고정할 수 있어서, 처음부터 완전한 값으로 만든다.

`zotero_add_item`에 `source_type="csl_json"`, `if_exists="skip"`으로 CSL JSON을 넣는다.

```json
[{
  "type": "article-journal",
  "title": "대학생의 생성형 AI의 교육적 사용경험 및 인식 탐색 : A대학 사례를 중심으로",
  "original-title": "Exploring College Students' Educational Experiences and Perceptions of Generative AI : The case of A University",
  "author": [{"family": "이", "given": "한샘"}, {"family": "유", "given": "지원"}],
  "original-author": "Lee, Han-Saem; You, Ji-Won",
  "container-title": "한국콘텐츠학회논문지",
  "original-container-title": "Journal of the Korea Contents Association",
  "volume": "24",
  "issue": "1",
  "page": "428-437",
  "issued": {"date-parts": [[2024, 1, 31]]},
  "DOI": "10.5392/JKCA.2024.24.01.428",
  "ISSN": "1598-4877",
  "URL": "https://doi.org/10.5392/JKCA.2024.24.01.428",
  "language": "ko",
  "abstract": "본 연구는 ..."
}]
```

사용자가 컬렉션을 지정했으면 `collections`로 넘긴다. 이어서 PDF를 연결한다.

- 새 파일: `zotero_attach_file(item_key=<새 항목>, file_path=<PDF 또는 OCR 사본>)`
- Zotero의 단독 PDF: `zotero_set_item_parent(item_key=<첨부 키>, parent_key=<새 항목>)`. 첨부가 속해 있던 컬렉션을 새 항목으로 옮긴다

## 5. 인용 키 확인

`zotero_get_item_metadata(format="json")`로 `citationKey`를 읽는다. 한글 저자는 `iEtAl2024`처럼 쓰기 어려운 키가 나올 수 있다.

1. 서재의 다른 키 형식을 따른다. 없으면 `로마자성 + (2인 이상이면 EtAl) + 연도`로 한다. 예: `LeeEtAl2024`
2. `zotero_search_by_citation_key`로 중복을 확인한다.
3. `zotero_update_item(item_key=<항목>, fields={"citation_key": "LeeEtAl2024"})`로 넣는다.

## 6. 확인과 보고

항목을 다시 읽어 필수 값, 첨부 1개, 인용 키를 확인한다. 값의 출처를 표로 보고한다.

| 필드 | 값 | 출처 |
|---|---|---|
| 제목 | ... | PDF 1쪽 |
| 학술지 | ... | PDF 3쪽 머리글 |
| 쪽 | ... | Crossref |

추정이 하나라도 있거나 스캔본에서 읽은 값이 있으면 `확인필요` 태그를 달고, 사용자가 대조할 필드를 짚어 준다.

일괄 등록은 끝에 성공, 확인필요, 실패 수와 실패 사유를 정리한다.

## 하지 말 것

- 원본 PDF를 승인 없이 덮어쓰기
- 없는 값을 지어내기
- 사용자의 다른 항목을 수정하거나 지우기
