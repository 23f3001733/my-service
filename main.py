import json
import time
import uuid
from collections import deque

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

EMAIL = "your_email@example.com"   # <-- CHANGE THIS to your real email

START_TIME = time.time()           # remember when we started (for uptime)
LOGS = deque(maxlen=1000)          # notebook that keeps the last 1000 entries

# The "clicker at the door"
REQUESTS = Counter("http_requests_total", "Total HTTP requests")

app = FastAPI()


# ---- Middleware: runs on EVERY request, for every endpoint ----
@app.middleware("http")
async def observe(request: Request, call_next):
    REQUESTS.inc()                          # click the counter
    request_id = str(uuid.uuid4())          # unique ticket number
    response = await call_next(request)     # let the real endpoint run

    entry = {
        "level": "ERROR" if response.status_code >= 500 else "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
    }
    LOGS.append(entry)                      # write in the notebook
    print(json.dumps(entry), flush=True)    # also print JSON to the console
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int = 1):
    n = max(0, min(n, 1000))                # keep it sane
    total = 0
    for i in range(n):                      # "K units of work"
        total += sum(range(1000))
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.time() - START_TIME)}


@app.get("/logs/tail")
def logs_tail(limit: int = 50):
    if limit <= 0:
        return []
    return list(LOGS)[-limit:]