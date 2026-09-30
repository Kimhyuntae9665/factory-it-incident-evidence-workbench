"""Native incident-queue Tab/Enter reproduction and focus checks; GPU0.

Creates/closes only its own tab in an existing sandboxed Chrome. Queue reads and
synthetic session creation are real; the delayed case pauses a real source GET.
No source-response fabrication, model request, or review mutation is used.
"""
import argparse
import base64
import hashlib
import json
import urllib.request
from pathlib import Path
from scripts.browser_smoke import CDP
from scripts import operator_review_browser as workflow

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('before','after'),required=True)
    parser.add_argument('--cdp',default='http://127.0.0.1:19085')
    args=parser.parse_args()
    with urllib.request.urlopen(urllib.request.Request(args.cdp+'/json/new?about:blank',method='PUT'),timeout=10) as response:page=json.load(response)
    client=CDP(page['webSocketDebuggerUrl'])
    output=ROOT/'artifacts/queue-keyboard'/args.phase;output.mkdir(parents=True,exist_ok=True)
    result={'phase':args.phase,'actual_browser':True,'synthetic':True,'model_requests':0,'checks':[],'cases':[],'screenshots':[]}
    def check(expression,label):
        assert client.evaluate(expression),label
        result['checks'].append(label)
    def key(name,shift=False):
        code={'Tab':9,'Enter':13,'ArrowLeft':37}[name]
        parameters={'key':name,'code':name,'windowsVirtualKeyCode':code,'nativeVirtualKeyCode':code,'modifiers':8 if shift else 0}
        client.call('Input.dispatchKeyEvent',{'type':'keyDown',**parameters,**({'text':'\r'} if name=='Enter' else {})})
        client.call('Input.dispatchKeyEvent',{'type':'keyUp',**parameters})
    def capture(name):
        client.call('Page.bringToFront');client.call('Emulation.setPageScaleFactor',{'pageScaleFactor':1})
        client.evaluate('new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(done)),500))))')
        check("!/Bearer\\s+[A-Za-z0-9]|BEGIN [A-Z ]*PRIVATE KEY|[A-Z]:\\\\Users/.test(document.body.textContent)",'capture excludes authentication/private path')
        metadata=client.evaluate("({incident:document.querySelector('#incident-id').textContent,principal:document.querySelector('#principal').textContent,css_width:innerWidth,scale:visualViewport.scale,overflow:document.documentElement.scrollWidth>innerWidth,task:document.body.dataset.task,focus:{id:document.activeElement.id,tag:document.activeElement.tagName,class:document.activeElement.className,queue_id:document.activeElement.querySelector('.card-top span')?.textContent||null},old_origin_connected:window.__queueOrigin?.isConnected})")
        data=base64.b64decode(client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data']);(output/name).write_bytes(data)
        result['screenshots'].append({'file':name,'sha256':hashlib.sha256(data).hexdigest(),'actual_ui':True,**metadata})
    def selected_queue():return "document.activeElement.classList.contains('incident-card') && document.activeElement.querySelector('.card-top span').textContent==='INC-A-002' && document.activeElement.getAttribute('aria-current')==='true'"
    try:
        client.call('Page.enable');client.call('Runtime.enable')
        client.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
        client.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1080,'deviceScaleFactor':1,'mobile':False})
        client.call('Page.navigate',{'url':workflow.APP})
        workflow.wait(client,"document.querySelectorAll('#profile-select option').length===6 && !document.querySelector('#session-button').disabled")
        workflow.login(client,'A-reviewer')
        for layout in ('desktop','mobile'):
            client.call('Emulation.setDeviceMetricsOverride',{'width':1440 if layout=='desktop' else 390,'height':1080 if layout=='desktop' else 1000,'deviceScaleFactor':1,'mobile':layout=='mobile'})
            workflow.select(client,'INC-A-001')
            workflow.wait(client,"!document.querySelector('.incident-card').disabled")
            if layout=='mobile':
                client.evaluate("document.querySelector('#task-cases').focus()")
                key('Enter')
                check("document.body.dataset.task==='cases' && getComputedStyle(document.querySelector('.sidebar')).display!=='none'",'mobile native Enter opens incident queue task')
            else:client.evaluate("document.querySelector('#session-button').focus()")
            key('Tab');key('Tab')
            check("document.activeElement===document.querySelectorAll('.incident-card')[1]",layout+' native Tab reaches second incident queue row')
            client.evaluate('window.__queueOrigin=document.activeElement')
            key('Enter')
            workflow.wait(client,"document.querySelector('#incident-id').textContent==='INC-A-002' && !document.querySelector('#analyze-button').disabled && !document.querySelector('.incident-card').disabled")
            check("document.querySelector('.incident-card.selected .card-top span').textContent==='INC-A-002' && document.querySelector('#document-content').textContent.length>0",layout+' native Enter loads intended incident and accessible source')
            check("document.querySelector('#principal').textContent.includes('사이트 A / 검토자')",layout+' selection preserves authenticated profile')
            observed=client.evaluate("({tag:document.activeElement.tagName,id:document.activeElement.id,class:document.activeElement.className,old_origin_connected:window.__queueOrigin.isConnected})")
            if args.phase=='before':
                check('document.activeElement===document.body',layout+' reproduced focus drops to body after queue render')
                assert observed['old_origin_connected'] is False,'Queue origin was not rebuilt'
            elif layout=='desktop':check(selected_queue(),'desktop completed selection restores exact selected queue row')
            else:
                check("document.activeElement.id==='incident-title' && document.querySelector('#incident-title').textContent==='MES 주문 조회 실패' && document.body.dataset.task==='sources' && getComputedStyle(document.querySelector('.sidebar')).display==='none'",'mobile completed selection focuses visible incident heading in source task')
                check("(()=>{const e=document.querySelector('#incident-title'),r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()",'mobile focused incident heading is visible in viewport')
            capture(layout+'-queue-selection.png')
            if args.phase=='after':
                if layout=='mobile':
                    key('Tab',shift=True)
                    check("document.activeElement.id==='task-sources'",'mobile ShiftTab reaches active task control from incident heading')
                    key('ArrowLeft')
                    check("document.activeElement.id==='task-cases' && document.body.dataset.task==='cases'",'mobile native ArrowLeft returns to incident queue task')
                    key('Tab');key('Tab')
                    check(selected_queue(),'mobile native Tab returns to exact selected incident row')
                key('Tab')
                check("document.activeElement.classList.contains('incident-card') && document.activeElement.querySelector('.card-top span').textContent==='INC-A-003'",layout+' next native Tab continues queue position')
            if layout=='mobile':check("innerWidth===390 && visualViewport.scale===1 && document.documentElement.scrollWidth<=390",'native mobile390 has no auto-shrink/page overflow')
            result['cases'].append({'layout':layout,'observed':observed,'passed':True})
        if args.phase=='after':
            # Keep a later explicit keyboard focus choice during a genuinely delayed GET.
            client.evaluate("document.querySelectorAll('.incident-card')[1].focus();window.__queueNativeFetch=window.fetch;window.fetch=(()=>{const original=window.fetch;return async(...args)=>{if(String(args[0]).startsWith('/api/evidence?'))await new Promise(done=>window.__queueRelease=done);return original(...args)}})()")
            key('Enter')
            workflow.wait(client,"typeof window.__queueRelease==='function' && document.querySelector('.incident-card').disabled")
            client.evaluate("document.querySelector('#task-review').focus()")
            key('Enter')
            client.evaluate("window.__queueRelease();window.fetch=window.__queueNativeFetch;delete window.__queueRelease;delete window.__queueNativeFetch")
            workflow.wait(client,"!document.querySelector('#analyze-button').disabled")
            check("document.activeElement.id==='task-review' && document.body.dataset.task==='review'",'delayed real queue read does not steal a later explicit focus/task choice')
        result['passed']=True
        (output/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'passed':True,'phase':args.phase,'cases':len(result['cases']),'checks':len(result['checks']),'screenshots':len(result['screenshots']),'model_requests':0}))
    except Exception as error:
        result.update(passed=False,error=str(error));(output/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        client.socket.close()
        with urllib.request.urlopen(args.cdp+'/json/close/'+page['id'],timeout=10):pass

if __name__=='__main__':main()
