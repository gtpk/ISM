# Phase 0 완료 보고서: 프로젝트 골격

## 1. 목표

Phase 0의 목표는 외부 모델과 GPU 없이 이후 실험을 안전하게 구현할 기반을 만드는 것이었다.

구현 범위:

- `uv` 기반 Python 패키지와 잠금 파일
- 엄격한 실험 설정 schema
- 설정 검증 및 비용 dry-run CLI
- 중복 handler를 만들지 않는 로깅 초기화
- 아키텍처, 설정, CLI, 결정성에 대한 로컬 Blocking TC

논문 가설, synthetic rule 실행기, 실제 모델 추론은 이 Phase의 범위가 아니다.

## 2. 환경

| 항목 | 값 |
|---|---|
| Python | 3.14.3 |
| 패키지 관리 | uv 0.11.2 |
| 가상환경 | 프로젝트 `.venv` |
| 실행 환경 | 로컬 CPU |
| Colab/GPU 사용 | 없음 |

## 3. 구현 파일

| 경로 | 역할 |
|---|---|
| `pyproject.toml` | 패키지, 의존성, Ruff, Pyright, Pytest 설정 |
| `uv.lock` | 재현 가능한 의존성 잠금 |
| `configs/experiments/smoke.yaml` | L2 로컬 smoke 설정 |
| `src/ism/config.py` | Pydantic 설정 모델, 모순 검사, 경로 해석 |
| `src/ism/cli.py` | `validate-config`, `dry-run` 명령 |
| `src/ism/planning.py` | 호출량과 worst-case 실행량 계산 |
| `src/ism/logging.py` | idempotent logger 설정 |
| `tests/` | Phase 0 Blocking TC |

## 4. 구현된 계약

### 설정 계약

- 알 수 없는 키는 `extra=forbid`로 거부한다.
- `split=test`와 `tuning_mode=true`의 조합을 거부한다.
- CPU 실행에서 4-bit GPU 설정을 거부한다.
- 로컬 stage는 `max_gpu_hours=0`이어야 한다.
- 설정의 sample, condition, generation 상한이 실제 실행 범위를 포함해야 한다.
- 상대경로는 config 파일 위치가 아니라 프로젝트 루트를 기준으로 해석한다.

### 비용 계획 계약

- Full Context는 압축 호출을 만들지 않는다.
- Full+Dict, Symbol Only 등 ISM 파생 조건은 문서당 하나의 ISM 압축을 공유한다.
- reasoning 호출은 문서 수, 질문 수, 조건 수, budget 수, seed 수를 모두 반영한다.
- worst-case 호출은 설정된 최대 generation attempt를 반영한다.

## 5. 통과한 TC

| TC | 결과 |
|---|---|
| P0-ARC-001 import boundary | 통과 |
| P0-CON-001 typed config load | 통과 |
| P0-CFG-001 unknown key rejection | 통과 |
| P0-CFG-002 conflicting config rejection | 통과 |
| P0-IO-001 project-root path resolution | 통과 |
| P0-IO-002 idempotent logging | 통과 |
| P0-ERR-001 invalid CLI arguments | 통과 |
| P0-DET-001 byte-identical resolved config | 통과 |
| P0-REG-001 CLI help/validate/dry-run | 통과 |
| ISM compression-family cost regression | 통과 |

자동 테스트는 총 14개다.

## 6. 검증 결과

실행 명령:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright src tests
.venv/bin/pytest -m "not gpu and not network"
.venv/bin/python -m ism dry-run --config configs/experiments/smoke.yaml
```

결과:

```text
Ruff: all checks passed
Formatting: 11 files already formatted
Pyright: 0 errors, 0 warnings
Pytest: 14 passed
```

Smoke dry-run:

```json
{
  "stage": "L2",
  "documents": 3,
  "questions": 6,
  "conditions": 3,
  "compression_calls": 3,
  "reasoning_calls": 18,
  "nominal_calls": 21,
  "worst_case_calls": 63,
  "max_gpu_hours": 0.0
}
```

## 7. 발견한 문제와 수정

### 저장소 밖 코드가 lint 범위에 포함됨

초기 Ruff 실행은 기존 `.claude/skills/`의 Python 파일까지 검사했다. ISM 코드와 무관한 사용자 도구를
변경하지 않도록 `.claude`를 Ruff 검사 범위에서 제외했다.

### uv 전역 cache 권한

샌드박스에서 `uv run`이 사용자 전역 cache 접근으로 실패했다. 의존성 설치 후 검증 명령은 프로젝트
`.venv/bin/` 실행 파일을 직접 사용하도록 했다. 이는 테스트 결과에는 영향을 주지 않는다.

### 압축 호출 수 과대 계산

초기 dry-run은 Full+Dict와 Symbol Only를 별도 압축 호출로 계산해 6회로 표시했다. 두 조건은 같은
ISM 압축에서 파생되므로 compression family 개념을 추가했고 3회로 수정했다. 이를 고정하는 회귀
테스트도 추가했다.

## 8. 알려진 제한

- 아직 synthetic 데이터 schema와 rule graph는 구현되지 않았다.
- 실제 tokenizer와 model adapter는 구현되지 않았다.
- `dry-run`은 호출 수와 상한을 계산하지만 실제 GPU 시간과 저장공간 추정은 Phase 3 이후 보강한다.
- 현재 import boundary 검사는 Phase 0 순수 모듈만 대상으로 하며 패키지 확장에 따라 강화해야 한다.

## 9. Phase 1 진입 조건

Phase 1 시작 조건은 충족됐다.

- Phase 0 Blocking TC 전부 통과
- 로컬 CPU에서 CLI와 dry-run 동작
- GPU 및 서버 비용 0
- 미해결 Blocking 오류 0

Phase 1에서는 rule graph, symbolic executor, template renderer, question generator, JSONL
round-trip을 구현한다.

## 10. 재현 절차

```bash
uv sync --dev
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright src tests
.venv/bin/pytest -m "not gpu and not network"
.venv/bin/python -m ism validate-config \
  --config configs/experiments/smoke.yaml
.venv/bin/python -m ism dry-run \
  --config configs/experiments/smoke.yaml
```

## 11. Git 상태

이 보고서는 Phase 0 구현 직후, 아직 해당 구현을 별도 커밋하기 전에 작성되었다. 완료 커밋이 생성되면
이 절에 commit hash를 추가한다.
