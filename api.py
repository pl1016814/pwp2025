from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from threading import Lock
from pathlib import Path
import json, time

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATE_PATH = Path(__file__).with_name("robotState.json")

class ControlData(BaseModel):
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    command: str | None = None

stateLock = Lock()
robotState = {
    "up": False,
    "down": False,
    "left": False,
    "right": False,
    "command": "stop",
    "command_id": 0,
    "timestamp": int(time.time()),
}

def write_state_to_disk(state: dict):
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(STATE_PATH)

@app.get("/")
def root():
    return {"ok": True}

@app.post("/control/set")
async def update_controls(data: ControlData):
    global robotState
    with stateLock:
        robotState["up"] = data.up
        robotState["down"] = data.down
        robotState["left"] = data.left
        robotState["right"] = data.right

        if data.command:
            robotState["command"] = data.command
        else:
            robotState["command"] = "move" if any([data.up, data.down, data.left, data.right]) else "stop"

        robotState["command_id"] = int(robotState.get("command_id", 0)) + 1
        robotState["timestamp"] = int(time.time())
        write_state_to_disk(robotState)

    print(f"GUI Updated State: {robotState}")
    return {"message": "Updated", "state": robotState}

@app.get("/control/status")
def status():
    with stateLock:
        return robotState
