# Contract v1 — 공유 코어 경계

**상태: 다음 SOP 프로젝트를 위한 경계 설계 문서. 공유 라이브러리 배포, framework 재구성 또는 프로젝트 간 상태 공유를 구현한 문서가 아닙니다.**

이 문서의 `v1`은 첫 번째 증거·검토 인터페이스 기준을 뜻합니다. 현재 HTTP API에 버전 협상, 신규 endpoint 또는 자동 migration 기능을 추가한 것은 아닙니다. 실행 중인 01 프로젝트의 API는 [contract.md](contract.md)가 기준입니다.

## 목표

01 장애 근거 워크벤치와 다음 02 SOP 업무 흐름은 원문 참조, 개정, 권한, 인용 검증, 사람의 결정과 감사 기록이라는 문제를 공유할 수 있습니다. 반면 장애 로그의 오류 코드와 SOP 조항의 해석은 서로 다른 도메인입니다.

우선 공통 인터페이스와 실패 의미를 합의하고, 각 프로젝트의 실제 사례에서 두 번째 사용을 확인합니다. 지금 공통 패키지를 만들거나 기존 구현을 일반 framework로 바꾸지 않습니다. 02가 01의 SQLite DB·세션·권한 저장소를 import해서 쓰는 구조도 허용하지 않습니다.

## 경계 표

| 영역 | 공통 후보 | 01 IT 도메인에 남는 구현 | 02가 별도로 소유할 것 |
| --- | --- | --- | --- |
| 원문 참조 | 문서 ID, 논리 ID, 개정, 사이트, 원문 span, 관측/발효 시각의 명시적 schema | MES log/config/health의 의미 | SOP 조항·문서 발효·예외 적용의 의미 |
| 최신 개정 | 최신 선택 후 권한 검사, 과거 개정 fallback 금지 원칙 | 현재 corpus loader와 쿼리 | SOP ingestion·등록 검증과 독립 corpus |
| ACL | 인증된 principal을 기준으로 모든 읽기 표면 재검사하는 계약 | 현재 demo session과 A/B 역할 매핑 | SOP별 사이트·역할 정책과 독립 세션/인증 상태 |
| 검색 | 허용된 최신 문서만 반환하는 입력/출력 계약 | 오류 코드·서비스 어휘와 현재 n-gram 순위 | 조항·공정·작업 조건 검색 전략 |
| 관측 추출 | 결과 구조·출처·누락·오류를 전달하는 계약 | `workbench/rules.py`와 `llm.py`의 IT 정형 필드 | SOP 도메인 schema·추출기·근거 검증 |
| 인용 | 정확한 원문 부분 문자열과 해당 개정에 결합된 참조 | 현재 문서 조회 경로와 canonical IT facts | SOP별 인용/조항 span 기준 |
| 검증 게이트 | `passed`, `issues`, 실패 시 승인 차단 | IT entity/value/unit/polarity/time/coverage 검증 | SOP 적용성·조항 누락·예외 검증 |
| 사람 검토 | 분석 ID별 승인/반려, 멱등 결정과 감사 기록 계약 | 01 검토 DB와 현재 reviewer 정책 | 02 검토 DB·상태·검토자 정책 |
| 모델 실행 | bounded JSON 요청, 단일 실행 lease, 명확한 timeout/degraded 의미 | 현재 모델 대상·IT 추출 prompt/schema | SOP prompt/schema와 독립 예산 |
| n8n | 향후 읽기·대기·상태 조정 패턴 | 실행 연동 없음 | 별도 승인 후 adapter 개발; 현재 설계만 존재 |

## 최소 인터페이스

현재 01 API 객체를 기반으로 다음 개념의 경계를 유지합니다. 재사용할 구현이 실제로 필요해지면 작은 순수 함수나 versioned adapter를 먼저 고려합니다.

