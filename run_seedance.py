#!/usr/bin/env python3
r"""Seedance 2.0 runner (BytePlus ModelArk), stdlib only.

  python run_seedance.py prompts/shot1_villain_reveal.txt             # plan + price, no spend
  python run_seedance.py prompts/shot1_villain_reveal.txt --execute   # one paid job
  python run_seedance.py --resume out/<task-id>.json                  # poll/download again, no new spend

Key: ARK_API_KEY in the environment, else "ARK_API_KEY" in
%APPDATA%\agent-sprite-forge\config.json (the same file the Forge skills read).
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

BASE = "https://ark.ap-southeast.bytepluses.com/api/v3"
MODELS = {
    "mini": "dreamina-seedance-2-0-mini-260615",
    "fast": "dreamina-seedance-2-0-fast-260128",
    "std":  "dreamina-seedance-2-0-260128",
    "2.5":  "dreamina-seedance-2-5-260628",
}
# USD per output second, 16:9, list price verified 2026-10-06 (Forge prices.json)
PRICE = {
    "mini": {"480p": 0.04, "720p": 0.08},
    "fast": {"480p": 0.07, "720p": 0.15},
    "std":  {"480p": 0.07, "720p": 0.15, "1080p": 0.37},
    "2.5":  {"480p": 0.103, "720p": 0.231, "1080p": 0.569},
}

def load_key():
    k = os.environ.get("ARK_API_KEY")
    if k:
        return k
    cfg = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~/.config")), "agent-sprite-forge", "config.json")
    try:
        with open(cfg, encoding="utf-8") as f:
            return json.load(f).get("ARK_API_KEY")
    except (OSError, ValueError):
        return None

def call(method, path, key, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, {"error": {"message": str(e)}}

def download(url, dest):
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)

def poll(task_id, key, out_dir, interval, timeout):
    t0 = time.time()
    while True:
        st, res = call("GET", f"/content_generation/tasks/{task_id}", key)
        status = res.get("status")
        print(f"[{int(time.time()-t0):4d}s] {status}", file=sys.stderr)
        if status == "succeeded":
            url = res["content"]["video_url"]
            dest = os.path.join(out_dir, f"{task_id}.mp4")
            download(url, dest)
            with open(os.path.join(out_dir, f"{task_id}.json"), "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
            print(json.dumps({"status": "done", "file": dest, "usage": res.get("usage")}))
            return 0
        if status in ("failed", "expired", "cancelled"):
            print(json.dumps({"status": status, "error": res.get("error")}))
            return 1
        if time.time() - t0 > timeout:
            print(json.dumps({"status": "pending_timeout", "task": task_id,
                              "resume": f"python run_seedance.py --resume {out_dir}/{task_id}.json"}))
            return 2
        time.sleep(interval)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file", nargs="?")
    ap.add_argument("--model", choices=MODELS, default="mini")
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--ratio", default="16:9")
    ap.add_argument("--duration", type=int, default=10)
    ap.add_argument("--audio", action="store_true", help="let Seedance generate the soundtrack/dialogue")
    ap.add_argument("--ref", action="append", default=[], help="reference image URL (Image 1, Image 2 ... in the prompt)")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--resume")
    ap.add_argument("--poll-interval", type=int, default=15)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    key = load_key()
    os.makedirs(a.out_dir, exist_ok=True)

    if a.resume:
        if not key:
            sys.exit("error: no ARK_API_KEY")
        with open(a.resume, encoding="utf-8") as f:
            task_id = json.load(f)["id"]
        sys.exit(poll(task_id, key, a.out_dir, a.poll_interval, a.timeout))

    if not a.prompt_file:
        ap.error("prompt_file required (or --resume)")
    with open(a.prompt_file, encoding="utf-8") as f:
        prompt = f.read().strip()

    content = [{"type": "text", "text": prompt}]
    for u in a.ref:
        content.append({"type": "image_url", "image_url": {"url": u}, "role": "reference_image"})
    body = {"model": MODELS[a.model], "content": content, "resolution": a.resolution,
            "ratio": a.ratio, "duration": a.duration, "generate_audio": a.audio, "watermark": False}
    per_s = PRICE[a.model].get(a.resolution)
    est = round(per_s * a.duration, 3) if per_s else None
    plan = {"model": body["model"], "resolution": a.resolution, "ratio": a.ratio, "duration": a.duration,
            "audio": a.audio, "refs": len(a.ref), "estimateUsd": est, "apiHost": BASE, "keyFound": bool(key)}
    if not a.execute:
        print(json.dumps({"plan": plan, "note": "add --execute to spend"}, ensure_ascii=True))
        return
    if not key:
        sys.exit("error: no ARK_API_KEY (env or %APPDATA%/agent-sprite-forge/config.json)")
    if est is None:
        sys.exit(f"error: {a.model} does not render {a.resolution}")

    st, res = call("POST", "/content_generation/tasks", key, body, timeout=120)
    if st != 200 or "id" not in res:
        print(json.dumps({"status": "failed", "httpStatus": st, "error": res.get("error", res)}))
        sys.exit(1)
    task_id = res["id"]
    with open(os.path.join(a.out_dir, f"{task_id}.json"), "w", encoding="utf-8") as f:
        json.dump({"id": task_id, "request": body, "estimateUsd": est, "submittedAt": time.time()}, f, indent=2)
    print(f"task {task_id} submitted (est ${est})", file=sys.stderr)
    sys.exit(poll(task_id, key, a.out_dir, a.poll_interval, a.timeout))

if __name__ == "__main__":
    main()
