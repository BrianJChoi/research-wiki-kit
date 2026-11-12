# 시험

저장소 루트에서 실행합니다. uv와 Pandoc이 필요합니다.

```text
uv run tests/run.py
```

두 묶음이 함께 돕니다.

- **원고·업데이트(`test_release_tools.py`):** 합성 서지와 임시 볼트를 사용합니다. Zotero에 쓰지 않고, 키나 네트워크 없이 동작합니다. 세 양식의 인용·링크·콜아웃, 미해결 키, 원본 보존과 업데이트의 백업·롤백·압축 경로·릴리스 선택을 확인합니다. 이 묶음만 돌릴 때는 `python -m unittest discover -s tests -p "test_release_tools.py" -v`도 됩니다.
- **PDF 도구(`test_paper_*.py`, `test_pipeline.py`):** 코드로 만든 PDF로 paper_scan·paper_ocr·paper_link를 확인합니다. 실제 논문 PDF는 쓰지 않습니다. OCR 엔진 자리에는 정답 줄을 넣고, 엔진이 돌려주는 줄 순서를 바꿔 가며 글자 층이 단 순서로 들어가는지와 하이라이트 상자가 보이는 줄과 겹치는지 봅니다. 맥에서는 Apple Vision 실제 인식도 돕니다. RapidOCR 실제 인식은 모델을 내려받으므로 `RWK_TEST_RAPIDOCR=1`일 때만 돕니다. 고치지 않은 알려진 문제는 예상 실패로 표시합니다.

이는 Claude가 스킬을 선택하고 판단하는 실습이나 Windows·Word·Zotero 리더 실기 시험을 대신하지 않습니다. 테스트는 Mac과 Windows에서 실행할 수 있으나 실제 실행한 플랫폼만 시험 기록에 적습니다.
