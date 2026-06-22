# Phase 2 완료 보고서: ISM 표현과 intervention

## 1. 목표

Phase 2의 목표는 모델 출력에서 ISM을 엄격하게 복원하고, 논문의 핵심 개입을 원본 변경 없이
재현 가능하게 생성하는 것이다.

구현 범위:

- immutable ISM symbol, dictionary, relation schema
- `[DICTIONARY]`, `[RELATIONS]` parser와 canonical serializer
- 주입 가능한 tokenizer 기반 token budget 검증
- malformed output 오류 코드와 원문 보존
- question/answer leakage 탐지
- dictionary removal, corruption, random-symbol, label swap
- intervention seed와 label mapping 메타데이터
- 1,000개 무작위 표현 불변식 스트레스

모델 호출, retry orchestration, Transformers tokenizer adapter는 Phase 3 범위다.

## 2. 구현 파일

| 경로 | 역할 |
|---|---|
| `src/ism/representation/models.py` | ISM schema와 참조 무결성 |
| `src/ism/representation/parser.py` | parser, serializer, 오류 코드, budget |
| `src/ism/representation/tokenizer.py` | tokenizer-independent `TokenCounter` Protocol |
| `src/ism/representation/leakage.py` | question/answer 직접 포함 탐지 |
| `src/ism/representation/interventions.py` | 네 가지 pure intervention |
| `tests/test_ism_parser.py` | parser, budget, malformed, golden corpus TC |
| `tests/test_interventions.py` | 개입 불변식, 결정성, 1,000-object stress |
| `tests/test_leakage.py` | leakage fixture TC |
| `tests/test_architecture.py` | data/representation 외부 모델 import 금지 |

## 3. 표현 계약

- symbol label은 `Z1`, `Q7`, `R0000042`처럼 숫자를 포함한 대문자 식별자다.
- symbol, dictionary label은 각각 유일해야 한다.
- dictionary와 relations는 선언되지 않은 symbol을 참조할 수 없다.
- definition과 relation 항목은 blank일 수 없다.
- Full Symbol + Dict는 비어 있는 dictionary와 relations를 거부한다.
- Symbol Only는 parser option으로 빈 dictionary를 허용하되 relations에서 symbol 집합을 복원한다.
- canonical serializer는 section 순서와 마지막 newline을 고정한다.

## 4. Parser와 budget 계약

- 허용 section은 `[DICTIONARY]`, `[RELATIONS]`뿐이다.
- 중복 section, section 전 content, malformed dictionary line을 별도 오류 코드로 구분한다.
- budget은 문자 수나 공백 수를 직접 가정하지 않고 주입된 `TokenCounter`로 측정한다.
- 예산 초과 출력은 절단하지 않고 `budget_exceeded`로 거부한다.
- parser 오류는 원시 모델 출력을 보존해 Phase 3 retry/failure record에서 사용할 수 있다.
- 보호된 question 또는 answer가 포함되면 `leakage_detected`로 거부한다.

## 5. Intervention 계약

| Intervention | 보존 조건 |
|---|---|
| remove dictionary | symbols와 relations byte-level 내용 유지 |
| corrupt dictionary | definition multiset 유지, 모든 위치가 원본과 다름 |
| random symbol | symbol 수와 tokenizer 길이 허용 오차 유지, 원본 relation substring 제거 |
| label swap | 전 영역에 동일 bijection 적용, definition 의미와 relation 구조 유지 |

모든 함수는 새 `ISMRepresentation`과 mapping/seed를 반환하며 입력 객체를 수정하지 않는다.

## 6. 통과한 TC

