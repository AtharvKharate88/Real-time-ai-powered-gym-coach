"""Production-build smoke test in temporary headless Chrome with a simulated camera and API."""
import os
import queue
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

dist = Path(__file__).resolve().parents[1] / "dist"
results = queue.Queue()
script = """<script>
const network=window.fetch.bind(window);
const send=(url,body)=>network(url,{method:'POST',body:JSON.stringify(body)});
const sleep=t=>new Promise(r=>setTimeout(r,t));
async function wait(test){for(let i=0;i<400;i++){let v=test();if(v)return v;await sleep(100)}throw Error('Timeout '+test)}
function button(label){return [...document.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(label)&&!b.disabled)}
async function click(label){
 try{(await wait(()=>button(label))).click();await sleep(30)}
 catch(e){throw Error(label+' step '+sessionStorage.getItem('step')+' current '+document.body.innerText.slice(-850))}
}
let writes=[],offline=false;
window.fetch=async (url,options)=>{
 const path=new URL(url instanceof Request?url.url:url,location.href).pathname;
 if(!path.startsWith('/api/'))return network(url,options);
 if(path==='/api/auth/me')return Response.json({id:7,email:'tester@example.invalid',full_name:'Test',picture_url:null});
 if(path.endsWith('/drafts'))return Response.json([]);
 if(path.startsWith('/api/workouts/local/accounts/7/')){
   if(!options?.body)return Response.json({exists:false});
   const body=JSON.parse(options.body);writes.push(body);
   return offline?new Response('',{status:503}):Response.json({finished:body.finished,revision:body.revision});
 }
 throw Error('Unexpected API route '+path);
};
async function workout(name){
 (await wait(()=>document.querySelector('.showcase-action button:not(:disabled)'))).click();
 (await wait(()=>[...document.querySelectorAll('article')].find(a=>a.querySelector('h2')?.textContent===name))).querySelector('button').click();
 await click('Set up camera'); await click('Continue');
 await click('Start workout');
 await wait(()=>document.querySelector('.local-squat-preview canvas')?.width===640 && document.body.innerText.includes('Step back'));
 await click('Pause');await click('Resume');await click('Finish workout');
 await wait(()=>document.body.innerText.includes('no recorded reps'));
 if(!writes.some(v=>v.finished&&v.exercise===name))throw Error('Wrong exercise on completion');
}
async function benchmark(){
 const before=performance.now();
 await click('Start benchmark');
 await wait(()=>document.body.innerText.includes('Recording measurements'));
 await sleep(6000);await click('Stop');
 let report;
 HTMLAnchorElement.prototype.click=async function(){report=await (await network(this.href)).json()};
 await click('Export benchmark JSON');await wait(()=>report);
 if(report.frames.length<3||report.inferenceP95Ms<=0)throw Error('Missing inference samples');
 const live={frames:report.frames.length,fps:report.processedFps,inferenceP95:report.inferenceP95Ms};
 // Produce a decodable local clip without accessing a real camera or a remote video.
 const canvas=document.createElement('canvas');canvas.width=320;canvas.height=240;
 const ctx=canvas.getContext('2d');const stream=canvas.captureStream(15);const rec=new MediaRecorder(stream);
 const chunks=[];rec.ondataavailable=e=>chunks.push(e.data);const done=new Promise(r=>rec.onstop=r);
 rec.start();for(let i=0;i<30;i++){ctx.fillStyle=i%2?'#222':'#333';ctx.fillRect(0,0,320,240);await sleep(70)}
 rec.stop();await done;stream.getTracks().forEach(t=>t.stop());
 const dt=new DataTransfer();dt.items.add(new File(chunks,'fixture.webm',{type:rec.mimeType}));
 const input=document.querySelector('input[type=file]');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));
 const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
 for(const field of document.querySelectorAll('input[placeholder]')){setter.call(field,'[]');field.dispatchEvent(new Event('input',{bubbles:true}));}
 report=null;await click('Start benchmark');await wait(()=>document.body.innerText.includes('Recording complete'));
 await click('Export benchmark JSON');await wait(()=>report);
 if(report.source!=='recording'||!report.frames.length||report.repAccuracy?.falseReps!==0||report.formAccuracy?.fp!==0)throw Error('Bad replay report');
 return {live,replayFrames:report.frames.length,elapsedMs:Math.round(performance.now()-before)};
}
window.addEventListener('load',async()=>{
 try{
 const names=['Squats','Push-ups','Biceps Curls (Dumbbell)','Shoulder Press','Lunges'];
 const step=Number(sessionStorage.getItem('step')||0);
 if(!location.search && step<names.length){
   await workout(names[step]);sessionStorage.setItem('step',String(step+1));
   location.reload();
 }else if(!location.search && step===5){
   const id=crypto.randomUUID();sessionStorage.setItem('testWorkout',id);
   const progress={exercise:'Squats',reps:2,target_sets:3,reps_per_set:10,good_frames:30,warning_frames:5,incorrect_frames:1,elapsed_seconds:18,revision:4,finished:false};
   localStorage.setItem('gym-workout:7:'+id,JSON.stringify({id,progress}));
   (await wait(()=>document.querySelector('.showcase-action button:not(:disabled)'))).click();await click('View instructions');
   await click('Set up camera');await click('Continue');await click('Recover workout');offline=true;await click('Finish workout');
   await wait(()=>document.body.innerText.includes('save has not been confirmed'));
   if(!JSON.parse(localStorage.getItem('gym-workout:7:'+id)).progress.finished)throw Error('Missing offline final');
   sessionStorage.setItem('step','6');location.reload();
 }else if(!location.search && step===6){
   (await wait(()=>document.querySelector('.showcase-action button:not(:disabled)'))).click();await click('View instructions');
   await click('Set up camera');await click('Continue');await click('Retry save');await click('Retry save');
   await wait(()=>document.body.innerText.includes('Workout saved to history'));
   if(localStorage.getItem('gym-workout:7:'+sessionStorage.getItem('testWorkout'))||writes.at(-1).reps!==2)throw Error('Recovery failed');
   location.search='?benchmark';
 }else{await send('/result',await benchmark())}
 }catch(e){await send('/result',{error:String(e)})}
});
</script>"""

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path.split("?")[0]!="/": return super().do_GET()
        body=(dist/"index.html").read_text(encoding="utf-8").replace("<head>","<head>"+script).encode()
        self.send_response(200);self.send_header("Content-Type","text/html");self.end_headers();self.wfile.write(body)
    def do_POST(self):
        import json
        results.put(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(204);self.end_headers()

if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",0),lambda *args:Handler(*args,directory=dist))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        chrome=os.environ.get("CHROME_BIN") or str(Path(os.environ["ProgramFiles"])/"Google/Chrome/Application/chrome.exe")
        p=subprocess.Popen([chrome,"--headless=new","--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream",
            "--enable-unsafe-swiftshader","--disable-background-networking","--no-first-run","--user-data-dir="+profile,
            f"http://127.0.0.1:{server.server_port}/"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            outcome=results.get(timeout=240)
            print(outcome)
            assert "error" not in outcome
        finally:
            p.terminate();p.wait(timeout=15);server.shutdown()

