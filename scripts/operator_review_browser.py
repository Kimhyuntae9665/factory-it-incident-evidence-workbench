"""Actual UI regression: a redacted operator review must never imply rejection.

Run with the project app on loopback 19080 and an owned sandboxed Chrome CDP
listener on loopback 19085. No model requests; baseline mutations use only
synthetic demo profiles. Assertions exercise the actual page and server.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

from scripts.browser_smoke import CDP

ROOT = Path(__file__).resolve().parents[1]
APP = "http://127.0.0.1:19080"
CDP_ROOT = "http://127.0.0.1:19085"


def connect():
    with urllib.request.urlopen(CDP_ROOT + "/json", timeout=10) as response:
        targets = json.load(response)
    target = next(item for item in targets if item["type"] == "page")
    client = CDP(target["webSocketDebuggerUrl"])
    client.call("Page.enable")
    client.call("Runtime.enable")
    return client


def wait(client, condition, seconds=20):
    expression = "(async()=>{const end=Date.now()+" + str(int(seconds * 1000)) + ";while(Date.now()<end){if(" + condition + ")return true;await new Promise(r=>setTimeout(r,100));}throw new Error('UI condition timed out');})()"
    return client.evaluate(expression)


def login(client, profile):
    wait(client, "!document.querySelector('#session-button').disabled")
    client.evaluate("document.querySelector('#profile-select').value=" + json.dumps(profile) + ";document.querySelector('#profile-select').dispatchEvent(new Event('change'));document.querySelector('#session-button').click()")
    wait(client, "document.querySelector('#principal').textContent.includes(" + json.dumps("운영 담당" if profile.endswith("operator") else "검토자") + ") && document.querySelectorAll('.incident-card').length===4 && !document.querySelector('#analyze-button').disabled")


def select(client, incident_id):
    client.evaluate("Array.from(document.querySelectorAll('.incident-card')).find(b=>b.textContent.includes(" + json.dumps(incident_id) + ")).click()")
    wait(client, "document.querySelector('#incident-id').textContent===" + json.dumps(incident_id) + " && !document.querySelector('#analyze-button').disabled")


def baseline(client):
    wait(client, "!document.querySelector('#analyze-button').disabled")
    previous = client.evaluate("document.querySelector('#analysis-meta').textContent")
    client.evaluate("document.querySelector('input[name=mode][value=baseline]').checked=true;document.querySelector('#analysis-question').value='합성 운영 담당 브라우저 회귀';document.querySelector('#analysis-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    wait(client, "!document.querySelector('#analysis-result').hidden && !document.querySelector('#analyze-button').disabled && document.querySelector('#analysis-meta').textContent!==" + json.dumps(previous))
    analysis_id = client.evaluate("document.querySelector('#analysis-meta').textContent.split(' / ')[0]")
    if not analysis_id:
        raise AssertionError("No stored analysis ID")
    return analysis_id


def open_analysis(client, analysis_id):
    client.evaluate("Array.from(document.querySelectorAll('#audit-list .audit-event')).find(row=>row.textContent.includes(" + json.dumps(analysis_id) + ")).querySelector('button').click()")
    wait(client, "!document.querySelector('#analysis-result').hidden && document.querySelector('#analysis-meta').textContent.startsWith(" + json.dumps(analysis_id) + ") && !document.querySelector('#analyze-button').disabled")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/operator-review-browser.json")
    args = parser.parse_args()
    client = connect()
    try:
        client.call("Emulation.setDeviceMetricsOverride", {"width":1440, "height":1080, "deviceScaleFactor":1, "mobile":False})
        client.call("Page.navigate", {"url":APP})
        wait(client, "document.querySelectorAll('#profile-select option').length===6 && !document.querySelector('#session-button').disabled")
        results = []
        for decision in ("approved", "rejected"):
            login(client, "A-operator")
            select(client, "INC-A-001")
            analysis_id = baseline(client)
            assert client.evaluate("document.querySelector('#approve-button').disabled"), "operator received reviewer UI permission"
            login(client, "A-reviewer")
            select(client, "INC-A-001")
            open_analysis(client, analysis_id)
            assert client.evaluate("!document.querySelector('#approve-button').disabled"), "operator-safe baseline gate did not pass"
            button = "#approve-button" if decision == "approved" else "#reject-button"
            client.evaluate("document.querySelector('#review-comment').value=" + json.dumps("합성 UI 회귀: " + decision) + ";document.querySelector(" + json.dumps(button) + ").click()")
            wait(client, "!document.querySelector('#review-existing').hidden && !document.querySelector('#analyze-button').disabled")
            reviewer_text = client.evaluate("document.querySelector('#review-existing').textContent")
            assert ("승인 기록됨" if decision == "approved" else "반려 기록됨") in reviewer_text
            login(client, "A-operator")
            select(client, "INC-A-001")
            open_analysis(client, analysis_id)
            observed = client.evaluate("({status:document.querySelector('#analysis-status').textContent,review:document.querySelector('#review-existing').textContent,comment:document.querySelector('#review-existing').querySelector('p')?.textContent||'',audit:document.querySelector('#audit-list').textContent,approve_disabled:document.querySelector('#approve-button').disabled})")
            assert observed["status"] == "검토 완료", observed
            assert "검토 기록 있음" in observed["review"], observed
            assert "승인" not in observed["review"] and "반려" not in observed["review"], observed
            assert not observed["comment"], observed
            assert observed["approve_disabled"], observed
            assert "합성 UI 회귀:" not in observed["audit"], observed
            assert "approved" not in observed["audit"] and "rejected" not in observed["audit"], observed
            results.append({"analysis_id":analysis_id, "actual_reviewer_decision":decision, "operator_status":observed["status"], "operator_review_label":observed["review"], "private_review_fields_absent":True})
        result = {"real_browser":True, "synthetic":True, "model_requests":0, "passed":True, "cases":results}
        target = ROOT / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        client.socket.close()


if __name__ == "__main__":
    main()
