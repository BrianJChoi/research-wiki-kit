# Research Wiki Kit

Zotero, Obsidian, Claude로 **논문 PDF에서 Word 원고까지** 이어지는 연구 시스템을 만드는 Claude 스킬 모음입니다. 한국어 논문을 기본으로 두고 Mac과 Windows에서 씁니다. 자기개발자 BC (Brain Trinity)가 만듭니다.

```text
PDF 등록 → 논문 노트 → 연구 위키 → 문헌 검색·관점 탐색 → 원고 초안 → 인용 점검 → Word
```

## 무엇을 하나요

말로 요청하면 Claude가 맞는 스킬을 골라 씁니다. 스킬 11개를 단계별로 묶었습니다.

### 문헌 모으기

| 스킬 | 하는 일 |
|---|---|
| zotero-add-paper | PDF를 읽어 바로 인용할 수 있는 Zotero 항목으로 등록합니다. DOI가 없는 한국어 논문, 스캔본(OCR), 폴더 일괄 등록, 본문의 번호 인용 → 참고문헌 내부 링크를 처리합니다. |
| paper-note | Zotero의 서지·하이라이트·코멘트·노트를 읽어 Obsidian 논문 노트(`Literature/@인용키.md`)를 만듭니다. 하이라이트는 색 규칙으로 묶고, 내 생각 칸은 비워 둡니다. |
| research-search | 연구 주제를 Consensus → arXiv → Crossref → 내 Zotero → 웹 순서로 찾아 출처가 달린 리포트로 저장합니다. OpenAlex·Semantic Scholar는 개인 키가 있을 때만 씁니다. |
| storm-perspectives | 한 주제를 서로 다른 관점 3~4개로 조사해 합의점·충돌점과 연구 갭 후보를 정리합니다. |

### 연구 위키

| 스킬 | 하는 일 |
|---|---|
| wiki-setup | 기존 자료를 보존하면서 볼트에 위키 뼈대(폴더, INDEX, log, 운영 규칙)를 만듭니다. 만들기 전에 승인을 받습니다. |
| ingest | 논문 노트와 웹 클리핑에서 오래 쓸 지식만 뽑아 위키 개념 페이지로 정리하고 INDEX와 log를 갱신합니다. |
| query | 위키와 논문 노트를 근거로 출처를 달아 답합니다. 위키에 없는 내용은 지어내지 않습니다. |

### 원고 쓰기

| 스킬 | 하는 일 |
|---|---|
| manuscript-draft | 내가 쓴 아웃라인과 연결된 근거 노트로 Markdown 초안을 씁니다. 한국 학술지 일반형, 영문 IMRaD, 리서치 프로포절 양식을 지원합니다. |
| cite-check | 원고의 주장을 Zotero의 실제 근거와 대조하고 Better BibTeX 인용 키를 붙입니다. 근거가 없으면 문장을 바꾸지 않고 TODO로 표시합니다. |
| manuscript-export | Pandoc으로 Word를 만듭니다. 고정 참고문헌 방식과 Word에서 새로 고칠 수 있는 Zotero 필드 방식이 있고, APA 인용을 씁니다. |

### 관리

| 스킬 | 하는 일 |
|---|---|
| kit-update | 설치된 버전을 확인하고 GitHub 최신 정식 릴리스로 업데이트합니다. 기존 폴더는 백업하고 실패하면 되돌립니다. |

초안 → 인용 점검 → Word를 나눈 이유: 초안은 Obsidian에서 내가 고칠 원고로 먼저 남기고, 인용 점검은 문장을 바꾸지 않는 검증 단계로, Word 변환은 마지막 단계로 둡니다.

## 0.3.1에서 바뀐 것

- **스캔본 하이라이트:** OCR 사본에서 2단 논문의 한 단을 끌어 하이라이트하면 옆 단까지 칠해지던 문제를 고쳤습니다. 쪽마다 단과 제목·초록 같은 덩어리를 찾아 읽는 순서대로 글자를 넣습니다. 1·2·3단이 섞인 쪽도 처리합니다.
- **하이라이트 위치:** 띠가 글자보다 위로 뜨던 문제를 고쳤습니다.
- 0.3.0까지 만든 `_ocr.pdf` 사본은 다시 만들어야 고쳐집니다. 자세한 내용은 [변경 기록](CHANGELOG.md)을 봅니다.

## 준비물

| | Mac | Windows |
|---|---|---|
| Claude | Claude Desktop의 Code 탭 또는 Claude Code | 같음 |
| Zotero | Zotero와 Better BibTeX | 같음 |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Zotero MCP | `uv tool install zotero-mcp-server --python 3.12` | 같음 |
| Pandoc (Word 내보내기) | `brew install pandoc` | `winget install --id JohnMacFarlane.Pandoc` |
| Obsidian (노트·위키) | 연구 볼트 | 같음 |

