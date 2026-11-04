---
name: kit-update
description: "설치된 Research Wiki Kit 버전을 확인하고 GitHub 최신 정식 릴리스 태그의 압축본으로 업데이트합니다. 키트 업데이트, 연구 키트 새 버전 설치, kit update를 요청할 때 사용합니다. main이나 개발 브랜치로 업데이트하지 않습니다."
---

# 연구 키트 업데이트

## 공용 경로

먼저 이 스킬 파일에서 상대 경로 `../../references/vault-layout.md`를 읽고, 대상 볼트의 `CLAUDE.md`와 함께 적용합니다. 아래 경로 예시는 공용 표의 역할을 뜻하며 사용자 규칙이 우선합니다.

1. 이 스킬의 실제 위치에서 키트 루트와 `.claude-plugin/plugin.json`을 찾고 현재 버전을 읽습니다. 복사 설치 기본 위치는 Mac `~/.claude/skills/research-wiki-kit`, Windows `%USERPROFILE%\.claude\skills\research-wiki-kit`입니다.
2. 프로젝트 저장소나 플러그인 캐시에 있는 파일을 설치 폴더로 오인하지 않습니다. 이 도구는 폴더 복사 설치용입니다. 기본 위치가 아니면 사용자가 지정한 복사 설치 폴더인지 확인합니다. 플러그인 관리자 설치는 이 스크립트로 바꾸지 않고 설치 방식을 보고합니다.
3. `uv`와 네트워크를 확인하고 아래 명령을 실행합니다. 별도 Python 설치는 필요 없습니다.

```text
uv run --python 3.12 "<스킬 경로>/scripts/update_kit.py" --check
uv run --python 3.12 "<스킬 경로>/scripts/update_kit.py"
```

명확한 업데이트 요청이면 확인을 반복하지 않고 실행합니다. 스크립트는 GitHub `releases/latest`에서 정식 태그를 읽고, 해당 태그 zip의 이름·버전·필수 파일·경로를 검증한 후 교체합니다. main, draft, prerelease는 받지 않습니다. 기존 버전보다 낮거나 같은 버전은 설치하지 않습니다. 기존 폴더는 timestamp 백업으로 남기고 실패하면 되돌립니다.
4. 이전/새 버전, 바뀐 스킬, 백업 위치와 오류 여부를 보고합니다. 완료 후 반드시 **새 대화를 여세요**라고 안내합니다.
5. 네트워크 실패나 권한 거절은 기존 설치본을 유지하고 보고합니다. Zotero 설정과 연구 볼트는 수정하지 않습니다.

오프라인 수업 시험은 `--archive <태그 zip> --expected-version 0.3.0 --target <시험 폴더/research-wiki-kit>`을 사용합니다. 이 옵션은 검증된 태그 zip에만 사용합니다. 설치본 직접 수정은 백업에 보존되며 새 버전에 자동 병합하지 않습니다.
