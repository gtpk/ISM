# Evidence — Experiment 6.1 Dictionary Ablation (dev pilot)

RQ1 조건별 ablation의 **예비** 결과. 등록 규모(dev 5k)가 아닌 소규모 dev 파일럿이다.

## 설정

| 항목 | 값 |
|---|---|
| config | [configs/experiments/ablation_qwen7b.yaml](../../../configs/experiments/ablation_qwen7b.yaml) |
| config_hash | `204d4b4b7061495dce29d7fa86021deacd8e94be5ac0cc885e403ca6e239f00f` |
| code commit | `40a23b937782f6839b9d3a589adea324ef2a2fea` |
| 모델 | Qwen2.5-7B-Instruct 4-bit (prompt-only), greedy, seed 42, T4 |
| 규모 | 20 docs × 2 questions × 5 conditions = 200 predictions (0 errors), N=40 문항 |
| ISM 출처 | **gold rule graph로부터 결정적 생성** (논문 §3.3의 LLM 압축기가 아님) |
| 소요 | 189.9s |

## 결과

| 조건 | Accuracy | AR | CR | ES |
|---|---:|---:|---:|---:|
| Full Context | 0.700 | 1.000 | 1.000 | 1.000 |
| Full Symbol + Dict | 0.550 | 0.786 | 0.818 | 0.960 |
| Corrupted Dict | 0.550 | 0.786 | 0.818 | 0.960 |
| Symbol Only | 0.225 | 0.321 | 0.061 | 5.304 |
| Random Symbol | 0.250 | 0.357 | 0.811 | 0.441 |

사전등록 대비:
- **Δmap** = Acc(Full+Dict) − Acc(Corrupt) = **0.000**, 95% CI [0.000, 0.000], McNemar p=1.0 (n=40)
- **Δsymbol** = Acc(SymbolOnly) − Acc(Random) = **−0.025**, 95% CI [−0.075, 0.000], McNemar p=1.0 (n=40)

## 해석 (예비)

- Full Symbol+Dict와 Corrupted Dict가 **문항별로 완전히 동일한 정오답**(discordant=0)을 냈다.
  → 이 설정에서 모델은 **사전 정의 내용을 기능적으로 사용하지 않았다**.
- Symbol Only가 Random Symbol을 능가하지 못했다(Δsymbol ≤ 0).
- 따라서 논문 부록 A의 사전등록 기준 #2(Full+Dict > Corrupt, Symbol Only > Random)는
  **이 파일럿에서 충족되지 않는다.** 논문 §9.4가 예상한 실패 결과 범주에 해당한다.

### 강한 한계 (결론 전 반드시 해소)

1. **gold-derived ISM**: 현재 압축은 gold rule graph를 그대로 직렬화한 것이고, 논문 메인
   설정인 **LLM 압축기 산출물이 아니다.** 표현 형식·자연스러움이 다르다.
2. **규모**: N=40, 단일 seed. 등록 규모(dev 5k, paired bootstrap)가 아니다.
3. **비교군 누락**: model_summary/keyword_extract/llmlingua_2는 스텁이라 제외.
4. CR=0.061인 Symbol Only의 ES=5.30은 §10(넷째 한계)대로 작은 CR에서 과대해지는 값이다.

이 결과는 **파이프라인이 실제 신호를 산출함을 입증**하지만, RQ1에 대한 결론 근거로는
사용하지 않는다.

## 파일

| 경로 | 내용 |
|---|---|
| `ablation_summary.json` | 조건별 AR/CR/ES + Δmap/Δsymbol(CI·McNemar) |
| `condition_audit.json` | 조건별 입력 token 수·input hash (200 레코드) |
| `SHA256SUMS` | 위 파일 + predictions.jsonl(Colab 보관, 200줄) sha256 |
| `environment.json` | commit, GPU |

## 재현

```bash
# Colab GPU (T4+), commit 40a23b9
pip install -e ".[gpu]"
python -m ism run-ablation --config configs/experiments/ablation_qwen7b.yaml \
  --output artifacts/runs/ablation --batch-size 1
```
로컬 plumbing 검증: `uv run ism run-ablation --config configs/experiments/ablation_mock.yaml --output /tmp/abl`
