from fastapi.testclient import TestClient
from main import app

c = TestClient(app)
ITEMS = [
    {"id": 1, "name": "HDMI Cable", "description": "Black cable used to connect laptop to monitor"},
    {"id": 2, "name": "Phone Charger", "description": "White USB-C charging cable"},
    {"id": 3, "name": "Extension Box", "description": "Power extension box with multiple sockets"},
]
def run(label, q, items=ITEMS):
    print(label, "->", c.post("/search", json={"query": q, "items": items}).json())

run("exact name", "HDMI Cable")
run("description", "Where is that black cable I use to connect my laptop to the monitor?")
run("contract example", "that black cable for monitor")
run("misspelled", "phone chargr")
run("partial", "extens")
run("different order", "monitor laptop connect cable")
run("no match", "passport")
run("empty query", "")
run("empty items", "hdmi", [])