```text
Principal:
  id, site, role

EvidenceDocument:
  id, logical_id, revision, site, roles,
  domain-specific kind, original content, timestamp

SourceRef:
  document_id, revision, exact original quote
  optional explicit original span, observed_at/effective_at

Analysis:
  id, incident_or_work_item_id, site, mode, status,
  summary, facts, hypotheses, counterevidence, unknowns,
  citations, gate, metrics, review

Gate:
  passed: boolean
  issues: explicit machine-readable/reviewable reasons

Review:
  analysis_id, approved|rejected, comment, reviewer identity, timestamp
```

이 schema 표는 새로운 02 API를 구현했다는 뜻이 아닙니다. 01에는 `incident_id`가 이미 사용되고 있습니다. 02가 어떤 work item ID와 객체를 쓸지는 도메인 설계에서 결정합니다. 존재하지 않는 field를 현재 endpoint에 요구하지 않습니다.

## 관측 모듈은 IT 도메인에 남긴다

현재 실제 모델은 MES code/status/duration, inventory port/process/health 필드를 추출합니다. CPU 관측 파서는 IT 원문의 엔티티·값·단위·극성·관측 시각·출처·개정·원문 인용을 구성하고 중요 필드 누락을 검증합니다. 원인 범주는 잠정 IT 규칙 결과입니다.

이 모듈을 SOP 진단기 또는 범용 extraction package로 이름만 바꿔 재사용하지 않습니다. SOP는 조항 적용 조건, 문서 발효 시각, 예외, 승인 범위와 누락의 의미를 별도로 정의해야 합니다. 공통으로 사용할 것은 검증 결과를 전달하는 구조와 원문에 결합된 참조 원칙입니다. 일반 의미적 함의 검증이나 독립 원인 진단 완료를 주장하지 않습니다.

## 프로젝트별 상태 격리

01과 02는 다음 항목을 공유하지 않습니다.

- runtime corpus, DB, 분석 ID 공간, 리뷰·감사 상태
- demo session, bearer token, principal allowlist, ACL cache
- 모델 입력 문서 목록, 결과 cache, 평가 정답과 split
- 브라우저 sessionStorage와 사용자 선택 상태
- 쓰기 endpoint 권한 또는 이전 프로젝트의 승인 결정

공유 interface는 권한을 전달하는 bypass가 아닙니다. 출처 ID, 사이트 값 또는 correlation ID만으로 접근을 허용하지 않고, 해당 프로젝트가 인증한 principal을 기준으로 원문·개정·역할을 다시 확인해야 합니다. 한 프로젝트의 승인은 다른 프로젝트의 작업이나 새 원문 개정을 승인하지 않습니다.

## 공유 추론 lease의 범위

같은 GPU를 사용하는 협력 요청은 **추론 자원 점유 lease만 공유**할 수 있습니다. 기본 경로는 실행 사용자의 `~/.cache/ax-lab/runtime/inference.lock`입니다. 저장소 checkout 깊이나 01·02 프로젝트 디렉터리에 의존하지 않습니다. 두 프로젝트를 같은 사용자로 실행하면 같은 기본 lease를 사용합니다.

명시적으로 경로를 정할 때는 두 프로세스에 동일한 절대 경로의 `AX_LAB_INFERENCE_LOCK`을 설정해야 합니다. 상대 경로, 펼쳐지지 않은 `~/...`, 빈 값은 거절합니다. 설정은 client를 불러올 때 선택되므로 이미 실행 중인 프로세스에는 owned app 재시작 후 적용됩니다.

```text
user home/
  .cache/
    ax-lab/
      runtime/
        inference.lock
```

현재 01 client는 누락된 부모 디렉터리를 최대 세 단계까지 각각 mode 0700으로 생성합니다. 최종 부모는 현재 사용자가 소유한 private 디렉터리여야 하며 기존 디렉터리 권한을 자동 변경하지 않습니다. lock 파일은 사용자 소유 regular file, mode 0600입니다. 부모와 파일의 마지막 symlink를 거절하고 열린 directory descriptor를 기준으로 파일을 엽니다. 경로·권한 실패 시 네트워크 요청 전에 실패합니다. 기존 nonblocking `fcntl.flock`, 프로세스 내부 single-flight lock과 timeout disabled latch는 유지합니다.

