"""Real sandboxed Chrome UI smoke through loopback CDP; no browser downloads."""
import socket,struct,json,os,base64,time,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
class CDP:
    def __init__(self,url):
        u=urlsplit(url);self.socket=socket.create_connection((u.hostname,u.port),timeout=15);self.counter=0
        key=base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall(("GET "+u.path+" HTTP/1.1\r\nHost: "+u.netloc+"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: "+key+"\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        data=b""
        while b"\r\n\r\n" not in data:data+=self.socket.recv(1)
        if b" 101 " not in data:raise RuntimeError(data.decode())
    def exact(self,n):
        data=b""
        while len(data)<n:
            part=self.socket.recv(n-len(data))
            if not part:raise RuntimeError("CDP disconnected")
            data+=part
        return data
    def send(self,data,opcode=1):
        mask=os.urandom(4);n=len(data)
        head=bytes([0x80|opcode,0x80|n]) if n<126 else bytes([0x80|opcode,0xfe])+struct.pack("!H",n) if n<65536 else bytes([0x80|opcode,0xff])+struct.pack("!Q",n)
        self.socket.sendall(head+mask+bytes(value^mask[index%4] for index,value in enumerate(data)))
    def receive(self):
        chunks=[]
        while True:
            a,b=self.exact(2);n=b&127
            if n==126:n=struct.unpack("!H",self.exact(2))[0]
            elif n==127:n=struct.unpack("!Q",self.exact(8))[0]
            mask=self.exact(4) if b&128 else None
            payload=self.exact(n)
            if mask:payload=bytes(v^mask[i%4] for i,v in enumerate(payload))
            if a&15==9:self.send(payload,10);continue
            if a&15==8:raise RuntimeError("CDP closed")
            chunks.append(payload)
            if a&128:return json.loads(b"".join(chunks))
    def call(self,method,params=None):
        self.counter+=1;wanted=self.counter
        self.send(json.dumps({"id":wanted,"method":method,"params":params or {}}).encode())
        while True:
            response=self.receive()
            if response.get("id")==wanted:
                if "error" in response:raise RuntimeError(response["error"])
                return response.get("result",{})
    def evaluate(self,expression):
        result=self.call("Runtime.evaluate",{"expression":expression,"awaitPromise":True,"returnByValue":True})
        if "exceptionDetails" in result:raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")
    def wait(self,condition):
        return self.evaluate("(async()=>{for(let i=0;i<100;i++){if("+condition+")return true;await new Promise(r=>setTimeout(r,100));}throw new Error('UI wait timed out');})()")
def main():
    (ROOT/"artifacts").mkdir(exist_ok=True)
    targets=json.load(urllib.request.urlopen("http://127.0.0.1:19085/json"))
    target=next(t for t in targets if t["type"]=="page");cdp=CDP(target["webSocketDebuggerUrl"])
    cdp.call("Page.enable");cdp.call("Runtime.enable")
    cdp.call("Emulation.setDeviceMetricsOverride",{"width":1440,"height":1080,"deviceScaleFactor":1,"mobile":False})
    cdp.call("Page.navigate",{"url":"http://127.0.0.1:19080"})
    time.sleep(.5)
    cdp.wait("document.querySelectorAll('#profile-select option').length===6 && document.querySelector('#session-button') && !document.querySelector('#session-button').disabled")
    cdp.evaluate("document.querySelector('#profile-select').value='A-reviewer';document.querySelector('#profile-select').dispatchEvent(new Event('change'));document.querySelector('#session-button').click()")
    cdp.wait("document.querySelectorAll('.incident-card').length===4 && !document.querySelector('#analyze-button').disabled")
    cdp.evaluate("document.querySelectorAll('.incident-card')[1].click()")
    cdp.wait("document.querySelector('#incident-id').textContent==='INC-A-002' && document.querySelector('#analyze-button') && !document.querySelector('#analyze-button').disabled")
    cdp.evaluate("document.querySelector('input[name=mode][value=baseline]').checked=true;document.querySelector('#analysis-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    cdp.wait("document.querySelector('#analysis-mode-badge').textContent.includes('규칙') && !document.querySelector('#approve-button').disabled")
    baseline=cdp.evaluate("({gate:document.querySelector('#gate-title').textContent,mode:document.querySelector('#analysis-mode-badge').textContent,citations:document.querySelectorAll('.citation-card').length,text:document.body.textContent})")
    cdp.evaluate("document.querySelector('#review-comment').value='합성 브라우저 검증: 원문과 반증을 검토했습니다.';document.querySelector('#approve-button').click()")
    cdp.wait("document.querySelector('#review-existing').textContent.includes('승인')")
    reviewed=cdp.evaluate("({review:document.querySelector('#review-existing').textContent,audit:document.querySelector('#audit-list').textContent})")
    cdp.wait("!document.querySelector('#analyze-button').disabled")
    cdp.evaluate("document.querySelector('input[name=mode][value=model]').checked=true;document.querySelector('#analysis-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    cdp.wait("document.querySelector('#analysis-mode-badge').textContent.includes('실제 모델 추출') && !document.querySelector('#approve-button').disabled")
    cdp.evaluate("document.querySelectorAll('.citation-card')[1].click()")
    cdp.wait("document.querySelectorAll('#document-content mark').length>0")
    model=cdp.evaluate("({mode:document.querySelector('#analysis-mode-badge').textContent,gate:document.querySelector('#gate-title').textContent,incident:document.querySelector('#incident-id').textContent,quote_check:document.querySelector('#citation-check').textContent,highlight_count:document.querySelectorAll('#document-content mark').length,meta:document.querySelector('#analysis-meta').textContent,facts:document.querySelector('#facts-count').textContent})")
    if model["incident"]!="INC-A-002" or "인용·추출 검사 통과" not in model["gate"]:raise RuntimeError("incorrect incident or extraction gate")
    image=cdp.call("Page.captureScreenshot",{"format":"png","captureBeyondViewport":False})
    (ROOT/"artifacts/ui-desktop.png").write_bytes(base64.b64decode(image["data"]))
    cdp.call("Emulation.setDeviceMetricsOverride",{"width":390,"height":844,"deviceScaleFactor":1,"mobile":True})
    cdp.evaluate("window.scrollTo(0,0)")
    image=cdp.call("Page.captureScreenshot",{"format":"png","captureBeyondViewport":False})
    (ROOT/"artifacts/ui-mobile.png").write_bytes(base64.b64decode(image["data"]))
    result={"real_browser":True,"native_sandbox_retained":True,"profile":"A-reviewer","incident_count":4,"baseline":baseline,"reviewed":reviewed,"model":model,"mobile_horizontal_overflow":cdp.evaluate("document.documentElement.scrollWidth>window.innerWidth")}
    (ROOT/"artifacts/browser-smoke.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!="baseline"}));print(json.dumps({k:v for k,v in baseline.items() if k!="text"}))
if __name__=="__main__":main()
