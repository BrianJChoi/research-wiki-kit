# Research Wiki Kit

Zotero, Obsidian, Claude로 문헌에서 원고까지 이어지는 연구 시스템을 만듭니다. 자기개발자 BC (Brain Trinity)가 만듭니다.

## 스킬 11개

| 스킬 | 하는 일 |
|---|---|
| zotero-add-paper | PDF의 서지를 확인해 Zotero에 등록, OCR·번호 인용 링크 |
| wiki-setup | 기존 자료를 보존하며 위키 구조와 템플릿 생성 |
| paper-note | 문헌 한 편의 서지·하이라이트·코멘트, 내 생각은 비워 둠 |
| ingest | 원문 근거로 위키 개념과 INDEX·log 갱신 |
| query | 위키와 노트를 근거로 답변 |
| research-search | 웹·학술 DB·Zotero·내 볼트의 문헌 조사 |
| storm-perspectives | Light 모드 3~4개 관점과 연구 갭 후보 |
| manuscript-draft | 내가 쓴 아웃라인과 연결 노트로 Markdown 원고 |
| cite-check | 주장과 실제 Zotero 근거·키 대조, 미근거 표시 |
| manuscript-export | 고정 참고문헌 또는 Zotero 필드를 넣은 Word |
| kit-update | 최신 정식 릴리스 확인, 백업 후 업데이트 |

## 필요한 것

Claude Desktop Code 탭 또는 Claude Code, Zotero 10 이상과 Better BibTeX, Zotero MCP, uv가 필요합니다. Word 내보내기는 Pandoc을 사용합니다. 수업의 Windows 기준은 Pandoc 3.13입니다. 고정 방식은 bib 파일만 있으면 Zotero를 켜지 않아도 됩니다. Word에서 Zotero 필드를 새로 고치려면 Word와 Zotero Word 플러그인이 필요합니다.
플러그인은 Zotero MCP를 연결합니다. 폴더 복사 설치에서 자동 연결되는지는 설치 환경에 따라 확인해야 합니다. 이미 연결된 서버가 있으면 그 설정을 사용합니다.

## 설치·업데이트

수업 전 설치 안내는 v0.2.1을 유지합니다. v0.3.0은 릴리스 공개 후 [태그 압축본](https://github.com/BrianJChoi/research-wiki-kit/archive/refs/tags/v0.3.0.zip)을 풀어 폴더 이름을 `research-wiki-kit`로 바꾸고 Mac `~/.claude/skills/`, Windows `%USERPROFILE%\.claude\skills\`에 넣습니다. 기존 폴더는 먼저 백업합니다. **새 대화를 여세요.**
플러그인 방식은 `/plugin marketplace add BrianJChoi/research-wiki-kit`와 `/plugin install research-wiki-kit@brain-trinity`입니다. 이 경로는 저장소 기본 브랜치의 배포 상태를 따르므로 v0.3.0을 고정하려면 태그 압축본을 사용합니다.

현재 Claude Code는 `.claude-plugin/plugin.json`이 있는 스킬 폴더를 플러그인으로 읽을 수 있습니다. [공식 스킬 안내](https://code.claude.com/docs/en/skills)를 참고합니다. Windows Code 탭에서 `/research-wiki-kit:paper-note` 등 실제 인식과 권한 승인을 확인합니다. 인식하지 못하면 해당 설치본의 지원 여부를 확인하고 교재의 수동 스킬 복사 절차를 따릅니다.

## 이렇게 요청합니다

> 연구 볼트에 위키 구조와 템플릿을 만들어 주세요.

> 이 논문의 하이라이트로 논문 노트를 만들어 주세요.

> 이 아웃라인과 연결된 노트로 프로포절 초안을 만들고 인용을 확인해 주세요.

> 이 원고를 고정 참고문헌 방식의 Word로 내보내 주세요.

폴더 이름은 [공용 규칙](references/vault-layout.md) 한 곳에서 관리합니다. 기존 볼트의 명시적 규칙을 우선하며 자동 이동하지 않습니다. 사용자의 판단과 내 생각, 원문을 보존합니다. 없는 키와 근거는 TODO로 보여 줍니다.

## 시험과 범위

[시험 안내](tests/README.md)를 확인합니다. 자동 시험과 사람이 확인한 범위, 외부 서비스·Windows·Word 실기 시험을 구분합니다. 기존 PDF 도구의 알려진 문제를 이번 버전에서 고쳤다고 주장하지 않습니다.

## 라이선스

직접 작성한 코드는 MIT입니다. [NOTICE](NOTICE.md)에 서드파티의 저작자·수정점·라이선스를 기록했습니다. APA CSL은 CC BY-SA 3.0이며 키트 전체의 MIT와 별도입니다. 실행 중 내려받는 PyMuPDF(AGPL-3.0), RapidOCR(Apache-2.0) 등은 각자의 조건을 따릅니다. 논문 PDF와 비상업 조건 자료는 포함하지 않습니다.
