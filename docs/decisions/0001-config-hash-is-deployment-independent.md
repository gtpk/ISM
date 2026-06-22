# ADR 0001 — config_hash는 배포 경로와 독립적이어야 한다

- 상태: 채택 (Accepted)
- 날짜: 2026-06-23
- 관련 TC: `COL-ENV-004` (local/Colab config parity, Blocking), `COL-IO-001` (artifact export checksum)
- 관련 코드: [src/ism/config.py](../../src/ism/config.py), [tests/test_config.py](../../tests/test_config.py)

## 배경

`AppConfig.config_hash()`는 `stable_json()`의 SHA-256이고, `stable_json()`은
`model_dump()` 결과를 직렬화한다. 그런데 `load_config()`가 반환하는 config는
`resolved()`를 거치면서 `dataset.path`와 `output.artifact_dir`를 **프로젝트 루트
기준의 절대경로**로 바꾼다.

그 결과 같은 실험 config라도 실행 위치에 따라 해시가 달라졌다.

| 환경 | 직렬화된 dataset.path | config_hash |
|---|---|---|
| 로컬 | `/Users/puka/repository/SESC/data/processed/synthetic-v1` | `2306e863…` |
| Colab | `/content/SESC/data/processed/synthetic-v1` | `0bb41e10…` |

## 문제

이 동작은 프로젝트의 핵심 워크플로우(로컬=source of truth, Colab=실행 환경)와
직접 충돌한다.

1. **COL-ENV-004 불가능.** 로컬과 Colab의 resolved config hash가 같아야 하는데
   절대경로가 해시에 섞여 구조적으로 절대 일치할 수 없었다.
2. **manifest 교차검증 상시 실패.** [evaluation/manifest.py](../../src/ism/evaluation/manifest.py)는
   `config.config_hash() != self.config_hash`로 산출물을 검증한다. Colab에서 만든
   manifest를 로컬에서 검증하면 경로 차이만으로 **항상** 실패하여, 원격 산출물을
   로컬에서 확인하는 경로가 깨져 있었다.

즉 config_hash가 "실험 정체성"이 아니라 "실험 정체성 + 설치 위치"를 식별하고
있었다. 이는 잠재 버그다.

## 결정

`config_hash`/`stable_json`이 **authored(상대) 경로 형태**를 식별하도록 변경한다.
런타임에서 쓰는 절대경로는 모델 필드에 그대로 두되, **직렬화 identity에서만**
경로를 프로젝트 루트 기준 POSIX 상대경로로 환원한다.

- `resolved()`가 사용한 project root를 `_project_root`(`PrivateAttr`,
  직렬화 제외)에 보관한다.
- `stable_json()`은 `dataset.path`/`output.artifact_dir`를 `_identity_path()`로
  상대화한다. 루트 밖 경로는 절대 POSIX 형태로 fallback한다.
- POSIX(`as_posix`)로 통일해 macOS(로컬)와 Linux(Colab)의 구분자 차이도 제거한다.

부수 효과로 `ism validate-config` 출력도 상대경로를 보여준다. 이는 의도된 것으로,
로컬과 Colab이 **바이트 단위로 동일한** 정규 config를 보게 되어 parity 점검이
명확해진다.

## 영향

- `config_hash` 값이 바뀐다(`2306e863…` → `92701d9e…`). 이전 해시로 기록된 산출물
  manifest는 재생성하거나 마이그레이션해야 한다. 현재 산출물이 없으므로 영향 없음.
- 추가 회귀 테스트: `test_col_env_004_config_hash_is_project_root_independent` —
  서로 다른 project root로 같은 config를 로드해도 hash가 같음을 보장한다.
- 결정성 테스트(`test_p0_det_001`)와 경로 해석 테스트(`test_p0_io_001`)는 그대로
  통과한다.

## 대안 (기각)

- **S0 smoke에서만 경로를 빼고 비교.** 빠르지만 manifest 교차검증 버그는 그대로
  남아 source-of-truth 워크플로우가 계속 깨진다.
- **현상 유지(known-issue).** COL-ENV-004가 Blocking이라 수용 불가.
