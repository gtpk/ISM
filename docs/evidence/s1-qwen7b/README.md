# Evidence — S1 smoke (Qwen2.5-7B-Instruct 4-bit)

GPU 실행 경로(S1)의 재현 가능한 증거. 산출물 원본과 체크섬, 실행 환경, 재현 절차를 보관한다.

## 결과 요약

| 항목 | 값 |
|---|---|
| run_id | `s1-qwen7b` |
| config | [configs/experiments/s1_qwen7b.yaml](../../../configs/experiments/s1_qwen7b.yaml) |
| config_hash | `fe0c0667cfd3df2198f65add086cdbe13e20edd475f8a205f799277ea56c1bb7` |
| code commit | `3b772b4c25e02f4a9366c4b67cc56da398554f40` |
| documents / questions | 5 / 10 |
| predictions | 30 (= 5 docs × 2 questions × 3 conditions) |
| successful / errors | 30 / 0 |
| **accuracy** | **0.70** (21/30, exact-match after normalization) |
| 소요 | 105s (모델 캐시 상태, 생성만) / 최초 1258s (다운로드 포함) |
| GPU | Tesla T4 15360 MiB (driver 580.82.07) |

조건별: full_context / full_symbol_dict / symbol_only 모두 동일 입력(현 파이프라인은 reasoner QA만 수행, 압축 경로 미연동 — [phase-3b](../phases/phase-3b-transformers-backend.md) 참조).

오답 사례(형식 아님, 실제 추론 오류):
- `syn_dev_000000_q01` boolean: expected `False`, raw `True`
- `syn_dev_000004_q00` classification: expected `MEDIUM`, raw `HIGH`
- `syn_dev_000004_q01` boolean: expected `False`, raw `True`

## 파일

| 경로 | 내용 |
|---|---|
| `predictions.jsonl` | 30개 예측 레코드 원본 (Colab 산출물 그대로) |
| `metrics.json` | 파이프라인 요약 지표 |
| `manifest.json` | run 메타데이터 (config_hash, backend, seed, …) |
| `SHA256SUMS` | 위 세 파일의 sha256 |
| `environment.json` | commit, python, GPU, 핵심 패키지 버전 |

체크섬 검증:
```bash
cd docs/evidence/s1-qwen7b && shasum -a 256 -c SHA256SUMS
```

## 재현 절차

로컬(게이트):
```bash
uv sync --dev && uv run pytest -q
uv run ism dry-run --config configs/experiments/s1_qwen7b.yaml   # config_hash == fe0c0667...
```

Colab(GPU 런타임, T4 이상):
```bash
git clone --depth 1 https://github.com/gtpk/SESC.git && cd SESC
git checkout 3b772b4          # 이 증거를 생성한 커밋
pip install -e ".[gpu]"       # torch는 Colab 제공본 사용
python -m ism run --config configs/experiments/s1_qwen7b.yaml --output artifacts/runs/s1 --batch-size 1
```

재현성 참고:
- decoding은 greedy(`temperature=0`, `do_sample=False`) + per-request `manual_seed(42)`로 결정적이지만, 4-bit 양자화 커널·하드웨어(GPU 모델/드라이버)·transformers 버전이 다르면 부동소수점 차이로 소수 토큰이 달라질 수 있다. 정확한 바이트 재현은 위 `environment.json`과 동일 스택에서만 보장한다.
- 이 산출물은 `accuracy=0.0`이던 최초 실행 이후 **프롬프트 제약 + 정답 정규화**(commit `3b772b4`)를 적용해 재생성한 것이다.
