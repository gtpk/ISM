# Evidence — 6.1 Dictionary Ablation (LLM compressor + strong corruption)

진단 후속(#1+#1.5+#2 완료) 재실행. 고품질 ISM(purity 1.0) + 내용 변경형 corruption.

| 항목 | 값 |
|---|---|
| config | [configs/experiments/ablation_qwen7b.yaml](../../../configs/experiments/ablation_qwen7b.yaml) (7 conditions) |
| config_hash | `15c72cfd6d4bb6e3b4a3d89ebaa191a804c93746570d89bc19e7551a6cc0e2d8` |
| commit | `7be5618` · Tesla T4 · 644.5s |
| 압축 | 20/20 (실패 0), mean_attempts 1.0 (LLM ISM, purity 1.0) |
| 규모 | 20 docs × 2q × 7 conditions = 280 predictions, 0 errors, N=36–40 |

## 결과

| 조건 | Accuracy | AR | CR |
|---|---:|---:|---:|
| Full Context | 0.700 | 1.000 | 1.000 |
| Full Symbol + Dict | 0.500 | 0.714 | 0.730 |
| Corrupted Dict (derangement) | 0.450 | 0.643 | 0.730 |
| **Flipped Dict (결론 반전)** | **0.325** | 0.464 | 0.730 |
| Blank Dict | 0.225 | 0.321 | 0.206 |
| Symbol Only | 0.450 | 0.643 | 0.070 |
| Random Symbol | 0.250 | 0.357 | 0.722 |

| Contrast | 의미 | estimate | 95% CI | McNemar p |
|---|---|---:|---:|---:|
| Δmap (derangement) | label-binding 민감도 | +0.050 | [−0.175, 0.275] | 0.83 |
| **Δmap_strong (flip)** | **사전 의미내용 민감도** | **+0.175** | [0.000, 0.350] | 0.118 |
| **Δsymbol** | 심볼 구조 vs 무작위 | **+0.200** | [0.075, 0.350] | **0.021** |

## 해석

진단의 두 수정(압축기 purity↑, 내용 변경형 corruption)을 적용하자 신호가 바뀌었다.

- **Δsymbol = +0.20, p=0.021 (유의):** Symbol Only(0.45)가 Random(0.25)을 분명히 능가.
  심볼 관계/구조에 과제 정보가 실재함. 부록 A 기준 #2의 "Symbol Only > Random" 충족.
- **Δmap_strong = +0.175 (CI [0, 0.35], p=0.12, 경향):** 사전 결론을 반전하면 0.50→0.325로
  하락. **사전의 의미 내용이 답을 지탱함**을 시사(N=40이라 경계적 유의).
- **Δmap (derangement) ≈ 0, p=0.83:** 라벨-정의 순열은 영향 없음 → 라벨 자체는 임의적이며
  binding이 아니라 내용이 쓰인다는 점과 일치. derangement는 "label-binding probe"로만 유효.
- Blank Dict(0.225) ≈ Random(0.25): 정의 내용을 비우면 거의 무작위 수준으로 하락.

즉 이전의 "Δmap≈0"은 ISM 가설의 반증이 아니라 (1) 압축 purity 부족 + (2) label-only
derangement의 산물이었다. 수정 후에는 **심볼 구조와 사전 내용이 모두 사용된다는 예비 증거**가
나온다.

## 한계

N=40, 단일 seed로 Δmap_strong은 경계적(p=0.12). 등록 규모(dev 5k) paired evaluation에서
재확인 필요. blank_dict의 CR(0.21)·symbol_only CR(0.07)에서 ES는 §10대로 과대 해석 금지.

## 재현
```bash
# Colab GPU, commit 7be5618
python -m ism run-ablation --config configs/experiments/ablation_qwen7b.yaml \
  --output artifacts/runs/ablation --batch-size 1
```
