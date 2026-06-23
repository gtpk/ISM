# Evidence — compress-audit v2 (conclusion-bearing compressor, commit 71205fe)

압축기 개선(#1: 정의에 조건+결론 강제) 후 재측정. 비교: [v1](../compress-audit-qwen7b-dev/README.md).

| 지표 | v1 (ebc4222) | **v2 (71205fe)** |
|---|---:|---:|
| rule_coverage (purity) | 0.70 | **1.00** |
| self_containment | 0.71 | **1.00** |
| relations_structure | 0.79 | 0.61 |
| compressed | 18/20 | **14/20** |
| failures | 2 | **6 (all empty_relations)** |
| mean_attempts | 1.06 | 1.00 |

**결과:** purity·self_containment가 목표대로 1.0 달성(1차 원인 해소). 단, 결론까지 넣은
사전이 길어져 `max_new_tokens`(256) 안에서 `[RELATIONS]`가 잘려 **empty_relations 실패 6건**
(30%). 실패 6건 모두 동일 원인.

**후속(간단):** 압축 `max_new_tokens`를 키우거나(예: 384–512) 압축 budget을 조정하면 실패율
회복 예상. 그 뒤 6.1 재실행 → Δmap이 여전히 ≈0이면 2차 원인(corruption 설계)을
결론 반전/blanking으로 강화.

샘플(성공) ISM:
```
Z1 := if marker_a = high and marker_b = low then risk = HIGH
Z5 := if repair_score >= 0.8 then exception to r_conjunction risk = LOW
```

## 재현
```bash
# Colab GPU, commit 71205fe
python -m ism compress-audit --config configs/experiments/ablation_qwen7b.yaml --output artifacts/runs/compress_audit
```
