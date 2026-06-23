# ADR 0002 — QASPER 채점 규약

- 상태: 채택 (Accepted)
- 날짜: 2026-06-23
- 동기: [논문 실험 갭 분석](../reviews/paper-experiment-gaps.md) A2
- 관련 코드: [src/ism/evaluation/qasper_metrics.py](../../src/ism/evaluation/qasper_metrics.py), [src/ism/data/qasper.py](../../src/ism/data/qasper.py)

## 배경

논문 §5.1·§8.4는 모든 데이터셋을 "Accuracy / Accuracy Retention"으로만 기술한다.
그러나 QASPER는 자유형(extractive/abstractive) 답변과 yes/no, unanswerable이 섞여
있어 단순 exact-match accuracy로 채점하면 안 된다. QASPER 원논문(Dasigi et al., 2021)은
**answer-F1**(토큰 단위)을 표준 지표로 사용한다. 현재 어댑터([qasper.py](../../src/ism/data/qasper.py))는
네 가지 answer type을 매핑하지만 **채점 함수가 없었다.**

## 결정

QASPER 예측은 **token-level answer-F1**으로 채점한다.

1. **정규화(SQuAD 방식):** 소문자화 → 구두점 제거 → 관사(a/an/the) 제거 → 공백 정규화.
2. **token-F1:** 예측·정답 토큰의 다중집합 교집합으로 precision/recall/F1 계산.
   한쪽이 비고 다른 쪽이 비지 않으면 0, 둘 다 비면 1.
3. **다중 정답:** 질문마다 여러 주석자 정답이 있으므로 **정답들에 대한 최대 F1**을 취한다.
4. **Unanswerable:** 정답이 unanswerable이면 예측이 "no-answer"(정규화 결과가 빈 문자열
   또는 `unanswerable`)일 때 F1=1, 아니면 0. 반대로 정답이 존재하는데 예측이 no-answer면 0.
5. **yes/no:** 단일 토큰이므로 token-F1이 사실상 exact-match로 동작한다.
6. **집계:** 질문별 answer-F1의 평균을 주 지표로 보고하고, **answer type별
   (extractive/abstractive/yes_no/unanswerable) 분해**를 함께 보고한다.
7. **AR(QASPER):** \(AR = F1_{method} / F1_{full}\). Full Context F1이 사전 최소 기준
   미만인 경우 §7.3대로 주 분석에서 제외하고 sanity result로만 제시한다.

Synthetic Rule-QA는 폐쇄형 단일 라벨이므로 기존 exact-match
([evaluation/answers.py](../../src/ism/evaluation/answers.py))를 유지한다. 즉 데이터셋별로
채점 방식이 다르며, 이를 논문 §7.1에 명시한다.

## 범위

- 이 ADR은 **채점 함수와 그 정의**를 확정한다. QASPER를 `ism run` 파이프라인에
  end-to-end로 연결(다중 정답 sample 구성, 조건별 실행)하는 작업은 별도 후속이다.
- 따라서 본 변경은 순수 metric + 단위 테스트로 한정한다.

## 영향

- 논문 §5.1(데이터셋), §7.1(지표), §8.4(QASPER 결과)에 채점 규약·answer type 분해·
  unanswerable 처리를 명시한다.
- 새 모듈 `qasper_metrics`는 torch/네트워크 의존이 없고 순수 함수이므로 L0/L1에서 검증된다.
