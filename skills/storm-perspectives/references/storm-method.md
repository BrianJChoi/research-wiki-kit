# STORM 방법 요약

## 원 논문

- **STORM:** Yijia Shao et al., "Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models", NAACL 2024. Stanford OVAL 연구실. 참고 구현은 `github.com/stanford-oval/storm`입니다.
- **Co-STORM:** Yucheng Jiang et al., "Into the Unknown Unknowns: Engaged Human Learning through Participation in Language Model Agent Conversations", EMNLP 2024. 사람이 AI 전문가들의 대화에 함께 참여하는 확장판입니다.

## 핵심 생각

AI에게 주제를 바로 물으면 질문이 얕고 한쪽으로 치우칩니다. STORM은 먼저 주제를 볼 관점을 여러 개 찾고, 관점마다 질문을 만들어 출처를 찾아가며 답하게 합니다. 관점이 다르면 질문이 달라지고, 질문이 다르면 찾는 출처도 달라집니다.

## 다섯 단계

| 단계 | 하는 일 | 이 스킬에서 |
|---|---|---|
| 1 관점 찾기 | 주제에 필요한 전문가 관점과 날카로운 질문을 정합니다 | 1단계, 출발 편향을 추가로 적습니다 |
| 2 전문가 인터뷰 | 관점마다 질문하고 검색한 출처로 답합니다 | 2단계, Light 모드는 차례로 진행합니다 |
| 3 정리 | 인터뷰를 주제별로 묶고 출처 간 모순을 표시합니다 | 3단계, 충돌 지점을 연구 갭 후보로 씁니다 |
| 4 근거 기반 쓰기 | 정리한 순서대로, 모은 출처만으로 씁니다 | 5단계 |
| 5 점검 | 아무도 묻지 않은 질문과 치우친 출처를 찾습니다 | 6단계 |

## 이 스킬의 바탕이 된 응용판

Brad Trnavsky의 `storm-fusion-research-pipeline` v0.3.0(MIT)은 STORM을 글쓰기와 조사용 에이전트 스킬로 옮기면서 두 가지를 더했습니다.

1. **합성 뒤 사람 확인:** 관점별 결과를 합친 뒤, 정리하기 전에 실무자에게 "맞는가, 무엇이 빠졌는가"를 묻는 단계를 둡니다. 이 스킬의 4단계 "사용자(연구자) 확인"입니다.
2. **점검 역할 강조:** 응용판 설명에 따르면 Co-STORM 평가에서 점검(모더레이터) 역할을 빼는 것이 전문가 수를 줄이는 것보다 결과를 더 나쁘게 만들었습니다. 그래서 마지막 점검 단계를 빼지 않습니다.

응용판은 관점마다 서로 다른 AI 모델 네 개를 함께 돌렸습니다. 이 스킬은 Claude 한 모델로 돌리므로 그 부분은 없습니다. 무엇이 남고 무엇이 빠졌는지는 `SKILL.md`의 "다양성에 대해 솔직하게"에 적었습니다.
