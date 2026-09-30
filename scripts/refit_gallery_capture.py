"""Capture an actual synthetic UI gallery using the installed sandboxed Chrome.

Baseline-only screenshots on an isolated loopback server and Chrome.
This refit script has no model request path. Never downloads browsers,
changes shared services, or captures authentication values.
"""
import base64
import json
import os
from pathlib import Path

from scripts import operator_review_browser as workflow
from scripts.operator_review_browser import connect, login, open_analysis, select, wait

workflow.CDP_ROOT = "http://127.0.0.1:19102"

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "docs/demo/refit-gallery"
APP = "http://127.0.0.1:19101"


def desktop(client):
    client.call("Emulation.setDeviceMetricsOverride", {"width":1440, "height":1080, "deviceScaleFactor":1, "mobile":False})


def analyze(client):
    wait(client, "!document.querySelector('#analyze-button').disabled")
    previous = client.evaluate("document.querySelector('#analysis-meta').textContent")
    client.evaluate("document.querySelector('input[name=mode][value=baseline]').checked=true;document.querySelector('input[name=mode][value=baseline]').dispatchEvent(new Event('change'));document.querySelector('#analysis-question').value='원문에 근거해 관측 사실, 잠정 가설, 반증과 미확인 사항을 정리해 주세요.';document.querySelector('#analysis-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    wait(client, "!document.querySelector('#analysis-result').hidden && !document.querySelector('#analyze-button').disabled && document.querySelector('#analysis-meta').textContent!==" + json.dumps(previous), seconds=20)
    return client.evaluate("document.querySelector('#analysis-meta').textContent.split(' / ')[0]")


def quote(client, index=0):
    client.evaluate("document.querySelectorAll('.citation-card')[" + str(index) + "].click()")
    wait(client, "document.querySelectorAll('#document-content mark').length>0 && document.querySelector('#citation-check').textContent.includes('정확히 일치')")


def capture(client, filename, caption, entries):
    # Page screenshots include rendered content only, without browser UI.
    private_markers = [str(Path.home()), os.environ.get("USER", "")]
    expression = "({incident:document.querySelector('#incident-id').textContent,profile:document.querySelector('#principal').textContent,mode:document.querySelector('#analysis-mode-badge').textContent,gate:document.querySelector('#gate-title').textContent,viewport:{width:window.innerWidth,height:window.innerHeight},overflow:document.documentElement.scrollWidth>window.innerWidth,sensitive:/\\b10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b|\\b192\\.168\\.\\d{1,3}\\.\\d{1,3}\\b|\\b172\\.(?:1[6-9]|2\\d|3[01])\\.\\d{1,3}\\.\\d{1,3}\\b|[A-Z]:\\\\Users|BEGIN [A-Z ]*PRIVATE KEY|Bearer\\s+[A-Za-z0-9]/i.test(document.body.textContent) || " + json.dumps([item for item in private_markers if item]) + ".some(marker=>document.body.textContent.includes(marker))})"
    state = client.evaluate(expression)
    if state.pop("sensitive"):
        raise RuntimeError("Refusing to capture page with private host/path/authentication text")
    image = client.call("Page.captureScreenshot", {"format":"png", "captureBeyondViewport":False})
    (GALLERY / filename).write_bytes(base64.b64decode(image["data"]))
    entries.append({"file":filename, "caption":caption, "actual_ui":True, "synthetic":True, **state})
    print(json.dumps({"captured":filename, "incident":state["incident"], "mode":state["mode"]}, ensure_ascii=False), flush=True)


def main():
    GALLERY.mkdir(parents=True, exist_ok=True)
    client = connect()
    entries = []
    try:
        desktop(client)
        client.call("Page.navigate", {"url":APP})
        wait(client, "document.querySelectorAll('#profile-select option').length===6 && !document.querySelector('#session-button').disabled")
        login(client, "A-reviewer")
        cases = [
            ("INC-A-001","01-normal-baseline.png","정상 주문 조회: 규칙 기준선과 접근 가능한 원문을 함께 확인합니다."),
            ("INC-A-002","02-endpoint-mismatch.png","접속 주소 오류: 설정 포트와 기준 포트를 원문에서 대조합니다."),
            ("INC-A-003","03-dependency-unavailable.png","의존 서비스 비활성: 연결 오류와 상태 조회 근거를 구분합니다."),
            ("INC-A-004","04-delay-counterevidence.png","지연: 정상 상태 조회가 전체 서비스 단절 가설의 반증으로 표시됩니다."),
        ]
        for incident_id, filename, caption in cases:
            select(client, incident_id)
            analyze(client)
            quote(client, 1 if incident_id == "INC-A-002" else 0)
            client.evaluate("window.scrollTo(0,0)")
            capture(client, filename, caption, entries)

        select(client, "INC-A-002")
        analyze(client)
        quote(client, 1)
        client.evaluate("document.querySelector('#document-view').scrollIntoView({block:'start'});window.scrollBy(0,-30)")
        capture(client, "05-original-quote-validation.png", "원문 인용 대조: 정확한 부분 문자열 검증과 현재 개정의 강조 표시입니다.", entries)

        client.evaluate("document.querySelector('#review-comment').value='합성 갤러리 검토: 설정 포트·기준 포트·정상 상태 조회를 원문에서 대조했습니다. 최종 복구 결과는 미확인입니다.';document.querySelector('#approve-button').click()")
        wait(client, "document.querySelector('#review-existing').textContent.includes('승인 기록됨') && !document.querySelector('#analyze-button').disabled")
        client.evaluate("document.querySelector('.review-block').scrollIntoView({block:'start'});window.scrollBy(0,-30)")
        capture(client, "06-review-and-audit.png", "검토자 승인과 감사 이력: 검토 기록은 자동 복구를 실행하지 않습니다.", entries)

        login(client, "A-operator")
        select(client, "INC-A-002")
        operator_analysis = analyze(client)
        client.evaluate("window.scrollTo(0,0)")
        restricted = client.evaluate("({count:document.querySelector('#evidence-count').textContent,approve:document.querySelector('#approve-button').disabled,text:document.querySelector('#evidence-list').textContent})")
        assert restricted["approve"] and "configuration" not in restricted["text"].lower(), restricted
        capture(client, "07-operator-evidence-scope.png", "운영 담당 접근 범위: 기술 로그·설정은 제외되고 승인 권한이 차단됩니다.", entries)

        login(client, "A-reviewer")
        select(client, "INC-A-002")
        open_analysis(client, operator_analysis)
        client.evaluate("document.querySelector('#review-comment').value='합성 갤러리: 운영 담당에게 허용된 접수 근거만 검토했습니다.';document.querySelector('#approve-button').click()")
        wait(client, "!document.querySelector('#review-existing').hidden && !document.querySelector('#analyze-button').disabled")
        login(client, "A-operator")
        select(client, "INC-A-002")
        open_analysis(client, operator_analysis)
        neutral = client.evaluate("document.querySelector('#review-existing').textContent")
        assert "검토 기록 있음" in neutral and "승인" not in neutral and "반려" not in neutral, neutral
        client.evaluate("document.querySelector('.review-block').scrollIntoView({block:'start'});window.scrollBy(0,-30)")
        capture(client, "08-operator-neutral-review.png", "결정 비공개: 운영 담당에게는 승인·반려를 추정하지 않는 중립 검토 표시만 제공합니다.", entries)

        login(client, "A-reviewer")
        select(client, "INC-A-004")
        analyze(client)
        quote(client)
        client.call("Emulation.setDeviceMetricsOverride", {"width":390,"height":1100,"deviceScaleFactor":1,"mobile":True})
        client.evaluate("document.querySelector('#workspace').scrollIntoView({block:'start'})")
        capture(client, "09-mobile-workspace.png", "모바일 화면: 사건·근거·분석이 세로로 배치되며 가로 넘침을 확인합니다.", entries)
        assert not entries[-1]["overflow"], "Mobile horizontal overflow"
        desktop(client)
        client.evaluate("window.scrollTo(0,0)")
        (GALLERY / "baseline-capture.json").write_text(json.dumps({"real_browser":True,"synthetic":True,"real_model_requests":0,"screenshots":entries},ensure_ascii=False,indent=2),encoding="utf-8")
        print("PASS: 9 actual UI screenshots; baseline-only; mobile overflow false.", flush=True)
    finally:
        client.socket.close()


if __name__ == "__main__":
    main()
