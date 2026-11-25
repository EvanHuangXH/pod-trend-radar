"""Fetch the hosted application snapshot. Run from a private backup repository."""
import hashlib
import json
import subprocess
from pathlib import Path
import re


root = Path(__file__).resolve().parents[1] / "data"
root.mkdir(exist_ok=True)
origin = "https://pod-trend-radar-studio.grassyabbey3.chatgpt.site"
def get(path):
    return subprocess.run(["curl","--fail","--silent","--show-error","--max-time","45",origin+path],check=True,capture_output=True).stdout

def save(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)

def export(state):
    for key in ("keywords","images","projects","collection_jobs","reports","data_sources"):
        if not isinstance(state.get(key), list):
            raise ValueError("Incomplete response: " + key)
    state.pop("can_edit", None)
    hashes = {}
    for image in state["images"]:
        path = image["url"]
        if not path.startswith("/api/media/"):
            continue
        if not re.fullmatch(r"/api/media/[a-f0-9]{64}",path):
            raise ValueError("Invalid hosted media identifier")
        digest = path.rsplit("/", 1)[1]
        folder = root / "media"
        folder.mkdir(exist_ok=True)
        target = folder / digest
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            content = get(path)
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError("Media hash mismatch")
            save(target, content)
        hashes["media/"+digest] = digest
    raw=(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2)+"\n").encode()
    hashes["state.json"]=hashlib.sha256(raw).hexdigest()
    save(root/"state.json",raw)
    save(root/"manifest.json",(json.dumps({"format":1,"source":origin,"sha256":hashes},indent=2)+"\n").encode())
    # Public consumer data has a stable allowlist independent of site schema additions.
    terms=[{"term":k["term"], "first_seen":k["first_seen"],"series":[
        {"source":s["source"],"market":s["market"],"period":s["period"],"unit":s["unit"],
         "observations":[{n:p.get(n) for n in ("day","value","url")} for p in s["points"]]}
        for s in k["series"] if s["source"] in ("Google Trends","Folklife Today")]} for k in state["keywords"]]
    research={"schema_version":1,"keywords":[k for k in terms if k["series"]]}
    save(root/"trends-public.json",(json.dumps(research,ensure_ascii=False,indent=2)+"\n").encode())

if __name__=="__main__":
    export(json.loads(get("/api/state")))
