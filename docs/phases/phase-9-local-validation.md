# Phase 9 진행 보고서: 로컬 검증 완료, Colab S0 차단

## 1. 상태

2026-06-23 기준 Phase 9의 로컬 통계·보고·비용 게이트는 완료됐다. Colab MCP 도구는 Codex에
노출되지만 브라우저 Colab session handshake가 실패해 S0 이후는 실행하지 못했다.

이 문서는 논문 실험 완료 보고서가 아니다. 실제 model 결과 없이 mock 정확도를 논문 결과로
해석하지 않는다.

## 2. 로컬 구현 범위

- frozen config hash와 provenance 검증
- prediction uniqueness와 paired sample equality audit
- Accuracy, Accuracy Retention, Compression Ratio, Efficiency Score, Swap Robustness
- deterministic paired bootstrap confidence interval
- exact McNemar test
- Holm correction
- source run/metric key가 포함된 JSON, CSV, Markdown report
- raw artifact를 수정하지 않는 rerender
- pilot 처리량 기반 GPU 시간·저장공간 추정과 quota gate
- artifact 기반 `report-run` CLI
- `estimate-server` CLI

## 3. 통과한 Phase 9 TC

| TC | 결과 |
|---|---|
| P9-CFG-001 frozen config 변경 탐지 | 통과 |
| P9-CFG-002 provenance 완전성 | 통과 |
| P9-CON-001 prediction uniqueness | 통과 |
| P9-CON-002 paired sample equality | 통과 |
| P9-FUN-001 metric 수작업 fixture | 통과 |
| P9-FUN-002 zero denominator undefined | 통과 |
| P9-FUN-003 bootstrap 결정성 | 통과 |
| P9-FUN-004 exact McNemar fixture | 통과 |
| P9-FUN-005 Holm correction fixture | 통과 |
| P9-IO-001 report traceability | 통과 |
| P9-IO-002 rerender purity | 통과 |
| P9-REG-001 JSON/CSV/Markdown golden | 통과 |
| COST-CFG-001/002 호출 수와 retry 상한 | 통과 |
| COST-CFG-003 GPU 시간 추정 | 통과 |
| COST-CFG-004 저장공간 추정 | 통과 |
| COST-CFG-005 quota 누락 거부 | 통과 |
| COST-CFG-006 quota 초과 거부 | 통과 |

전체 로컬 자동 테스트는 143개다.

## 4. 로컬 end-to-end

실행:

```bash
.venv/bin/python -m ism run-mock \
  --config configs/experiments/smoke.yaml \
  --output /tmp/ism-phase9-local/run \
  --batch-size 4
.venv/bin/python -m ism audit-conditions \
  --config configs/experiments/smoke.yaml \
  --output /tmp/ism-phase9-local/condition-audit.json
.venv/bin/python -m ism report-run \
  --config configs/experiments/smoke.yaml \
  --predictions /tmp/ism-phase9-local/run/predictions.jsonl \
  --condition-audit /tmp/ism-phase9-local/condition-audit.json \
  --output /tmp/ism-phase9-local/report
```

결과:

```text
Documents: 3
Questions: 6
Conditions: 3
Predictions: 18
Report conditions: 3
Report files: metrics.json, metrics.csv, metrics.md
```

mock adapter는 gold expected output을 반환하므로 accuracy 1.0은 pipeline TC일 뿐 논문 성능이 아니다.

## 5. 서버 비용 예비 추정

입력:

```text
Worst-case calls: 63
Pilot assumption: 0.2 calls/second
Artifact assumption: 100,000 bytes/call
Approved GPU quota: 1 hour
```

출력:

```text
Estimated GPU time: 0.0875 hours
Estimated storage: 6,300,000 bytes
Quota gate: pass
```

이 수치는 실제 7B model S1 pilot 측정값이 아니라 서버 진입 로직 fixture다. S1 완료 후 실제
throughput, latency, memory, bytes/call로 다시 계산해야 한다.

## 6. Colab MCP 결과

공식 `googlecolab/colab-mcp` server는 local MCP client와 browser Colab session을 연결한다.

수행 결과:

| TC | 결과 |
|---|---|
| MCP server config 등록 | 통과 |
| `open_colab_browser_connection` 도구 노출 | 통과 |
| COL-ENV-001 browser session handshake | 실패 |
| 첫 시도 | 약 62초 후 `false` |
| 두 번째 시도 | 300초 timeout |
| Chrome session discovery | 사용 가능한 extension session 없음 |

따라서 아래 TC는 실행 전 상태다.

- COL-ENV-002 cell CRUD
- COL-ENV-003 stdout fixture
- COL-ENV-004 config hash parity
- COL-ENV-005 package lock manifest
- COL-RES-001/002 reconnect와 interrupted cell
- COL-IO-001 artifact checksum export
- COL-ARC-001 thin notebook audit
- S1 7B 4-bit 최소 GPU smoke
- S2 제한 pilot
- S3 main run

## 7. 재개 절차

1. Chrome에서 로그인된 Google Colab notebook을 연다.
2. Codex가 해당 Chrome session에 연결 가능한 상태인지 확인한다.
3. `open_colab_browser_connection`을 다시 호출한다.
4. 연결되면 임시 셀 CRUD와 `print("ISM_COLAB_OK")`를 실행한다.
5. 로컬 `smoke.yaml` config hash `2306e8631fd792f0ca90cab5bb3b7271578ab9299d97956587894a5f7adc5b43`
   와 Colab 값을 비교한다.
6. package version manifest를 저장한다.
7. S1 최소 GPU smoke 이후 실제 비용 추정을 다시 실행한다.

## 8. 미완료 조건

Phase 9와 전체 실험은 완료로 표시하지 않는다. Colab S0 연결과 실제 model adapter/pilot이
통과하기 전에는 논문 결과 표를 채우거나 성능 주장을 생성하지 않는다.

## 9. Git 상태

이 보고서는 Phase 9 로컬 구현 직후, 해당 구현을 독립 커밋하기 전에 작성되었다.
