# v0.3.0 시험 기록

2026-11-05 KST, Mac에서 확인했습니다. 새 스킬 10개와 기존 zotero-add-paper를 합쳐 11개입니다. 시험 기록은 배포한 구현의 범위이며 Windows 성공을 의미하지 않습니다.

## 자동 시험

- `python -m unittest discover -s tests -v`: 16개 통과.
- 세 Word 양식, 영어 APA 인용과 한국어 본문 언어 유지, Pandoc 구·신 위키 링크 표현, 콜아웃·일반 링크·강조, 없는 키의 경고 및 종료 코드 2를 확인했습니다.
- 원고·bib·기존 출력 보존, 키트 업데이트의 백업·버전 일치·경로 검증·롤백·다운그레이드 방지·정식 릴리스 태그 선택을 확인했습니다. 네트워크 부분은 응답 대역을 사용했습니다.
- 스킬 frontmatter 검증 11/11 통과. `claude plugin validate` 통과. 선택 항목인 아이콘이 없다는 경고는 남습니다.

## 실제 도구 시험

- Pandoc 3.8.3, Better BibTeX `zotero.lua` revision 5904ae6을 사용했습니다.
- 실제 Zotero 항목을 읽어 메타데이터·BibTeX·주석·노트 조회를 확인했습니다. 선택한 항목에는 하이라이트와 코멘트가 없었습니다. 서재에는 쓰지 않았습니다.
- 고정 방식은 `lang: ko-KR`에서도 `(Tian et al., 2024)`와 참고문헌을 생성했습니다. 합성 서지이며 실존 논문인 것처럼 배포하지 않습니다.
- Zotero 방식의 Word에 `ADDIN ZOTERO_ITEM` 필드 2개가 생성됐습니다. Mac Word에서 Refresh 후 `(Su et al., 2026)`으로 바뀌고 Add/Edit Bibliography로 `ZOTERO_BIBL` 참고문헌 필드가 생성됐습니다. 문서별 APA 7·English (US)를 확인했습니다.
- Zotero의 없는 키도 `@…: not found` 경고와 종료 코드 2로 보고했습니다.
- Word 출력물을 별도 LibreOffice 프로필로 렌더링해 한글·문단·인용 표시를 눈으로 확인했습니다. 기본 Word 인용 placeholder는 Refresh 전까지 남는 것이 정상입니다.
- arXiv와 Crossref 실제 요청이 응답했습니다. Consensus 연결은 이 시험에 없어 fallback했습니다. OpenAlex·Semantic Scholar의 개인 키와 강사 키는 사용하지 않았습니다.

## 독립 스킬 실습

wiki-setup·paper-note·ingest·query·manuscript-draft·cite-check를 별도 표본 볼트에서 지시 문서에 따라 수동 실행했습니다. 실제 Zotero 읽기부터 논문 노트, 개념 2개, INDEX 근거 답변, 5절 한국어 프로포절과 인용 검증까지 수행했습니다. 기존 인용 3개·키 1개는 초록의 근거 범위로 확인하고, 일반화한 주장과 가짜 키에는 검증 표시를 남겼습니다. 기존 원문·규칙·템플릿·아웃라인의 해시가 유지됐고 중복 논문 노트와 깨진 파일·절 링크는 없었습니다. references.bib가 없으면 생성했다고 꾸미지 않고 미연결로 보고했습니다.
이 시험은 Codex의 격리 수동 실습이며 Claude Desktop의 스킬 자동 선택·인식이나 사용자 확인 대화 시험은 아닙니다.

표본 볼트의 research-search와 storm-perspectives를 실행했습니다. Consensus가 없는 환경에서 arXiv·Crossref·Zotero·웹으로 진행했고, 원문 3편의 방법·결과·한계를 확인한 리포트와 3관점 Light 결과를 저장했습니다. 연구자 확인이 없는 판단은 잠정 합성으로 표시했습니다. OpenAlex의 무키 검색 안내가 남아 있던 지침 충돌과 선택 경로의 조건 문장을 발견해 수정했습니다.
전체 키트 압축본으로 별도 시험 설치본의 0.2.1→0.3.0 업데이트와 기존 파일의 백업을 실제 실행했습니다. 사용자 설치본은 바꾸지 않았습니다.

## 남은 실기 시험

- Windows Code 탭에서 전체 11개 스킬 인식과 MCP 연결, PowerShell·한글 사용자명·공백 경로.
- Windows Pandoc 3.13과 Word의 Zotero Refresh·참고문헌·PDF 저장.
- 무료 Consensus 계정의 실제 검색 한도와 Windows Code 탭에서의 커넥터 노출.
- 실제 색별 주석·코멘트가 있는 Zotero 항목으로의 paper-note 시험과 수강생 Claude Pro 한도 리허설.
- 기존 zotero-add-paper의 Zotero 쓰기 시험은 하지 않았습니다. 해당 실행 스크립트는 이번 릴리스에서 바꾸지 않았습니다.

## 배포 범위

`release/v0.3.0`에서 준비했습니다. main·team/dev와 수업 전 사전 설치 v0.2.1은 유지합니다. 폴더 구조는 공용 참고 파일의 기본안이며 기존 볼트를 자동 재편하지 않습니다. 실제 수강생 환경의 미검증 항목은 수업 전 리허설에서 확인합니다.
