# Research Wiki Kit

Zotero, Obsidian, Claude로 연구 시스템을 만드는 분을 위한 스킬 모음입니다.

## 들어 있는 스킬

**`zotero-add-paper`**: PDF를 읽어 바로 인용할 수 있는 Zotero 항목으로 등록합니다.

- DOI가 있으면 Crossref 값과 PDF를 대조합니다
- DOI가 없는 한국어 논문은 PDF에서 서지 정보를 읽어 등록합니다
- 이미지 PDF에 보이지 않는 글자를 얹어 검색할 수 있게 만듭니다
- 폴더를 통째로 처리하고, 값마다 출처를 보고합니다

## 필요한 것

- Zotero 10 이상
- Claude Desktop의 Code 탭 또는 Claude Code
- [uv](https://docs.astral.sh/uv/)
- [Zotero MCP](https://github.com/54yyyu/zotero-mcp) 연결과 로컬 쓰기 승인

## 설치

Claude Code 터미널에서 실행합니다.

```text
/plugin marketplace add BrianJChoi/research-wiki-kit
/plugin install research-wiki-kit@brain-trinity
```

플러그인 없이 쓰려면 `skills/zotero-add-paper` 폴더를 `~/.claude/skills/`에 복사합니다.

## 쓰는 법

Claude에게 이렇게 말하면 됩니다.

> 이 PDF를 Zotero에 등록해 줘.

> 이 폴더의 논문을 전부 등록해 줘.

## 상태

v0.1.0 시험판입니다. 맥에서 시험했고 Windows는 시험 중입니다. AI가 읽은 서지 값은 원문과 대조해 주세요.

## 라이선스

MIT. 실행할 때 내려받는 도구는 각자의 라이선스를 따릅니다 (PyMuPDF: AGPL-3.0, RapidOCR: Apache-2.0).
