# Research Wiki Kit

Zotero, Obsidian, Claude로 연구 시스템을 만드는 분을 위한 스킬 모음입니다.

## 들어 있는 스킬

**`zotero-add-paper`**: PDF를 읽어 바로 인용할 수 있는 Zotero 항목으로 등록합니다.

- DOI가 있으면 Crossref 값과 PDF를 대조합니다
- DOI가 없는 한국어 논문은 PDF에서 서지 정보를 읽어 등록합니다
- 이미지 PDF에 보이지 않는 글자를 얹어 검색할 수 있게 만듭니다
- 본문의 `[1]` 같은 번호와 참고문헌을 클릭으로 오갈 수 있게 PDF 내부 링크를 넣습니다
- 폴더를 통째로 처리하고, 값마다 출처를 보고합니다

## 필요한 것

- Zotero 10 이상
- Claude Desktop의 Code 탭 또는 Claude Code
- [uv](https://docs.astral.sh/uv/)
- [Zotero MCP](https://github.com/54yyyu/zotero-mcp): `uv tool install zotero-mcp-server --python 3.12`

플러그인이 Zotero MCP 서버를 자동으로 연결합니다. 이미 같은 서버를 연결해 두었다면 그 설정이 우선합니다. 처음 등록할 때 Zotero 창에 뜨는 쓰기 승인에서 "Always Allow"를 눌러 주세요.

## 설치

**방법 1. 폴더 복사 (터미널 없이)**

[v0.2.1 zip](https://github.com/BrianJChoi/research-wiki-kit/archive/refs/tags/v0.2.1.zip)을 받아 압축을 풀고, `research-wiki-kit-0.2.1` 폴더 이름을 `research-wiki-kit`로 바꿔 `~/.claude/skills/` 아래에 넣은 뒤 Claude를 다시 시작합니다. Windows에서는 `%USERPROFILE%\.claude\skills\`입니다.

**방법 2. Claude Code 터미널**

```text
/plugin marketplace add BrianJChoi/research-wiki-kit
/plugin install research-wiki-kit@brain-trinity
```

## 쓰는 법

Claude에게 이렇게 말하면 됩니다.

> 이 PDF를 Zotero에 등록해 줘.

> 이 폴더의 논문을 전부 등록해 줘.

## 상태

시험판입니다. 맥에서 시험했고 Windows는 시험 중입니다. AI가 읽은 서지 값은 원문과 대조해 주세요.

## 만든 사람

자기개발자 BC (Brain Trinity)

## 라이선스

MIT. 실행할 때 내려받는 도구는 각자의 라이선스를 따릅니다 (PyMuPDF: AGPL-3.0, RapidOCR: Apache-2.0).
