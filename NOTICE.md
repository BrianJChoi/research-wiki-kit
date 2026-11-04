# 서드파티와 라이선스

키트의 직접 작성 부분은 MIT, Copyright (c) 2026 BC (Brain Trinity)입니다. 원저작자의 조건은 아래 별도 라이선스가 우선합니다.

## storm-perspectives

Brad Trnavsky, storm-fusion-research-pipeline v0.3.0, MIT, Copyright (c) 2026 Brad Trnavsky.
출처: https://github.com/bmtrnavsky/storm-fusion-research-pipeline
`skills/storm-perspectives/LICENSE`에 원문을 보존했습니다. 한국어, 기본 Light 모드, 3~4개 관점과 연구 갭 후보, 사용자 확인과 연구 볼트 경로로 고쳤습니다.
방법 출처: STORM (Shao et al., NAACL 2024), Co-STORM (Jiang et al., EMNLP 2024). 논문 PDF나 구현 코드는 넣지 않았습니다.

## zotero.lua

Better BibTeX, Emiliano Heyns, MIT. 필터 자체의 Copyright (c) 2020 Emiliano Heyns 표기를 그대로 보존합니다.
받은 곳: https://retorque.re/zotero-better-bibtex/exporting/zotero.lua
공식 설명: https://retorque.re/zotero-better-bibtex/exporting/pandoc/
받은 날: 2026-11-05, 필터 표시 revision `5904ae6`. 원문 그대로 포함했습니다. 필터에 번들된 lunajson 코드도 포함됩니다. lunajson의 MIT 허가와 Copyright (c) 2015-2017 Shunsuke Shimizu (grafi) 표기는 assets/LICENSE-lunajson.txt에 보존합니다. 출처: https://github.com/grafi-tt/lunajson
라이선스: `skills/manuscript-export/assets/LICENSE-zotero.txt`와 필터 안의 허가 문구를 확인합니다.

## APA Style 7th edition CSL

출처: https://github.com/citation-style-language/styles/blob/master/apa.csl
CSL Style Authors. 저작자·기여자 목록과 원문 권리 표기를 apa.csl의 info에 보존했습니다.
라이선스: CC BY-SA 3.0, https://creativecommons.org/licenses/by-sa/3.0/
받은 날: 2026-11-05. 수정: style 루트에 `default-locale="en-US"`를 추가하고 연락용 email 요소 두 개를 제거했습니다. 저작자 이름·URI·권리 표기는 유지했습니다. 이 수정본도 CC BY-SA 3.0입니다.
원문 라이선스는 `skills/manuscript-export/assets/LICENSE-apa.txt`에 있습니다.

## Word 일반 양식

Pandoc 기본 reference.docx를 바탕으로 A4·문단·제목·한글 글꼴·참고문헌 들여쓰기를 지정했습니다. Pandoc이 생성한 출력물의 이용은 Pandoc 라이선스의 제한을 받지 않습니다: https://pandoc.org/FAQs.html
한국 학술지 일반형과 프로포절은 맑은 고딕 11pt·1.5줄, 영문형은 Times New Roman 12pt·2줄이며 동아시아 글꼴은 맑은 고딕입니다. 특정 학술지 공식 양식이 아닙니다.

## 포함하지 않은 것

논문 PDF, 비상업 조건의 academic-research-skills, 계정·토큰·개인 키를 넣지 않았습니다. Zotero MCP와 외부 API·커넥터는 사용자 환경에서 연결합니다. 기존 PDF 처리 도구가 실행 중 받는 PyMuPDF·RapidOCR 등은 각자 라이선스가 적용됩니다.

- `zotero.lua` SHA-256: `fc439b3122155feac8d4027132e6d98e53daf6be128925309cd12535b776ab94`

- `apa.csl` SHA-256: `1f71876e72f0a5739d93efbf609185a39fb083736168ed0e4d9d0ab63bdfa71a`