| TC | 결과 |
|---|---|
| P2-CON-001 parser/serializer round-trip | 통과 |
| P2-CON-002 duplicate label rejection | 통과 |
| P2-CON-003 undefined reference rejection | 통과 |
| P2-CON-004 condition별 empty section 계약 | 통과 |
| P2-FUN-001 63/64/65 token budget 경계 | 통과 |
| P2-FUN-002 Unicode tokenizer count | 통과 |
| P2-FUN-003 dictionary removal 불변식 | 통과 |
| P2-FUN-004 corruption derangement | 통과 |
| P2-FUN-005 1-symbol corruption 명시적 실패 | 통과 |
| P2-FUN-006 swap bijection | 통과 |
| P2-FUN-007 swap inverse | 통과 |
| P2-FUN-008 random control shape/length | 통과 |
| P2-DET-001 intervention seed 결정성 | 통과 |
| P2-ERR-001 malformed raw/error 보존 | 통과 |
| P2-ERR-002 parser leakage rejection | 통과 |
| P2-REG-001 정상·비정상 parser corpus | 통과 |
| 1,000-object intervention stress | 통과 |
| data/representation dependency boundary | 통과 |

Phase 0-1 회귀를 포함한 자동 테스트는 총 68개다.

## 7. 검증 결과

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright src tests
.venv/bin/pytest -m "not gpu and not network"
```

```text
Ruff: all checks passed
Formatting: 28 files already formatted
Pyright: 0 errors, 0 warnings
Pytest: 68 passed in 0.81s
Colab/GPU/API calls: 0
```

1,000개 stress에서는 각 객체에 대해 다음을 확인했다.

- corruption의 모든 definition 위치가 변경됨
- random control의 symbol 수가 동일함
- swap 후 inverse가 원본과 동일함
- 모든 intervention 후 원본 JSON이 byte-identical함

## 8. 발견한 문제와 수정

### 결론 상수를 symbol로 오인

초기 label 정규식은 모든 대문자 단어를 허용해 `HIGH`를 미정의 symbol로 판정했다. 논문 형식의
심볼은 번호를 포함하므로 label을 숫자 포함 대문자 식별자로 제한했다. 이 변경으로 `Z1`, `Q7`은
추적하면서 `HIGH`, `LOW` 같은 값은 relation 상수로 유지한다.

### parser와 leakage validator 분리만 되어 있었음

초기 구현은 leakage 탐지 함수를 제공했지만 parser가 호출하지 않았다. parser 인자로 보호할
question/answer를 받아 구조 검증 전에 직접 거부하도록 연결했다.

### random control 길이의 tokenizer 가정

초기 padding은 noise 한 단어가 한 token을 늘린다고 가정했다. 현재는 매 padding 후 실제
`TokenCounter` 값을 다시 측정하며 증가하지 않거나 목표를 넘으면 명시적으로 실패한다.

## 9. 알려진 제한

- 로컬 기본 counter는 whitespace 기반이며 실제 모델 tokenizer adapter는 Phase 3에서 추가한다.
- leakage 검사는 정규화된 직접 substring 탐지이며 의미적 paraphrase leakage는 탐지하지 않는다.
- parser는 현재 line-oriented 형식만 지원하며 JSON/YAML 모델 출력은 받지 않는다.
- random control은 token 수를 맞추지만 모델별 token identity 분포까지 맞추지는 않는다.
- label grammar 변경은 기존 artifact와 호환성에 영향을 주므로 버전 관리가 필요하다.

## 10. Phase 3 진입 조건

- Phase 2 Blocking TC 전부 통과
- 1,000개 무작위 객체 pure transformation 통과
- parser 오류에 raw output과 기계 판정 가능한 code가 남음
- tokenizer가 Protocol로 분리됨
- data/representation에서 Transformers, bitsandbytes, Colab import 0
- 외부 API, GPU, Colab 비용 0
- 미해결 Blocking 오류 0

Phase 3에서는 model adapter contract, mock backend, compression/reasoning runner, atomic artifact,
retry, resume, cache key, failure classification을 구현한다.

## 11. Git 상태

이 보고서는 Phase 2 구현 직후, 해당 구현을 독립 커밋하기 전에 작성되었다.