- 스크립트는 `uv run`이 필요한 부품을 알아서 받습니다. Python을 따로 설치하지 않아도 됩니다.
- 플러그인은 Zotero MCP(`zotero-mcp serve`, 로컬 Zotero)를 연결합니다. 이미 연결된 서버가 있으면 그 설정을 씁니다.
- Word에서 Zotero 필드를 새로 고치려면 Word와 Zotero Word 플러그인이 필요합니다. 고정 참고문헌 방식은 bib 파일만 있으면 됩니다.

## 설치

### 방법 1. 플러그인으로 설치

Claude Code에서 다음 두 줄을 입력합니다.

```text
/plugin marketplace add BrianJChoi/research-wiki-kit
/plugin install research-wiki-kit@brain-trinity
```

이 방법은 저장소 기본 브랜치(main)를 따릅니다. 특정 버전으로 고정하려면 방법 2를 씁니다.

### 방법 2. 릴리스 압축본으로 설치 (버전 고정)

1. [최신 릴리스](https://github.com/BrianJChoi/research-wiki-kit/releases/latest)에서 소스 압축본(zip)을 받아 풉니다.
2. 풀린 폴더 이름을 `research-wiki-kit`로 바꿉니다.
3. 아래 위치에 넣습니다. 같은 이름의 폴더가 있으면 먼저 다른 이름으로 백업합니다.
   - Mac: `~/.claude/skills/research-wiki-kit`
   - Windows: `%USERPROFILE%\.claude\skills\research-wiki-kit`
4. **새 대화를 엽니다.** 열려 있던 대화는 새 스킬을 읽지 않습니다.

### 업데이트

v0.3.0 이상이 설치되어 있으면 Claude에게 이렇게 말합니다.

> 연구 키트 업데이트해 줘

kit-update가 최신 정식 릴리스를 받아 백업 후 교체합니다. 끝나면 새 대화를 엽니다. v0.2.1에는 kit-update가 없으므로 방법 2로 설치합니다.

## 이렇게 요청합니다

> 이 PDF를 Zotero에 등록해 줘. 스캔본이면 검색되게 해 줘.

> 이 논문의 하이라이트로 논문 노트를 만들어 줘.

> 연구 볼트에 위키 구조와 템플릿을 만들어 줘.

> 이 논문 노트를 위키에 반영해 줘.

> 생성형 AI 글쓰기 교육에 대한 선행연구를 찾아 줘.

> 이 아웃라인으로 프로포절 초안을 만들고 인용을 확인해 줘.

> 이 원고를 고정 참고문헌 방식의 Word로 내보내 줘.

폴더 이름은 [공용 규칙](references/vault-layout.md) 한 곳에서 관리합니다. 기존 볼트의 규칙을 우선하고, 파일을 자동으로 옮기지 않습니다. 사용자의 판단과 내 생각, 원문을 보존하며, 없는 인용 키와 근거는 TODO로 보여 줍니다.

## OCR 메모

- Mac은 Apple Vision, Windows는 RapidOCR로 스캔본에 보이지 않는 글자를 얹습니다. 원본은 그대로 두고 `<이름>_ocr.pdf` 사본을 만듭니다.
- Windows는 첫 실행 때 한국어 인식 모델과 부품을 내려받아 몇 분 걸릴 수 있습니다.
- RapidOCR는 한국어 띄어쓰기를 자주 놓칩니다. 서지 값은 OCR 글자보다 쪽 이미지를 보고 확인합니다.

## 확인 범위

자동 시험은 `uv run tests/run.py`로 돌립니다. [시험 안내](tests/README.md)에 자동 시험, 사람이 확인한 범위, 아직 실기기에서 확인하지 못한 항목을 나눠 적었습니다. Mac에서 확인한 것과 Windows·Word·Zotero 리더에서 확인할 것을 구분합니다. 고치지 않은 기존 PDF 도구의 알려진 문제는 시험에 예상 실패로 남아 있습니다.

## 라이선스

직접 작성한 코드는 MIT입니다. [NOTICE](NOTICE.md)에 서드파티의 저작자·수정점·라이선스를 기록했습니다. APA CSL은 CC BY-SA 3.0이며 키트 전체의 MIT와 별도입니다. 실행 중 내려받는 PyMuPDF(AGPL-3.0), RapidOCR(Apache-2.0) 등은 각자의 조건을 따릅니다. 논문 PDF와 비상업 조건 자료는 포함하지 않습니다.
