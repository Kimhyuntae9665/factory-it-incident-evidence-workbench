"""Native Tab/Enter candidate focus regression; actual loopback UI, GPU0.

Only this driver's new tab is used. Before mode records the existing candidate
return fallback. After mode checks stable candidate identity and citation return.
All analyses are baseline-only; no actual model request is made.
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
    output=ROOT/'artifacts/candidate-keyboard'/args.phase;output.mkdir(parents=True,exist_ok=True)
    result={'phase':args.phase,'actual_browser':True,'synthetic':True,'model_requests':0,'checks':[],'cases':[],'screenshots':[]}
    def check(expression,label):
        assert client.evaluate(expression),label
        result['checks'].append(label)
    def key(name):
        code={'Tab':9,'Enter':13}[name]
        client.call('Input.dispatchKeyEvent',{'type':'keyDown','key':name,'code':name,'windowsVirtualKeyCode':code,'nativeVirtualKeyCode':code,**({'text':'\r'} if name=='Enter' else {})})
        client.call('Input.dispatchKeyEvent',{'type':'keyUp','key':name,'code':name,'windowsVirtualKeyCode':code,'nativeVirtualKeyCode':code})
    def capture(name):
        client.call('Page.bringToFront');client.call('Emulation.setPageScaleFactor',{'pageScaleFactor':1})
        client.evaluate('new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(done)),500))))')
        check("!/Bearer\\s+[A-Za-z0-9]|BEGIN [A-Z ]*PRIVATE KEY|[A-Z]:\\\\Users/.test(document.body.textContent)",'capture excludes authentication/private path')
        metadata=client.evaluate("({css_width:innerWidth,scale:visualViewport.scale,overflow:document.documentElement.scrollWidth>innerWidth,focus:{id:document.activeElement.id,tag:document.activeElement.tagName,class:document.activeElement.className,text:document.activeElement.textContent.trim().slice(0,160)}})")
        data=base64.b64decode(client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data']);(output/name).write_bytes(data)
        result['screenshots'].append({'file':name,'sha256':hashlib.sha256(data).hexdigest(),'actual_ui':True,**metadata})
    try:
        client.call('Page.enable');client.call('Runtime.enable')
        client.call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
        client.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1080,'deviceScaleFactor':1,'mobile':False})
        client.call('Page.navigate',{'url':workflow.APP})
        workflow.wait(client,"document.querySelectorAll('#profile-select option').length===6 && !document.querySelector('#session-button').disabled")
        workflow.login(client,'A-reviewer')
        for layout in ('desktop','mobile'):
            client.call('Emulation.setDeviceMetricsOverride',{'width':1440 if layout=='desktop' else 390,'height':1080 if layout=='desktop' else 1000,'deviceScaleFactor':1,'mobile':layout=='mobile'})
            workflow.select(client,'INC-A-002')
            workflow.wait(client,"document.querySelectorAll('.evidence-card').length>=2 && !document.querySelector('.evidence-card').disabled")
            client.evaluate("document.querySelector('#task-sources').click();document.querySelector('.source-picker').open=false;document.querySelector('.source-picker summary').focus()")
            key('Enter')
            check("document.querySelector('.source-picker').open",layout+' native Enter opens candidate selector')
            for _ in range(4):key('Tab')
            check("document.activeElement===document.querySelectorAll('.evidence-card')[1]",layout+' native Tab reaches second candidate')
            client.evaluate("window.__candidateOrigin=document.activeElement;window.__candidateTitle=document.activeElement.querySelector('strong').textContent")
            key('Enter')
            workflow.wait(client,"document.activeElement.id==='document-title' && document.querySelector('#document-title').textContent===window.__candidateTitle && !document.querySelector('.evidence-card').disabled")
            check("document.querySelector('.evidence-card.selected strong').textContent===window.__candidateTitle",layout+' native Enter opens intended latest accessible document')
            origin_connected=client.evaluate('window.__candidateOrigin.isConnected')
            key('Tab')
            check("document.activeElement.id==='return-claim'",layout+' native Tab reaches original-item return control')
            key('Enter')
            observed=client.evaluate("({selected_title:window.__candidateTitle,focus_tag:document.activeElement.tagName,focus_class:document.activeElement.className,focus_title:document.activeElement.querySelector('strong')?.textContent||document.activeElement.textContent.trim()})")
            if args.phase=='before':
                check("document.activeElement===document.querySelector('.source-picker summary')",layout+' reproduced candidate return falls back to list summary')
                assert origin_connected is False,'Expected old candidate node to be rebuilt'
            else:
                check("document.activeElement.classList.contains('evidence-card') && document.activeElement.querySelector('strong').textContent===window.__candidateTitle && document.activeElement.getAttribute('aria-pressed')==='true'",layout+' return focuses exact originating selected candidate')
                key('Tab')
                check("document.activeElement.classList.contains('evidence-card')",layout+' next native Tab continues candidate list from restored position')
                client.evaluate("document.querySelector('.evidence-card.selected').focus()")
            capture(layout+'-candidate-return.png')
            if layout=='mobile':check("innerWidth===390 && visualViewport.scale===1 && document.documentElement.scrollWidth<=390",'native mobile390 has no auto-shrink/page overflow')
            result['cases'].append({'layout':layout,'old_origin_connected':origin_connected,'observed':observed,'passed':True})
        if args.phase=='after':
            client.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1080,'deviceScaleFactor':1,'mobile':False})
            workflow.baseline(client)
            client.evaluate("document.querySelectorAll('.citation-card')[1].focus();window.__citationOrigin=document.activeElement")
            key('Enter')
            workflow.wait(client,"document.activeElement.id==='document-title' && document.querySelector('#citation-check').textContent.includes('정확히 일치')")
            check("document.querySelector('#document-content mark')!==null",'native citation Enter retains server-verified exact quote highlight')
            key('Tab');key('Enter')
            check("document.activeElement===window.__citationOrigin && document.body.dataset.task==='review'",'citation return retains original connected claim identity')
        result['passed']=True
        (output/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'passed':True,'phase':args.phase,'cases':len(result['cases']),'checks':len(result['checks']),'screenshots':len(result['screenshots']),'model_requests':0}))
    except Exception as error:
        result.update(passed=False,error=str(error));(output/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        client.socket.close()
        with urllib.request.urlopen(args.cdp+'/json/close/'+page['id'],timeout=10):pass

if __name__=='__main__':main()
