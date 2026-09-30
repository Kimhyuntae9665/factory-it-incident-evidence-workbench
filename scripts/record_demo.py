"""Record actual browser interaction; frames are not retouched or replaced."""
import json,base64,subprocess
from pathlib import Path
from scripts import browser_smoke
ROOT=Path(__file__).resolve().parents[1]
FRAMES=ROOT/"artifacts/demo-live-frames"
def main():
 FRAMES.mkdir(parents=True,exist_ok=False)
 metadata=[]
 original=browser_smoke.CDP.receive
 def receive(self):
  while True:
   event=original(self)
   if event.get("method")!="Page.screencastFrame":return event
   data=event["params"]
   name=f"frame-{len(metadata):05d}.jpg"
   (FRAMES/name).write_bytes(base64.b64decode(data["data"]))
   metadata.append({"file":name,"timestamp":data["metadata"]["timestamp"]})
   self.counter+=1
   self.send(json.dumps({"id":self.counter,"method":"Page.screencastFrameAck","params":{"sessionId":data["sessionId"]}}).encode())
 original_call=browser_smoke.CDP.call
 started=set()
 def call(self,method,params=None):
  if id(self) not in started:
   started.add(id(self))
   original_call(self,"Page.enable")
   original_call(self,"Page.startScreencast",{"format":"jpeg","quality":75,"maxWidth":1440,"maxHeight":1080,"everyNthFrame":1})
  return original_call(self,method,params)
 browser_smoke.CDP.receive=receive
 browser_smoke.CDP.call=call
 browser_smoke.main()
 if len(metadata)<3:raise RuntimeError("insufficient real screen frames")
 (FRAMES/"frames.json").write_text(json.dumps(metadata,indent=2))
 lines=[]
 for i,item in enumerate(metadata):
  lines.append("file '"+item["file"]+"'")
  delta=metadata[i+1]["timestamp"]-item["timestamp"] if i+1<len(metadata) else .5
  lines.append("duration "+str(max(.01,min(10,delta))))
 lines.append("file '"+metadata[-1]["file"]+"'")
 (FRAMES/"concat.txt").write_text("\n".join(lines)+"\n")
 target=ROOT/"artifacts/demo-live.mp4"
 subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(FRAMES/"concat.txt"),"-vf","scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2","-vsync","vfr","-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(target)],check=True)
 print(json.dumps({"recording":"actual browser screencast","frames":len(metadata),"duration_s":metadata[-1]["timestamp"]-metadata[0]["timestamp"],"bytes":target.stat().st_size}))
if __name__=="__main__":main()
