"""Read-only staff UI smoke check using installed Edge and its DevTools protocol."""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def check():
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from sqlalchemy import text
    from app.config import engine, settings
    async with engine.connect() as conn:
        user = (await conn.execute(text("""SELECT u.user_id,u.username FROM security.users u
            JOIN security.user_roles ur USING(user_id) JOIN security.roles r USING(role_id)
            WHERE r.role_name='super_admin' AND u.status='active' LIMIT 1"""))).first()
        if not user:
            raise RuntimeError("Seed an active super administrator before running this check")
    await engine.dispose()
    token = jwt.encode({"sub":str(user.user_id),"username":user.username,
                        "exp":datetime.now(timezone.utc)+timedelta(minutes=5)},settings.JWT_SECRET,algorithm="HS256")
    edge = Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
    profile = ROOT / ".browser-test"
    profile.mkdir(exist_ok=True)
    hidden = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    server = subprocess.Popen([sys.executable,"-m","uvicorn","main:app","--host","127.0.0.1","--port","8765"],
                              cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=hidden)
    browser = None
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:8765/health",timeout=1).close()
                break
            except OSError:
                await asyncio.sleep(.2)
        browser = subprocess.Popen([str(edge),"--headless=new","--disable-gpu","--no-first-run",
            "--remote-debugging-port=9227",f"--user-data-dir={profile}","about:blank"],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=hidden)
        for _ in range(60):
            try:
                tabs=json.load(urllib.request.urlopen("http://127.0.0.1:9227/json",timeout=1))
                break
            except OSError:
                await asyncio.sleep(.2)
        else:
            raise RuntimeError("Headless Edge did not start")
        tab=next(t for t in tabs if t["type"]=="page")
        async with websockets.connect(tab["webSocketDebuggerUrl"],max_size=10_000_000) as ws:
            sequence=0
            errors=[]
            async def call(method,params=None):
                nonlocal sequence
                sequence+=1
                await ws.send(json.dumps({"id":sequence,"method":method,"params":params or {}}))
                while True:
                    response=json.loads(await ws.recv())
                    if response.get("method")=="Runtime.exceptionThrown":
                        errors.append(response["params"]["exceptionDetails"].get("text"))
                    if response.get("id")==sequence:
                        if "error" in response:
                            raise RuntimeError(response["error"])
                        return response.get("result",{})
            await call("Runtime.enable")
            await call("Page.enable")
            for script in (ROOT / "frontend/js").glob("*.js"):
                compiled = await call("Runtime.compileScript", {"expression":script.read_text(encoding="utf-8"),
                    "sourceURL":script.name,"persistScript":False})
                assert "exceptionDetails" not in compiled, f"JavaScript syntax error: {script.name}"
            print("PASS JavaScript syntax")
            await call("Page.addScriptToEvaluateOnNewDocument",{"source":f"localStorage.setItem('hms_token',{json.dumps(token)});"})
            for path in ["pharmacist","lab","nurse","accounts","radiology","blood-bank"]:
                await call("Page.navigate",{"url":f"http://127.0.0.1:8765/{path}"})
                for _ in range(100):
                    await asyncio.sleep(.1)
                    result=await call("Runtime.evaluate",{"expression":"JSON.stringify({ready:document.getElementById('content')?.getAttribute('aria-busy')==='false',error:document.getElementById('message')?.textContent})","returnByValue":True})
                    state=json.loads(result.get("result",{}).get("value","{}"))
                    if state.get("ready"):
                        break
                assert state.get("ready") and not state.get("error"), f"{path}: workspace failed to load"
                print(f"PASS /{path}")
            assert not errors, errors
            # Verify a key interactive form renders, without submitting patient data.
            await call("Page.navigate",{"url":"http://127.0.0.1:8765/accounts"})
            await asyncio.sleep(1)
            await call("Runtime.evaluate",{"expression":"document.querySelector('[data-action=invoice]').click()"})
            result=await call("Runtime.evaluate",{"expression":"document.getElementById('dialog').open","returnByValue":True})
            assert result["result"]["value"], "Invoice patient search dialog did not open"
            print("PASS invoice dialog")
    finally:
        if browser:
            browser.terminate()
            browser.wait(timeout=10)
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    asyncio.run(check())
