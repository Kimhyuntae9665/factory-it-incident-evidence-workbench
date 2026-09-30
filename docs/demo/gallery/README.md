# 실제 UI 화면 갤러리

합성 데이터 기반 기업 업무 재현 테스트의 실제 브라우저 화면입니다. 공장 운영 화면이나 실제 ROI·MTTR 검증 자료가 아닙니다. 화면은 기존 코드의 UI와 API에서 생성했으며, 합성 프로필만 사용했습니다.

| 화면 | 내용 |
| --- | --- |
| [01 정상 조회](01-normal-baseline.png) | 규칙 기준선과 정상 주문 조회 근거 |
| [02 접속 주소 오류](02-endpoint-mismatch.png) | 설정 포트·기준 포트의 원문 대조 |
| [03 의존 서비스 비활성](03-dependency-unavailable.png) | 연결 오류와 상태 조회 근거 |
| [04 응답 지연](04-delay-counterevidence.png) | 정상 상태 조회를 포함한 반증 표시 |
| [05 원문 인용 검증](05-original-quote-validation.png) | 최신 개정의 정확한 부분 문자열과 강조 표시 |
| [06 검토·감사 이력](06-review-and-audit.png) | 검토자 승인 기록과 감사 이력; 자동 조치 없음 |
| [07 운영 담당 접근 범위](07-operator-evidence-scope.png) | 기술 근거 제외와 승인 권한 제한 |
| [08 중립 검토 표시](08-operator-neutral-review.png) | 결정 비공개 시 승인·반려를 추정하지 않는 표시 |
| [09 모바일 작업 화면](09-mobile-workspace.png) | 390×1100 viewport, 가로 넘침 없음 |
| [10 실제 모델 추출](10-real-model-extraction.png) | 로컬 모델의 정형 관측 추출과 원문 인용; 원인 가설은 잠정 규칙 결과 |

01–09는 규칙 기준선으로 캡처했으며 모델 추론을 요청하지 않았습니다. 캡처 상태·viewport·모드·합성 표시 정보는 [baseline-capture.json](baseline-capture.json)에 있습니다.

10은 공유 추론 lease와 실행 준비를 확인한 뒤 명시적인 실제 모델 요청 1회로 캡처했습니다. 통과한 인용·정형 관측 추출 상태는 [model-capture.json](model-capture.json)에 있습니다. 정형 관측 추출을 최종 원인 진단이나 독립 일반화 평가로 해석하지 않습니다.

재현 도구는 저장소의 `scripts/gallery_capture.py`와 `scripts/operator_review_browser.py`입니다. 설치된 sandboxed Chrome의 loopback CDP 세션과 실행 중인 로컬 앱을 사용합니다. 별도 브라우저 패키지를 다운로드하거나 backend 정책을 수정하지 않습니다.

운영 담당 중립 표시 회귀는 실제 승인 사례와 실제 반려 사례를 각각 생성하고, 운영 담당 프로필로 다시 열었을 때 상태가 “검토 완료”, 기록이 “검토 기록 있음”으로 표시되는지 확인했습니다. 비공개 결정·의견을 화면에서 추론하지 않습니다.
