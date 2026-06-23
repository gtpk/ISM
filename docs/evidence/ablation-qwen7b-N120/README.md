# Evidence — 6.1 Dictionary Ablation, dev scale-up N=120 (3×40 shards)

N=40 dev pilot의 scale-up. LLM 압축기(purity 1.0) + 내용 변경형 corruption, 3개 샤드(40문서)
+ resume/cache로 실행 후 병합(paired evaluation, N=240 문항).

| 항목 | 값 |
|---|---|
| config | [configs/experiments/ablation_qwen7b.yaml](../../../configs/experiments/ablation_qwen7b.yaml) (120 docs, 7 conditions) |
| config_hash | `c907f84068de6c99d79f5b298abb7c56a0e4056013545b1d9fcd1c199c15f07c` |
| commit | `87e216e` · Tesla T4 · 3616s (~60min, 3 shards + merge) |
| 압축 | **120/120 (실패 0)**, mean_attempts 1.008 |
| 규모 | 120 docs × 2q × 7 conditions = 1680 predictions, 0 errors, N=240 문항 |

## 결과 (병합, N=240)

| 조건 | Accuracy | AR | CR |
|---|---:|---:|---:|
| Full Context | 0.750 | 1.000 | 1.000 |
| Full Symbol + Dict | 0.446 | 0.594 | 0.745 |
| Corrupted Dict (derange) | 0.375 | 0.500 | 0.745 |
| Flipped Dict (flip) | 0.367 | 0.489 | 0.745 |
| Blank Dict | 0.250 | 0.333 | 0.215 |
| Symbol Only | 0.413 | 0.550 | 0.079 |
| Random Symbol | 0.304 | 0.406 | 0.738 |

| Contrast | 의미 | estimate | 95% CI | McNemar p |
|---|---|---:|---:|---:|
| Δmap_derange | label-binding (보조) | +0.071 | [−0.021, 0.163] | 0.159 |
| **Δmap_flip** | **semantic-content (primary)** | **+0.079** | **[0.013, 0.146]** | **0.032** |
| **Δsymbol** | symbolic-structure | **+0.108** | **[0.050, 0.167]** | **0.0005** |

## 성공 기준 점검 (사용자 사전 정의)

1. compression_success ≥95% → **100% (120/120)** ✓
2. rule_coverage ≈1.00 → ✓ (압축기 gate, mean_attempts 1.008)
3. self_containment ≈1.00 → ✓ (gate 강제)
4. Δmap_derange ≈0 재현 → +0.071, CI가 0 포함, p=0.16 (비유의, label-binding null) ✓
5. **Δmap_flip>0이고 CI가 0 위로 좁아짐 → +0.079, CI [0.013, 0.146], p=0.032 ✓✓** (N=40 p=0.12 → N=240 p<0.05)
6. **Δsymbol>0 재현 → +0.108, p=0.0005 ✓✓✓**

## 해석

dev scale-up에서 construct-valid contrast 두 개가 모두 유의해졌다.
- 사전의 **의미 내용**이 사용된다(flip이 성능을 떨어뜨림, p=0.032).
- **심볼 구조**가 무작위를 능가한다(p=0.0005).
- 라벨 순열(derangement)은 비유의(p=0.16) — 부록 A.1대로 label-binding만 측정.

이는 부록 A의 사전등록 기준 #2(amended: Full+Dict > Flipped AND Symbol Only > Random)를
dev scale-up에서 충족한다. 단 N=240은 full registered scale(dev 5k)이 아니므로 최종 확정은
아니다(full scale은 압축 batching 등 추가 컴퓨트 필요).

## 재현
```bash
# Colab GPU (T4), commit 87e216e
for off in 0 40 80; do
  python -m ism run-ablation --config configs/experiments/ablation_qwen7b.yaml \
    --output artifacts/runs/ablation120/shard$((off/40)) --doc-offset $off --doc-count 40 --resume
done
python -m ism merge-ablation --config configs/experiments/ablation_qwen7b.yaml \
  --output artifacts/runs/ablation120/merged \
  --shards artifacts/runs/ablation120/shard0 .../shard1 .../shard2
```
