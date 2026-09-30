# 현재 P01 브라우저 화면

모두 허구의 MES 장애·데모 역할을 담은 **실제 Chrome 화면 캡처**입니다. 이번 화면 재정렬은 P09 v2 개발 화면의 색·두 열·카드·버튼 패턴을 따르며, 모델과 백엔드 판단을 변경하지 않았습니다. 캡처 때 사용한 분석은 전부 CPU 규칙 기준선으로 **모델 요청 0회**입니다. 기존 모델 캡처와 영상은 이전 화면의 역사적 기록입니다.

| 순서 | 화면 | 상태 |
| --- | --- | --- |
| 01 | [정상 조회](01-normal-baseline.png) | 사건 선택과 근거·분석 두 열 |
| 02 | [주소 오류](02-endpoint-mismatch.png) | 설정 포트와 기준 포트 |
| 03 | [의존 서비스 단절](03-dependency-unavailable.png) | 연결 오류와 상태 조회 |
| 04 | [응답 지연](04-delay-counterevidence.png) | 지연 관측과 반증 |
| 05 | [인용 원문](05-original-quote-validation.png) | 현재 접근 가능 개정의 정확한 부분 문자열 |
| 06 | [검토·감사](06-review-and-audit.png) | 사람 검토 기록과 이력 |
| 07 | [역할별 근거](07-operator-evidence-scope.png) | 운영 담당의 제한된 근거 |
| 08 | [중립 표시](08-operator-neutral-review.png) | 비공개 결정 내용 미표시 |
| 09 | [모바일](09-mobile-workspace.png) | 390px 원문 작업 탭, 가로 넘침 없음 |

캡처 도구는 `scripts/run_refit_gallery.py`와 `scripts/refit_gallery_capture.py`입니다. 실제 앱은 이 작업만의 127.0.0.1:19101, Chrome CDP는 127.0.0.1:19102에서 실행했습니다. 별도 합성 SQLite 데이터베이스를 썼고, 종료 때 두 프로세스만 정리했습니다. 공유 Ollama/GPU나 기존 P01 서비스에는 요청하지 않았습니다. 개별 캡처의 사건·역할·모드·viewport는 [baseline-capture.json](baseline-capture.json), 바이트 해시는 [SHA256SUMS](SHA256SUMS)에 있습니다.

캡처 원본에는 서버의 실제 UI 출력만 담겼습니다. 비밀번호·토큰·개인키·사설 호스트 주소를 캡처하지 않도록 표시 텍스트를 검사했으며, 성공을 보이기 위해 이미지를 합성하거나 수정하지 않았습니다. 데스크톱은 1440×1080, 모바일은 390×1100 viewport입니다. [키보드 검사 기록](keyboard-checks.json)은 실제 브라우저의 사건 선택, 포커스 복귀 및 모바일 작업 탭 19개 확인 항목을 담습니다. 이 검사는 접근성 인증이 아닙니다.

현 화면 소스 SHA-256: `static/index.html` `58ee064c288bfcf0bf5492caabda80ff99e983e68755a19b20209713e57981f3`, `static/styles.css` `2c65081594e2ef6f86f750688467edfce60cdd1dfd3a071f51e78c0f4a08bcc8`. 이 출처 정보는 같은 파일의 현재 화면인지 확인하기 위한 것이며, 모델 성능이나 기업 성과 점수가 아닙니다.
