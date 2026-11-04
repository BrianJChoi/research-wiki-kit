---
name: manuscript-export
description: "Obsidian Markdown 원고를 Pandoc으로 Word로 내보냅니다. Word 내보내기, 원고 export, Zotero 인용 필드 또는 고정 참고문헌을 요청할 때 사용합니다. 한국 학술지 일반형, 영문 IMRaD, 프로포절 양식과 APA 영어 인용을 지원합니다."
---

# 원고를 Word로 내보내기

## 공용 경로

먼저 이 스킬 파일에서 상대 경로 `../../references/vault-layout.md`를 읽고, 대상 볼트의 `CLAUDE.md`와 함께 적용합니다. 아래 경로 예시는 공용 표의 역할을 뜻하며 사용자 규칙이 우선합니다.

먼저 원고와 공용 규칙을 읽고 인용 방식·양식을 정합니다. 사용자가 지정하지 않았으면 원고의 manuscript_format을 따르고, 양식이 없으면 proposal을 씁니다. 인용 방식은 고정 방식(fixed)을 기본으로 안내합니다.

## 준비

- `pandoc --version`으로 확인합니다. 수업 기준은 Windows 3.13, Mac 시험 환경은 시험 기록을 봅니다.
- `uv`는 사전 설치 도구입니다. Python이 따로 없어도 `uv run --python 3.12`로 아래 스크립트를 실행합니다. 경로는 항상 따옴표로 감쌉니다.
- 스크립트와 assets는 현재 실행 중인 스킬의 실제 경로에서 찾습니다.
- 원고·기존 docx·bib를 덮어쓰지 않습니다. 출력 파일이 있으면 새 이름을 정합니다.

## 두 방식

**고정 방식:** Zotero가 없어도 됩니다. 공용 표의 references.bib를 사용하며 참고문헌까지 렌더링합니다.

```text
uv run --python 3.12 "<스킬 경로>/scripts/export_manuscript.py" "<원고.md>" --mode fixed --bibliography "<references.bib>" --format korean --output "<새 원고.docx>"
```

**Zotero 방식:** Zotero와 Better BibTeX가 켜져 있어야 합니다. 키를 로컬 서재에서 읽어 Word에 `ADDIN ZOTERO_ITEM` 필드를 넣습니다. 서재를 바꾸지 않습니다. `--citeproc`을 함께 쓰지 않습니다.

```text
uv run --python 3.12 "<스킬 경로>/scripts/export_manuscript.py" "<원고.md>" --mode zotero --format korean --output "<새 원고.docx>"
```

format은 `korean`, `imrad`, `proposal` 중 하나입니다. 세 양식은 일반 서식이며 공식 투고 양식이 아닙니다.
스크립트는 Obsidian 위키 인용을 Cite로 변환하고 다른 링크를 표시 글자로, 콜아웃 표식을 제거합니다. `[[@key]]`와 `[[경로/@key|별칭]]`를 인용으로 인식하며 `[@key, p. 5]`도 유지합니다.
고정 방식은 `english-citations.lua`에서 인용 처리 동안만 lang을 en-US로 바꾸고 Pandoc의 citeproc을 실행한 뒤 원고의 lang을 복원합니다. 한국어 원고의 `lang: ko-KR`에서도 `Tian et al., 2024`를 사용하며 Word 본문 언어는 한국어로 유지합니다. 이 필터를 쓸 때 `--citeproc`을 추가로 실행하지 않습니다.

## 결과 확인

1. 원고 옆에 생긴 `<출력.docx>.warnings.txt`와 터미널 결과를 읽습니다. `Citeproc: citation … not found`, Zotero의 `@…: not found`를 사용자에게 키별로 보여 줍니다. 경고가 있으면 '검증 완료'로 말하지 않습니다.
2. Zotero 방식은 Word에서 Zotero → Refresh → Add/Edit Bibliography를 실행하도록 안내합니다. 필드가 들어간 것과 Word Refresh가 성공한 것은 별도 시험입니다. Word가 없으면 고정 방식을 사용합니다.
3. 출력 경로, 방식, 양식, 미해결 키를 보고합니다. PDF는 Word의 PDF 저장으로 만듭니다. LaTeX는 별도 선택 작업입니다.

필터 출처·라이선스와 APA CSL의 수정점은 키트 루트 NOTICE.md와 assets의 LICENSE 파일을 봅니다.
