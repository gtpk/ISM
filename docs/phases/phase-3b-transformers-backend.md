# Phase 3b 보고서: Transformers GPU backend (S1 준비)

## 1. 목표

Phase 3는 `TextGenerator` 계약과 mock/CPU 파이프라인을 구현하고, "실제 Transformers와
GPU model loading은 후속 adapter 범위"로 명시했다. Phase 3b는 그 후속 adapter를
**동일 계약 그대로** 구현해 S1(Colab GPU 최소 smoke)을 실행 가능하게 만든다.

## 2. 구현 파일

| 경로 | 역할 |
|---|---|
| [src/ism/inference/transformers_backend.py](../../src/ism/inference/transformers_backend.py) | 실제 모델 `TextGenerator` (torch/transformers lazy import) |
| [src/ism/inference/factory.py](../../src/ism/inference/factory.py) | `config.model.backend`로 backend 선택 |
| [src/ism/inference/pipeline.py](../../src/ism/inference/pipeline.py) | `run_mock_pipeline` → `run_pipeline` (backend 무관) |
| [src/ism/cli.py](../../src/ism/cli.py) | `ism run` 명령 |
| [configs/experiments/s1_qwen7b.yaml](../../configs/experiments/s1_qwen7b.yaml) | Qwen2.5-7B-Instruct 4-bit, stage S1 |
| [pyproject.toml](../../pyproject.toml) | optional `gpu` extra |
| [tests/test_transformers_backend.py](../../tests/test_transformers_backend.py) | adapter 계약·factory·config TC |

## 3. 설계 결정

- **의존성 격리.** transformers/torch/bitsandbytes는 `gpu` extra이며, `transformers_backend`
  모듈은 이를 `importlib`로 **메서드 내부에서만** import한다. 모듈 import와 전체 테스트
  스위트는 torch 없이 동작한다(계획서의 "domain/data/evaluation은 transformers를 import하지
  않는다", "runner는 구체 model class가 아니라 protocol에 의존" 원칙).
- **torch는 extra에서 제외.** Colab이 CUDA-매칭 torch를 이미 제공하므로 pin하지 않는다.
- **결정성.** `temperature=0`이면 greedy(`do_sample=False`), 요청 seed로 `manual_seed`.
- **실패 격리.** 요청별 try/except로 예외를 `classify_exception`(OOM/transient/validation/
  fatal)에 매핑해 실패 `GenerationResult`로 변환한다. runner의 retry 계약과 그대로 맞물린다.

## 4. 검증 TC (로컬, GPU 불필요)

| TC | 내용 | 결과 |
|---|---|---|
| P3-ARC-003 | adapter 생성이 torch를 import/로딩하지 않음 | pass |
| P3-ARC-004 | factory가 backend별로 올바른 generator 선택 | pass |
| P3-ARC-005 | transformers adapter가 runner에서 mock과 치환 가능 | pass |
| P3-CON-002 | 성공 결과 계약(text/token/latency) | pass |
| P3-ERR-003 | OOM/ValueError 예외 → 실패 결과 분류 | pass |
| (config) | s1_qwen7b.yaml 이 유효한 S1 서버 stage | pass |

전체: `ruff` / `pyright(strict)` / `pytest` 152 passed.

## 5. Colab/GPU 사용

- 로컬에서는 GPU 호출 0. 실제 GPU 로드·1 batch 검증은 Colab S1에서 수행한다.
- 실행: `pip install -e ".[gpu]"` 후 `ism run --config configs/experiments/s1_qwen7b.yaml
  --output artifacts/runs/s1`.
- S1 config_hash(로컬): `fe0c0667cfd3df2198f65add086cdbe13e20edd475f8a205f799277ea56c1bb7` —
  Colab에서 동일해야 한다(COL-ENV-004, [ADR 0001](../decisions/0001-config-hash-is-deployment-independent.md)).

## 6. 남은 작업

- **S1 실제 실행**: Colab GPU 런타임에서 노트북 cell 3–4 실행(모델 다운로드 ~5GB).
- compressor/ISM 압축 단계는 현재 `run` 파이프라인이 reasoner 단일 QA만 수행한다. 압축
  경로 연동은 후속(S2 이전) 범위.
