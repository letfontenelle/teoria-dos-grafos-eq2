from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

FRONTEND = Path(__file__).parent.parent / "front-end"

app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")