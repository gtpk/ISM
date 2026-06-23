# 논문 실험 갭 분석

- 날짜: 2026-06-23
- 대상: [deep-research-report.md](../../deep-research-report.md) (사전등록형 초안)
- 방법: 논문의 RQ1–RQ4·§6 실험·§7 지표를 [ism-system-plan.md](../../ism-system-plan.md)·구현(config 조건 10종)과 대조

## 결론

메인 실험 4종(6.1 Dictionary Ablation, 6.2 Swap, 6.3 Fixed-Budget, 6.4 Reuse)은
설계·구현 모두 존재하며 config 조건(`full_context … unseen_swap_no_dict`)과 1:1로
매핑된다. **핵심 실험 누락은 없다.** 단, 아래 항목이 빠져 있다.

## A. 논문이 약속했으나 §6/§8에 실험·결과가 없는 내부 불일치 (우선 보완)

| # | 항목 | 논문 근거 | 문제 |
|---|---|---|---|
| A1 | 압축기 크기 민감도(1.5B) | §5.2 | §6 실험 섹션·§8 결과표 부재. 약속만 존재 |
| A2 | QASPER 채점 방식·unanswerable | §5.1·§8.4가 "Accuracy/AR"로만 기술 | QASPER 표준은 token-F1 + answer type(extractive/abstractive/boolean/unanswerable). 구현은 normalization을 다루나(plan P8-FUN-001) **논문에 점수 정의·abstention 보고 없음** |
| A3 | 지연/연산 비용 측정 | §7.3(지연 Wilcoxon), §10 한계 | §6·§8에 latency/throughput 실험·표 없음. Reuse는 토큰 비용만 |
| A4 | §7.2 보조 분석 결과 슬롯 | §7.2(purity, 규칙유형 오류, 예외/우선순위 오류, OOD별 AR, 예산별 심볼 수) | §8 결과표(8.1–8.4)에 보고 자리 없음 |

## B. 주장 강화를 위해 추가 권장 (후속/부록 가능)

| # | 항목 | 이유 |
|---|---|---|
| B1 | 교정적(constructive) 개입 | 현 개입은 전부 파괴적(remove/corrupt/random/swap). 헤드라인이 "개입 가능성"인데 오답을 사전 수정→예측 회복하는 양의 개입 실험이 없음 (CBM 계열 §2.3 대비 자연스러운 요구) |
| B2 | Swap 분산/시드 | LoRA 학습(확률적)인데 seed 1개. 학습 반복 변동/CI 없음 |
| B3 | 교차 모델 전이 | 압축기=추론기(Qwen). 압축기 A→추론기 B 전이는 RQ2(암기 아닌 표현) 주장을 강화 |

## 진행 현황 (2026-06-23)

- **A2 — 처리 완료.** [ADR 0002](../decisions/0002-qasper-scoring.md) 확정 + token-F1 metric
  구현([qasper_metrics.py](../../src/ism/evaluation/qasper_metrics.py), 테스트 8) + 논문
  §5.1·§7.1·§8.4 반영. (QASPER를 `ism run`에 end-to-end 연결하는 것은 후속.)
- A1·A3·A4: 미착수. B1–B3: 후속/부록.

## 처리 우선순위와 결정

1. **A2 QASPER 채점 정의 — 최우선.** 외적 타당도 실험의 점수 방식이 미정이면 §8.4 전체가
   흔들린다. → [ADR 0002](../decisions/0002-qasper-scoring.md)에서 채점 규약을 확정하고
   구현·논문에 반영한다.
2. A1(1.5B 민감도), A3(지연 측정), A4(보조 분석 결과표)는 A2 이후 순차 보완.
3. B군은 본문 약속과 충돌하지 않으므로 부록/후속으로 둔다.

각 항목은 "실험 추가" 또는 "본문 약속 문장 제거" 중 하나로 닫아야 하며, A군은 약속이
이미 본문에 있으므로 전자를 기본으로 한다.
