"""Run the workout API against a temporary, password-protected, loopback PostgreSQL cluster."""
import asyncio
import json
import math
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def postgres():
    pg_bin = Path(os.environ.get("PG_BIN", r"C:\Program Files\PostgreSQL\18\bin"))
    def binary(name):
        return shutil.which(name) or str(pg_bin / (name + (".exe" if os.name == "nt" else "")))
    with tempfile.TemporaryDirectory(prefix="gym-bench-") as temp:
        directory = Path(temp)
        password = secrets.token_hex(20)
        pwfile = directory / "password"
        pwfile.write_text(password)
        pwfile.chmod(0o600)
        data = str(directory / "data")
        pg_port = port()
        subprocess.run([binary("initdb"), "-D", data, "-A", "scram-sha-256", "-U", "bench",
                        "--pwfile", str(pwfile), "--encoding=UTF8", "--no-locale"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([binary("pg_ctl"), "-D", data, "-l", str(directory/"pg.log"), "-w", "start",
                        "-o", f"-h 127.0.0.1 -p {pg_port}"], check=True, stdout=subprocess.DEVNULL)
        try:
            base = f"postgresql+psycopg://bench:{password}@"
            os.environ.update(DATABASE_URL=base+f"bench-pooler:{pg_port}/postgres?hostaddr=127.0.0.1",
                              DIRECT_DATABASE_URL=base+f"127.0.0.1:{pg_port}/postgres",
                              ENVIRONMENT="development", SESSION_SECRET=secrets.token_hex(32),
                              GROQ_API_KEY="", COOKIE_SECURE="false", PYTHON_DOTENV_DISABLED="1")
            subprocess.run([sys.executable,"-m","alembic","-c",str(BACKEND/"alembic.ini"),"upgrade","head"],check=True)
            yield
        finally:
            subprocess.run([binary("pg_ctl"),"-D",data,"-m","fast","-w","stop"],check=True,stdout=subprocess.DEVNULL)


def stats(values):
    s = sorted(values)
    return {"samples":len(s), "p50_ms":round(s[math.ceil(len(s)*.5)-1],2),
            "p95_ms":round(s[math.ceil(len(s)*.95)-1],2),"max_ms":round(max(s),2)} if s else {}


async def cohort(n, base, ids, tokens, cookie, restart):
    measurements = defaultdict(list)
    headers = [{"Cookie": f"{cookie}={token}"} for token in tokens]
    names = ["Squats","Push-ups","Biceps Curls (Dumbbell)","Shoulder Press","Lunges"]
    wids = [str(uuid4()) for _ in ids]
    async with httpx.AsyncClient(base_url=base,timeout=30,trust_env=False) as client:
        async def request(i, method, path, label, expected=200, **kw):
            start=time.perf_counter()
            r=await client.request(method,path,headers=headers[i],**kw)
            measurements[label].append((time.perf_counter()-start)*1000)
            assert r.status_code==expected,(label,r.status_code,r.text[:180])
            return r.json()
        def route(i): return f"/api/workouts/local/accounts/{ids[i]}"
        def body(i,j,finished=False):
            return dict(exercise=names[i%5],reps=min(30,j//2),target_sets=3,reps_per_set=10,elapsed_seconds=j*30,
                        revision=j+1,finished=finished,good_frames=j*35,warning_frames=j*5,incorrect_frames=j)
        async def exercise(i):
            assert (await request(i,"GET","/api/auth/me","authenticated session"))["id"]==ids[i]
            await request(i,"GET",route(i)+"/drafts","open drafts")
            for j in range(60):
                await asyncio.sleep(.01*(i%5))
                await request(i,"PUT",route(i)+"/"+wids[i],"checkpoint",json=body(i,j))
        await asyncio.gather(*(exercise(i) for i in range(n)))
        await asyncio.to_thread(restart)
        async def complete(i):
            path=route(i)+"/"+wids[i]
            rows=await request(i,"GET",route(i)+"/drafts","recover after restart")
            assert len(rows)==1 and rows[0]["progress"]==body(i,59)
            assert not await request(i,"GET","/api/workouts/history","history before finish")
            final=body(i,60,True)
            await asyncio.gather(*(request(i,"PUT",path,"final and retry",json=final) for _ in range(2)))
            await request(i,"PUT",path,"stale checkpoint",409,json=body(i,2))
            rows=await request(i,"GET","/api/workouts/history","history")
            assert len(rows)==1 and rows[0]["exercise_name"]==names[i%5] and rows[0]["reps"]==30
            assert not await request(i,"GET",route(i)+"/drafts","drafts after save")
        await asyncio.gather(*(complete(i) for i in range(n)))
        await request(1,"PUT",route(0)+"/"+wids[0],"account isolation",403,json=body(0,4,True))
    return {key:stats(values) for key,values in measurements.items()}


def serve():
    import uvicorn
    from api.main import app
    from database.engine import engine
    from sqlalchemy import event
    times = []
    cpu_start = time.process_time()
    peak = 0
    acquire = engine.pool.connect
    def timed_acquire():
        start = time.perf_counter()
        connection = acquire()
        times.append((time.perf_counter()-start)*1000)
        return connection
    engine.pool.connect = timed_acquire
    @event.listens_for(engine, "checkout")
    def checked_out(*_):
        nonlocal peak
        peak = max(peak, engine.pool.checkedout())
    # Only this disposable benchmark process gets the loopback metrics route.
    @app.get("/__benchmark/pool")
    def metrics():
        return {"times":times, "peak":peak, "cpu_seconds":time.process_time()-cpu_start, "pid":os.getpid()}
    server = uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=int(sys.argv[2]),access_log=False,log_level="error"))
    @app.post("/__benchmark/stop")
    def shutdown():
        server.should_exit=True
        return {"stopping":True}
    server.run()


def run():
    from api.config import settings
    from api.services.auth import create_session_token
    from database.session import SessionLocal
    from database.engine import engine
    from models import User
    api_port=port()
    base=f"http://127.0.0.1:{api_port}"
    process=None
    times=[]
    peaks=[]
    cpu=[]
    memory=[]
    def stop():
        nonlocal process
        if process is None: return
        try:
            metrics=httpx.get(base+"/__benchmark/pool",trust_env=False).json()
            times.extend(metrics["times"])
            peaks.append(metrics["peak"])
            cpu.append(metrics["cpu_seconds"])
            if os.name=="nt":
                # PID belongs to the isolated API process launched below.
                rss=subprocess.check_output(["powershell","-NoProfile","-Command",
                    f"(Get-Process -Id {int(metrics['pid'])}).PeakWorkingSet64"],text=True)
                memory.append(round(int(rss.strip())/1024**2,1))
        finally:
            try:
                httpx.post(base+"/__benchmark/stop",trust_env=False,timeout=2)
                process.wait(timeout=10)
            except (httpx.TransportError, subprocess.TimeoutExpired):
                process.terminate()
                process.wait(timeout=10)
            process=None
    def restart():
        nonlocal process
        stop()
        process=subprocess.Popen([sys.executable,__file__,"serve",str(api_port)])
        deadline=time.monotonic()+35
        with httpx.Client(trust_env=False,timeout=.5) as client:
            while time.monotonic()<deadline and process.poll() is None:
                try:
                    if client.get(base+"/api/health").status_code==200: return
                except httpx.TransportError: pass
                time.sleep(.05)
        raise RuntimeError("Local API did not start")
    try:
        for n in (10,30):
            times.clear();peaks.clear();cpu.clear();memory.clear()
            restart()
            with SessionLocal.begin() as db:
                users=[User(username=f"bench_{n}_{i}",email=f"u{n}_{i}@example.invalid") for i in range(n)]
                db.add_all(users);db.flush()
                ids=[u.id for u in users];tokens=[create_session_token(u) for u in users]
            report=asyncio.run(cohort(n,base,ids,tokens,settings.auth_cookie_name,restart))
            stop()
            print(json.dumps({"users":n,"http":report,"pool_acquire_including_ping":stats(times),"peak_connections":max(peaks),"api_cpu_seconds":round(sum(cpu),2),"peak_api_rss_mib":max(memory,default=None)}),flush=True)
    finally:
        stop()
        engine.dispose()


if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="serve": serve()
    else:
        with postgres(): run()
