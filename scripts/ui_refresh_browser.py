"""Actual 01 UI before/after, recovery, ACL, keyboard and mobile checks. No model request."""
import argparse,base64,json,os
from pathlib import Path
from scripts import operator_review_browser as workflow
from scripts.gallery_capture import analyze,quote
from scripts import operator_review_browser
workflow.CDP_ROOT="http://127.0.0.1:19086"
ROOT=Path(__file__).resolve().parents[1]
CONTRAST_CHECK="(()=>{\n  const rgb=value=>{const m=value.match(/[\\d.]+/g)||[];return [Number(m[0]||0),Number(m[1]||0),Number(m[2]||0),m[3]===undefined?1:Number(m[3])];};\n  const blend=(top,bottom)=>top.slice(0,3).map((n,i)=>n*top[3]+bottom[i]*(1-top[3]));\n  const lum=value=>value.map(n=>{n/=255;return n<=0.04045?n/12.92:Math.pow((n+0.055)/1.055,2.4);}).reduce((s,n,i)=>s+n*[.2126,.7152,.0722][i],0);\n  const inspect=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);\n  const failures=[],smallKorean=[],checked=[];\n  let item;\n  while(item=inspect.nextNode()){\n    const text=item.textContent.trim();if(!text)continue;\n    const parent=item.parentElement;if(!parent||parent.closest('script,style,[hidden]'))continue;\n    const rect=parent.getBoundingClientRect(),style=getComputedStyle(parent);\n    if(!rect.width||!rect.height||style.visibility==='hidden'||style.display==='none')continue;\n    let p=parent,chain=[],skip=false;\n    while(p){const cs=getComputedStyle(p);if(Number(cs.opacity)<1||p.matches(':disabled'))skip=true;chain.push(p);p=p.parentElement;}\n    if(skip)continue;\n    let bg=[255,255,255];\n    chain.reverse().forEach(el=>{bg=blend(rgb(getComputedStyle(el).backgroundColor),bg);});\n    const fg=blend(rgb(style.color),bg),a=lum(fg),b=lum(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);\n    const size=parseFloat(style.fontSize),snippet=text.slice(0,90),entry={text:snippet,size,contrast:Number(ratio.toFixed(3)),element:parent.id||parent.className||parent.tagName};\n    checked.push(entry);\n    if(/[가-힣]/.test(text)&&size<14)smallKorean.push(entry);\n    const large=size>=24||(size>=18.66&&Number(style.fontWeight)>=700);\n    if(ratio<(large?3:4.5))failures.push(entry);\n  }\n  return {checked:checked.length,minimum_normal_contrast:Math.min(...checked.filter(e=>e.size<24).map(e=>e.contrast)),contrast_failures:failures,korean_below14:smallKorean,limitation:'computed-style text/background sampling; inactive controls, opaque media and forced-colors behavior excluded'};\n})()"
def screenshot(client,path):
    text=client.evaluate("document.body.textContent")
    assert "Bearer " not in text
    assert not any(item and item in text for item in (str(Path.home()),os.environ.get("USER","")))
    path.write_bytes(base64.b64decode(client.call("Page.captureScreenshot",{"format":"png","captureBeyondViewport":False})["data"]))
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--before",action="store_true")
    args=parser.parse_args()
    out=ROOT/"artifacts/ui-refresh"
    out.mkdir(exist_ok=True,parents=True)
    c=workflow.connect()
    try:
        c.call("Emulation.setDeviceMetricsOverride",{"width":1440,"height":1080,"deviceScaleFactor":1,"mobile":False})
        c.call("Page.navigate",{"url":workflow.APP})
        workflow.wait(c,"document.querySelectorAll('#profile-select option').length===6 && !document.querySelector('#session-button').disabled")
        workflow.login(c,"A-reviewer")
        workflow.select(c,"INC-A-002")
        analyze(c)
        quote(c,1)
        c.evaluate("window.scrollTo(0,0)")
        screenshot(c,out/("before-desktop.png" if args.before else "after-desktop.png"))
        if args.before:
            c.call("Emulation.setDeviceMetricsOverride",{"width":390,"height":1000,"deviceScaleFactor":1,"mobile":True})
            c.evaluate("window.scrollTo(0,0)")
            screenshot(c,out/"before-mobile.png")
            print("PASS before capture; model_requests=0",flush=True)
            return

        results={"actual_browser":True,"synthetic":True,"model_requests":0,"checks":{}}
        results["contrast"]=c.evaluate(CONTRAST_CHECK)
        assert not results["contrast"]["contrast_failures"],results["contrast"]["contrast_failures"]
        assert not results["contrast"]["korean_below14"],results["contrast"]["korean_below14"]
        results["checks"]["text_contrast_and_korean_size"]=True
        assert c.evaluate("document.querySelector('#document-content').getBoundingClientRect().top<900"),"Original text remains below desktop viewport"
        results["checks"]["source_visible_in_desktop_viewport"]=True
        c.evaluate("document.querySelector('#profile-select').focus()")
        c.call("Input.dispatchKeyEvent",{"type":"keyDown","key":"Tab","code":"Tab","windowsVirtualKeyCode":9})
        c.call("Input.dispatchKeyEvent",{"type":"keyUp","key":"Tab","code":"Tab","windowsVirtualKeyCode":9})
        assert c.evaluate("document.activeElement.id==='session-button'")
        results["checks"]["keyboard_session_focus"]=True
        # Reduced-motion citation navigation and focus return to the actual claim.
        c.call("Emulation.setEmulatedMedia",{"features":[{"name":"prefers-reduced-motion","value":"reduce"}]})
        c.evaluate("window.__scrollModes=[];window.__nativeScroll=Element.prototype.scrollIntoView;Element.prototype.scrollIntoView=function(options){window.__scrollModes.push(options?.behavior);return window.__nativeScroll.call(this,options)};document.querySelectorAll('.citation-card')[1].focus();document.querySelectorAll('.citation-card')[1].click()")
        workflow.wait(c,"document.activeElement.id==='document-title' && document.querySelector('#citation-check').textContent.includes('정확히 일치')")
        assert c.evaluate("window.__scrollModes.every(mode=>mode==='auto')")
        c.evaluate("document.querySelector('#return-claim').click()")
        assert c.evaluate("document.activeElement.classList.contains('citation-card')")
        c.evaluate("Element.prototype.scrollIntoView=window.__nativeScroll")
        c.call("Emulation.setEmulatedMedia",{"features":[]})
        results["checks"]["reduced_motion_citation_focus_and_return"]=True
        c.call("Emulation.setDeviceMetricsOverride",{"width":720,"height":540,"deviceScaleFactor":2,"mobile":False})
        assert not c.evaluate("document.documentElement.scrollWidth>window.innerWidth")
        c.evaluate("document.querySelector('#profile-select').focus()")
        assert c.evaluate("document.activeElement.id==='profile-select'")
        screenshot(c,out/"after-200-percent-reflow.png")
        c.call("Emulation.setDeviceMetricsOverride",{"width":1440,"height":1080,"deviceScaleFactor":1,"mobile":False})
        results["checks"]["two_hundred_percent_equivalent_reflow"]=True
        c.evaluate("document.querySelector('.case-timeline').open=true;document.querySelector('.case-timeline').scrollIntoView({block:'start'})")
        screenshot(c,out/"after-timeline.png")
        c.evaluate("document.querySelector('.case-timeline').open=false;window.scrollTo(0,0)")
        c.call("Emulation.setDeviceMetricsOverride",{"width":390,"height":1000,"deviceScaleFactor":1,"mobile":True})
        c.evaluate("document.querySelector('#task-sources').click();document.querySelector('#workspace').scrollIntoView({block:'start'})")
        assert c.evaluate("getComputedStyle(document.querySelector('.sidebar')).display==='none' && getComputedStyle(document.querySelector('.evidence-pane')).display!=='none' && getComputedStyle(document.querySelector('.analysis-pane')).display==='none'")
        assert not c.evaluate("document.documentElement.scrollWidth>window.innerWidth")
        screenshot(c,out/"after-mobile-source.png")
        c.evaluate("document.querySelector('#task-review').click();document.querySelector('#task-review').focus();window.scrollTo(0,0)")
        screenshot(c,out/"after-mobile-review.png")
        c.call("Input.dispatchKeyEvent",{"type":"keyDown","key":"ArrowLeft","code":"ArrowLeft","windowsVirtualKeyCode":37})
        c.call("Input.dispatchKeyEvent",{"type":"keyUp","key":"ArrowLeft","code":"ArrowLeft","windowsVirtualKeyCode":37})
        assert c.evaluate("document.body.dataset.task==='sources' && document.activeElement.id==='task-sources'")
        c.call("Input.dispatchKeyEvent",{"type":"keyDown","key":"Home","code":"Home","windowsVirtualKeyCode":36})
        c.call("Input.dispatchKeyEvent",{"type":"keyUp","key":"Home","code":"Home","windowsVirtualKeyCode":36})
        assert c.evaluate("document.body.dataset.task==='cases' && document.activeElement.id==='task-cases'")
        assert not c.evaluate("document.documentElement.scrollWidth>window.innerWidth")
        screenshot(c,out/"after-mobile-cases.png")
        results["checks"]["mobile_task_tabs_keyboard_and_overflow"]=True
        c.call("Emulation.setDeviceMetricsOverride",{"width":1440,"height":1080,"deviceScaleFactor":1,"mobile":False})
        # Simulate a restart-invalidated opaque token using only authenticated GETs.
        c.evaluate("sessionStorage.setItem('trace-demo-session-v1',JSON.stringify({token:'expired-synthetic-recovery-check',principal:{id:'A-reviewer',site:'A',role:'reviewer'}}))")
        probe=c.call("Page.addScriptToEvaluateOnNewDocument",{"source":"window.__recoveryCalls=[];const f=window.fetch.bind(window);window.fetch=(path,options={})=>{window.__recoveryCalls.push({path:String(path),method:options.method||'GET'});return f(path,options)};"})["identifier"]
        c.call("Page.navigate",{"url":workflow.APP})
        workflow.wait(c,"document.querySelector('#notice').textContent.includes('세션이 만료') && !document.querySelector('#session-button').disabled && sessionStorage.getItem('trace-demo-session-v1')===null")
        assert c.evaluate("document.querySelectorAll('.incident-card').length===0 && document.querySelector('#incident-workspace').hidden && document.querySelector('#analyze-button').disabled")
        calls=c.evaluate("window.__recoveryCalls")
        assert all(item["method"]=="GET" for item in calls),calls
        assert sum(item["path"]=="/api/incidents" for item in calls)==2,calls
        results["checks"]["expired403_readonly_probe_clears_session"]=True
        results["recovery_calls"]=calls
        screenshot(c,out/"after-expired-session.png")
        c.call("Page.removeScriptToEvaluateOnNewDocument",{"identifier":probe})
        workflow.login(c,"A-reviewer")
        workflow.select(c,"INC-A-002")
        analyze(c)
        quote(c,1)
        results["checks"]["explicit_relogin_recovers"]=True
        # Verify a stored analysis restores focused in reduced-motion mode.
        stored=c.evaluate("document.querySelector('#analysis-meta').textContent.split(' / ')[0]")
        c.call("Emulation.setEmulatedMedia",{"features":[{"name":"prefers-reduced-motion","value":"reduce"}]})
        c.evaluate("window.__restoreScroll=[];window.__nativeRestore=Element.prototype.scrollIntoView;Element.prototype.scrollIntoView=function(options){window.__restoreScroll.push(options?.behavior);return window.__nativeRestore.call(this,options)}")
        workflow.open_analysis(c,stored)
        assert c.evaluate("document.activeElement.id==='analysis-result' && window.__restoreScroll.every(mode=>mode==='auto')")
        c.evaluate("Element.prototype.scrollIntoView=window.__nativeRestore")
        c.call("Emulation.setEmulatedMedia",{"features":[]})
        results["checks"]["stored_analysis_reduced_motion_focus"]=True
        # Browser response mock for a protected-read 403; session probe stays real.
        # This verifies the distinction without adding an unsafe backend endpoint.
        old=c.evaluate("sessionStorage.getItem('trace-demo-session-v1')")
        c.evaluate("window.__realFetch=window.fetch.bind(window);window.__aclProbe=[];window.fetch=(path,options={})=>{window.__aclProbe.push({path:String(path),method:options.method||'GET'});if(String(path).startsWith('/api/evidence/'))return Promise.resolve(new Response(JSON.stringify({error:'Synthetic UI ACL regression'}),{status:403,headers:{'Content-Type':'application/json'}}));return window.__realFetch(path,options);};document.querySelector('.source-picker').open=true;document.querySelector('.evidence-card').click()")
        workflow.wait(c,"document.querySelector('#notice').textContent.includes('허용되지 않은') && !document.querySelector('#analyze-button').disabled")
        assert c.evaluate("sessionStorage.getItem('trace-demo-session-v1')")==old
        acl_calls=c.evaluate("window.__aclProbe")
        assert any(item["path"]=="/api/incidents" and item["method"]=="GET" for item in acl_calls)
        results["checks"]["mock_acl403_real_valid_probe_preserves_session"]=True
        c.evaluate("window.fetch=window.__realFetch")
        # A failed validation read must also retain identity; it proves no expiry.
        c.evaluate("window.fetch=(path,options={})=>{if(String(path).startsWith('/api/evidence/'))return Promise.resolve(new Response(JSON.stringify({error:'Synthetic UI ACL regression'}),{status:403,headers:{'Content-Type':'application/json'}}));if(String(path)==='/api/incidents')return Promise.reject(new TypeError('Synthetic unavailable probe'));return window.__realFetch(path,options);};document.querySelector('.evidence-card').click()")
        workflow.wait(c,"!document.querySelector('#analyze-button').disabled && document.querySelector('#notice').textContent.includes('허용되지 않은')")
        assert c.evaluate("sessionStorage.getItem('trace-demo-session-v1')")==old
        results["checks"]["uncertain_probe_preserves_session"]=True
        c.evaluate("window.fetch=window.__realFetch")
        # Exercise both genuine review decisions against operator-redacted responses.
        operator_review_browser.CDP_ROOT=workflow.CDP_ROOT
        saved_args=__import__("sys").argv
        try:
            __import__("sys").argv=["operator_review_browser","--output","artifacts/ui-refresh/operator-neutral.json"]
            operator_review_browser.main()
        finally:__import__("sys").argv=saved_args
        results["checks"]["actual_approved_and_rejected_operator_neutral"]=True
        c.evaluate("document.querySelector('.review-block').scrollIntoView({block:'start'});window.scrollBy(0,-20)")
        screenshot(c,out/"after-operator-neutral-review.png")

        # A browser-only response-delay mock commits one real synthetic review.
        # Shorten the UI's timeout; reconcile with GET and never repeat the POST.
        workflow.login(c,"A-reviewer")
        workflow.select(c,"INC-A-001")
        analyze(c)
        c.evaluate("window.__timeoutNativeFetch=window.fetch.bind(window);window.__timeoutNativeTimer=window.setTimeout;window.__reviewPostCount=0;window.__timeoutCalls=[];window.setTimeout=(fn,delay,...args)=>window.__timeoutNativeTimer(fn,delay===15000?150:delay,...args);window.fetch=(path,options={})=>{window.__timeoutCalls.push({path:String(path),method:options.method||'GET'});if(String(path).endsWith('/review')&&options.method==='POST'){window.__reviewPostCount++;return new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(new DOMException('Synthetic delayed response','AbortError')),{once:true});window.__timeoutNativeFetch(path,{...options,signal:undefined}).catch(reject);});}return window.__timeoutNativeFetch(path,options);};document.querySelector('#review-comment').value='합성 UI 응답 지연 회귀: 기존 기록을 GET으로 확인';document.querySelector('#approve-button').click()")
        workflow.wait(c,"document.querySelector('#notice').textContent.includes('기존 검토 기록을 확인') && !document.querySelector('#analyze-button').disabled")
        assert c.evaluate("window.__reviewPostCount===1 && !document.querySelector('#review-existing').hidden")
        assert c.evaluate("document.querySelector('#analysis-status').textContent==='승인됨' && !document.querySelector('#gate-title').textContent.includes('사람 검토 필요')")
        assert c.evaluate("window.__timeoutCalls.some(item=>item.path.startsWith('/api/analyses/')&&item.method==='GET')")
        results["checks"]["delayed_review_get_reconciliation_single_post"]=True
        results["review_delay_mock"]=True
        c.evaluate("window.fetch=window.__timeoutNativeFetch;window.setTimeout=window.__timeoutNativeTimer")
        c.evaluate("document.querySelector('.review-block').scrollIntoView({block:'start'});window.scrollBy(0,-20)")
        screenshot(c,out/"after-reviewed-record.png")
        results["reviewed_contrast"]=c.evaluate(CONTRAST_CHECK)
        assert not results["reviewed_contrast"]["contrast_failures"]


        # Deterministic browser-response mock for backend retrieval failure metadata.
        # The real compare POST remains baseline; no model is requested.
        workflow.select(c,"INC-A-002")
        c.evaluate("window.__retrievalNative=window.fetch.bind(window);window.fetch=async(path,options={})=>{const response=await window.__retrievalNative(path,options);if(String(path).endsWith('/analyze')&&response.ok){const p=await response.json();p.analysis.mode='degraded';p.analysis.status='degraded';p.analysis.metrics={failure_stage:'retrieval',retrieval_error_kind:'retrieval_unavailable',requested_mode:'baseline'};p.analysis.summary='모의 회귀: 근거 검색 실패';p.analysis.facts=[];p.analysis.hypotheses=[];p.analysis.counterevidence=[];p.analysis.citations=[];p.analysis.gate={passed:false,issues:['모의 검색 실패']};return new Response(JSON.stringify(p),{status:200,headers:{'Content-Type':'application/json'}})}return response;}")
        analyze(c)
        assert c.evaluate("document.querySelector('#analysis-mode-badge').textContent.includes('근거 검색 실패') && document.querySelector('#analysis-status').textContent==='검색 실패' && document.querySelector('#approve-button').disabled && document.querySelector('#gate-issues').textContent.includes('모델 추출은 실행하지')")
        results["checks"]["mock_retrieval_failure_distinct_and_approval_blocked"]=True
        results["retrieval_failure_mock"]=True
        c.evaluate("window.fetch=window.__retrievalNative")
        workflow.select(c,"INC-A-002")
        analyze(c)
        results["passed"]=True
        (out/"result.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(results,ensure_ascii=False),flush=True)
    finally:c.socket.close()
if __name__=="__main__":main()