이는 데이터나 인증 상태의 공유가 아닙니다. lease에는 원문, 사용자 정보, session 값, 승인 상태 또는 정답을 기록하지 않습니다. 02가 실제 모델 경로를 추가할 때는 01의 `workbench/llm.py::_configured_inference_lock`, `_open_inference_lease`와 `request_json`의 acquisition/finally-close 패턴을 별도 client에 복사해 동일한 자원 정책을 적용할 수 있습니다. 01의 도메인 추출기·DB·세션을 import하지 않고 SOP prompt/schema와 독립 예산을 유지합니다.

이 lease는 규약을 따르는 요청 사이의 협력 경계입니다. 임의의 다른 GPU 작업을 중단하거나 모든 시스템 추론을 통제하지 않습니다. timeout 후 disabled latch는 각 프로젝트 프로세스 상태입니다. 해당 owned 요청이 끝났는지 확인하고 owned app만 복구하며, 다른 프로젝트나 Ollama 작업을 임의로 종료하지 않습니다.

기존 checkout-relative `ax-lab/inference.lock`에서 새 경로로 바꿀 때는 **기존 lease와 모델 요청이 모두 idle인 것을 먼저 확인**해야 합니다. 이후 두 프로젝트의 owned app을 같은 새 경로 설정으로 재시작합니다. 서로 다른 경로를 사용하는 client를 동시에 실행하거나 lock 파일 삭제로 active lease를 우회하면 안 됩니다. 시스템 전역 설정, 인증 또는 모델 설정은 변경하지 않습니다. 파일은 남아 있어도 descriptor가 닫히면 OS lease는 해제됩니다.

01의 clone 깊이 독립 경로, private 생성, 절대 경로 설정, 상대 경로·권한·symlink 실패, cross-process 경쟁은 임시 lease와 mocked network를 사용해 검사합니다. 테스트는 새 runtime lease를 취득하거나 live migration을 실행하지 않습니다. 02를 복사·실행하여 공유 lease를 검증한 결과라는 뜻은 아닙니다. 실제 동시 사용 전에 두 client의 절대 경로 일치와 cross-process 거절을 별도로 확인해야 합니다.

## n8n과의 관계

[n8n adapter 문서](n8n-adapter-design.md)는 설계만 제공합니다. 현재 설치된 workflow, 커넥터 인증, webhook 또는 외부 시스템 전송은 없습니다.

미래 adapter는 수집 요청을 조정하고 backend의 분석/결정을 읽거나 사람이 검토할 때까지 기다릴 수 있습니다. ACL, 최신 개정, 인용/관측 검증과 승인 권한은 각 프로젝트 backend가 소유합니다. adapter는 실패 게이트를 통과 상태로 바꾸거나 reviewer 권한을 가진 observer처럼 행동하면 안 됩니다. 이벤트 재시도와 불확실한 mutation 결과는 기존 ID를 대조해 처리해야 합니다.

## 다음 구현 전에 확인할 기준

1. 02의 합성 사례와 schema를 독립적으로 정의합니다. 01 정답이나 상태를 재사용하지 않습니다.
2. 각 프로젝트에서 cross-site/role 접근 차단, 최신 개정 권한, 정확한 인용, 누락·실패 게이트, 멱등 검토를 독립 테스트합니다.
3. 실제 두 번째 사용이 확인된 작은 interface만 추출합니다. 추출 시 contract 버전과 compatibility 검사를 남깁니다.
4. 새로운 corpus·도메인·모델 입력 예산에 대한 실패 시나리오를 확인합니다.
5. 둘 다 실제 추론을 사용하는 경우 단일 lease 경쟁·timeout 복구를 확인합니다. 이 문서로 해당 통합 테스트가 완료됐다고 주장하지 않습니다.

현재 승인된 구현 범위는 01의 작업 흐름입니다. 이 문서는 다음 프로젝트에서 경계를 유지하기 위한 설계 기준이며, 대규모 framework refactor를 실행하지 않습니다.
