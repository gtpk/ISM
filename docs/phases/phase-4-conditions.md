# Phase 4 완료 보고서: Condition orchestration

## 1. 목표

Phase 4의 목표는 정확도 계산 전에 모든 질문과 실험 조건이 완전하고 동일하게 정렬됐는지 검증하는
condition matrix와 audit artifact를 만드는 것이다.

구현 범위:

- gold graph 기반 deterministic ISM compression
- full context, ISM 파생, summary/baseline method 분리
- 문서별 source compression linkage
- condition completeness와 paired question alignment audit
- input hash와 token count 기록
- 3문서 golden condition run
- `audit-conditions` 로컬 CLI

## 2. 핵심 계약

- `full_context`는 compression을 만들거나 참조하지 않는다.
- `full_symbol_dict`, `symbol_only`, `corrupted_dict`, `random_symbol`은 같은 문서의 원본 ISM
  compression ID를 공유한다.
- intervention은 Phase 2 구현을 재사용하며 condition builder가 의미론을 다시 구현하지 않는다.
- `model_summary` 등 비교군은 ISM과 다른 method와 compression ID를 사용한다.
- 모든 `(question_id, condition)`은 정확히 한 번 존재한다.
- 모든 condition의 question ID 집합은 완전히 동일하다.
- audit 실패 시 prediction/metric 단계로 진행하지 않는다.

## 3. 통과한 TC

| TC | 결과 |
|---|---|
| P4-CON-001 condition completeness | 통과 |
| P4-CON-002 paired question alignment | 통과 |
| P4-CON-003 source compression linkage | 통과 |
| P4-CFG-001 duplicate condition rejection | 통과 |
| P4-FUN-001 full context compression bypass | 통과 |
| P4-FUN-002 model summary method 분리 | 통과 |
| P4-IO-001 audit count와 실제 record 일치 | 통과 |
| P4-REG-001 3문서 input hash golden | 통과 |
| missing condition audit rejection | 통과 |
| `audit-conditions` CLI | 통과 |

Phase 0-3 회귀를 포함한 자동 테스트는 총 93개다.

## 4. 검증 결과

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright src tests
.venv/bin/pytest -m "not gpu and not network"
.venv/bin/python -m ism audit-conditions \
  --config configs/experiments/smoke.yaml \
  --output /tmp/ism-phase4-audit.json
```

```text
Ruff: all checks passed
Formatting: 44 files already formatted
Pyright: 0 errors, 0 warnings
Pytest: 93 passed
Smoke compressions: 3
Smoke condition inputs: 18
Colab/GPU/API calls: 0
```

3문서 golden input hash:

```text
87847a88f39f6414c5a490a05298554c45e5907480b9eeff2a445eac2133840c
```

## 5. 알려진 제한

- 현재 ISM compression은 gold graph를 deterministic text로 렌더링한 local oracle 구현이다.
- unseen swap condition은 아직 label family 변환 전이며 Phase 7에서 실제 swap을 연결한다.
- summary/baseline은 현재 budget 길이의 deterministic text truncation placeholder다.
- condition artifact는 입력 hash와 linkage를 검증하지만 실제 model prediction은 Phase 3 runner와
  아직 하나의 ablation CLI로 결합하지 않았다.

## 6. Phase 5 진입 조건

- 모든 configured condition record가 질문별 정확히 1개
- condition별 question ID 집합 동일
- ISM 파생 조건의 source linkage 일치
- full context compression 우회 확인
- golden input hash 고정
- 미해결 Blocking 오류 0

Phase 5에서는 동일 budget matrix, tokenizer identity, budget enforcement, regeneration 상한,
method-budget audit를 구현한다.

## 7. Git 상태

이 보고서는 Phase 4 구현 직후, 해당 구현을 독립 커밋하기 전에 작성되었다.
