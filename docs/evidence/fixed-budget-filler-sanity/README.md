# Evidence — filler artifact sanity (RQ3)

6.3 long smoke의 "model_summary AR>1(full_context 초과)"이 진짜 요약 우위인지, 아니면 긴 중립
filler가 full_context 추론을 방해한 artifact인지 분리하는 소규모 점검.

| 항목 | 값 |
|---|---|
| commit | `2405314` · Tesla T4 · 824s |
| 설정 | 같은 10 문서, budget 256, methods=full_context+model_summary, 문서길이 3종 |

## 결과 (N=10 docs / 20 문항)

| profile | full_context 토큰 | full_context acc | model_summary acc | gap (summary−full) |
|---|---:|---:|---:|---:|
| none | 132 | 0.75 | 0.70 | **−0.05** |
| mid  | 409 | 0.85 | 1.00 | +0.15 |
| long | 1262 | 0.70 | 0.95 | **+0.25** |

## 해석

- summary 정확도는 문서 길이와 거의 무관(~0.85)하지만, full_context는 길어질수록 상대적으로
  뒤처진다. **gap이 문서 길이에 따라 단조 증가(−0.05 → +0.15 → +0.25)** 한다.
- **filler가 없을 때(none) summary는 full_context를 이기지 못한다(−0.05).** 따라서 long smoke의
  "summary AR>1(full_context 초과)"은 **상당 부분 중립 filler가 full_context 추론을 방해한
  artifact**다 — "요약이 본질적으로 더 강하다"가 아니다.
- 단, 이는 summary vs full_context 비교에 대한 것이다. summary vs ISM(둘 다 filler를 제거)
  비교는 별개이며, 더 큰 N의 pilot에서 확인한다.

## 함의

§9.3은 "동일 예산에서 ISM이 요약보다 토큰 효율이 낮다"를 **단정하지 않고**, full-context
degradation/filler artifact 가능성을 명시한 채 신중히 서술한다. ISM의 차별점은 순수 효율보다
inspectability/intervention(6.1)에 있다는 해석을 우선한다.

## 재현
```bash
for cfg in fixed_budget_qwen7b fixed_budget_qwen7b_mid fixed_budget_qwen7b_long; do
  python -m ism run-fixed-budget --config configs/experiments/$cfg.yaml \
    --output artifacts/runs/sanity_$cfg --doc-count 10 --budgets 256 \
    --methods full_context model_summary
done
```
