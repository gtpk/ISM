# Phase 5 완료 보고서: Fixed-budget orchestration

## 1. 목표

Phase 5의 목표는 모든 압축 method를 동일 budget과 tokenizer 경계에서 비교하고, 예산 초과 출력을
절단하지 않은 채 제한된 재생성 후 명시적 failure로 기록하는 것이다.

## 2. 구현 계약

- 모든 method는 동일한 budget 집합을 사용한다.
- token count는 외부 reasoning prompt를 제외한 representation text만 측정한다.
- run 안의 모든 artifact는 동일 tokenizer revision을 기록한다.
- 유효 artifact의 token count는 반드시 budget 이하이다.
- 초과 출력은 자르지 않고 최대 attempt까지 producer를 다시 호출한다.
- 최대 attempt 뒤에도 초과하면 마지막 원문, token count, attempt 수, 오류를 보존한다.
- `(document, method, budget)` 조합은 정확히 한 번 존재해야 한다.

## 3. 통과한 TC

| TC | 결과 |
|---|---|
| P5-CFG-001 method별 동일 budget 집합 | 통과 |
| P5-FUN-001 유효 artifact budget enforcement | 통과 |
| P5-FUN-002 공통 prompt 제외 count | 통과 |
| P5-FUN-003 max regeneration attempt | 통과 |
| P5-CON-001 tokenizer revision identity | 통과 |
| P5-CON-002 method-budget matrix 완전성 | 통과 |
| P5-REG-001 token count와 matrix digest golden | 통과 |
| `audit-budgets` CLI | 통과 |

Phase 0-4 회귀를 포함한 자동 테스트는 총 101개다.

## 4. 검증 결과

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright src tests
.venv/bin/pytest -m "not gpu and not network"
.venv/bin/python -m ism audit-budgets \
  --config configs/experiments/smoke.yaml \
  --output /tmp/ism-phase5-budget-audit.json
```

```text
Ruff: all checks passed
Formatting: 46 files already formatted
Pyright: 0 errors, 0 warnings
Pytest: 101 passed
Smoke budget artifacts: 3
Invalid/over-budget artifacts: 0
Colab/GPU/API calls: 0
```

Golden:

```text
Whitespace count("Z1 Z2 !Z3 => HIGH") = 5
Matrix digest = 43d080da51da7face4ef58bc76823e61d5d540161da051f50e78e9fd67023b34
```

## 5. 알려진 제한

- 현재 tokenizer revision `local`은 whitespace counter를 의미하며 실제 model tokenizer가 아니다.
- config는 현재 단일 compression budget만 표현한다. 다중 budget API와 TC는 구현됐지만 YAML
  schema 확장은 main experiment config 작성 시 필요하다.
- deterministic local producer는 예산에 맞게 내용을 재작성하지 않아 작은 budget에서는 failure가
  정상 결과다.
- LLMLingua-2 등 실제 baseline producer는 아직 연결되지 않았다.

## 6. Phase 6 진입 조건

- 동일 method-budget matrix audit 통과
- 유효 artifact budget 초과 0
- tokenizer revision 혼용 거부
- 재생성 무한 루프 없음
- budget failure 원문과 횟수 보존
- 미해결 Blocking 오류 0

Phase 6에서는 질문 독립 compression cache, checksum corruption recovery, 동시 write 안전성,
serving/end-to-end 비용 분리를 구현한다.

## 7. Git 상태

이 보고서는 Phase 5 구현 직후, 해당 구현을 독립 커밋하기 전에 작성되었다.
