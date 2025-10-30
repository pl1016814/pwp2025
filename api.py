from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from threading import Lock
from pathlib import Path
import json, time, os
import requests

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ROBOT_BASE = os.getenv("ROBOT_BASE", "http://192.168.240.17:8000")  # <— change if needed
ROBOT_SET   = f"{ROBOT_BASE}/control/set"
ROBOT_STAT  = f"{ROBOT_BASE}/control/status"
ROBOT_STOP  = f"{ROBOT_BASE}/control/stop"

STATE_PATH = Path(__file__).with_name("robotState.json")
stateLock = Lock()

class ControlData(BaseModel):
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    command: str | None = None
    speed: float = Field(0.6, ge=0.0, le=1.0)
    duration: float = Field(0.8, ge=0.05, le=5.0)

robotState = {
    "up": False, "down": False, "left": False, "right": False,
    "command": "stop", "command_id": 0, "timestamp": int(time.time()),
    "speed": 0.6, "duration": 0.8,
}

def write_state_to_disk(state: dict):
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(STATE_PATH)

def derive_command(d: ControlData) -> str:
    if d.command:
        return d.command
    if d.up: return "forward"
    if d.down: return "back"
    if d.left: return "left"
    if d.right: return "right"
    return "stop"

@app.get("/")
def root():
    return {"ok": True, "robot_base": ROBOT_BASE}

@app.post("/control/set")
def update_controls(data: ControlData):
    global robotState
    # 1) Update local state for proof/logging
    with stateLock:
        cmd = derive_command(data)
        robotState.update({
            "up": data.up, "down": data.down, "left": data.left, "right": data.right,
            "command": cmd, "speed": float(data.speed), "duration": float(data.duration)
        })
        robotState["command_id"] += 1
        robotState["timestamp"] = int(time.time())
        write_state_to_disk(robotState)

    payload = robotState.copy()
    # the robot doesn’t need command_id/timestamp from the webserver
    payload.pop("command_id", None); payload.pop("timestamp", None)
    forwarded = {"ok": False, "robot_reply": {"error": "not attempted"}}
    try:
        r = requests.post(ROBOT_SET, json=payload, timeout=3)
        forwarded = {"ok": r.ok, "robot_reply": r.json() if r.content else {}}
    except requests.RequestException as e:
        forwarded = {"ok": False, "robot_reply": {"error": str(e)}}

    return {"message": "Updated (local) & forwarded", "state": robotState, "forwarded": forwarded}

@app.get("/control/status")
def status():
    # local
    with stateLock:
        local = robotState.copy()
    # remote
    try:
        rr = requests.get(ROBOT_STAT, timeout=2)
        remote = rr.json()
        ok = True
    except requests.RequestException as e:
        remote = {"error": str(e)}
        ok = False
    return {"local": local, "robot_reachable": ok, "robot": remote}

@app.post("/control/stop")
def stop():
    # local
    with stateLock:
        robotState.update({"command": "stop"})
        robotState["command_id"] += 1
        robotState["timestamp"] = int(time.time())
        write_state_to_disk(robotState)
    # remote
    try:
        rr = requests.post(ROBOT_STOP, timeout=2)
        remote = rr.json()
        ok = True
    except requests.RequestException as e:
        remote = {"error": str(e)}
        ok = False
    return {"state": robotState, "forwarded": {"ok": ok, "robot_reply": remote}}
