"""Audit public HF metadata and bounded download access without fetching datasets."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "references" / "huggingface"


def get_json(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.load(response)


def probe(url):
    request = urllib.request.Request(url, headers={"Range": "bytes=0-1023"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            prefix = response.read(1024)
            return {"url": url, "status": response.status, "bytes_read": len(prefix),
                    "content_range": response.headers.get("Content-Range"),
                    "content_length": response.headers.get("Content-Length"),
                    "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                    "note": "Bounded prefix access only; full file integrity and model/data use are untested."}
    except Exception as exc:
        return {"url": url, "error": f"{type(exc).__name__}: {exc}"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    model_list = get_json("https://huggingface.co/api/models?author=fin-ai-lab&limit=100")
    (OUT / "models.json").write_text(json.dumps(model_list, indent=2) + "\n", encoding="utf-8")
    datasets = [("datasets", f"fin-ai-lab/Market-1T-1Hz-2019H2-2020-{kind}") for kind in ["dense", "sparse", "daystore"]]
    models = [("models", m["id"]) for m in model_list if m["id"].startswith("fin-ai-lab/tfwm-")]
    for kind, repo in datasets + models:
        try:
            url = f"https://huggingface.co/api/{kind}/{repo}?blobs=true"
            data = get_json(url)
            filename = repo.split("/")[-1] + ".json"
            (OUT / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            files = data.get("siblings", [])
            total = sum(f.get("size", 0) for f in files)
            record = {"repo": repo, "kind": kind, "revision": data.get("sha"),
                      "private": data.get("private"), "gated": data.get("gated"),
                      "file_count": len(files), "total_bytes": total,
                      "license": data.get("cardData", {}).get("license"), "metadata_url": url}
            prefix = "datasets/" if kind == "datasets" else ""
            base = f"https://huggingface.co/{prefix}{repo}/resolve/{data['sha']}/"
            # Probe all three data layouts and one representative encoder's weights.
            if kind == "datasets" or repo.endswith("tfwm-supervised-spread"):
                candidates = [f for f in files if f.get("size", 0) > 10000 and not f["rfilename"].endswith(".md")]
                if kind == "models":
                    candidates = [f for f in candidates if f["rfilename"].endswith((".pt", ".safetensors", ".bin", ".pth"))]
                if candidates:
                    chosen = min(candidates, key=lambda f: f["size"])
                    record["download_probe"] = {"file": chosen["rfilename"], "file_bytes": chosen["size"],
                        **probe(base + urllib.parse.quote(chosen["rfilename"]))}
            # Read the dataset/model card and a single small representative config.
            if kind == "datasets" or repo.endswith("tfwm-supervised-spread"):
                small = [f for f in files if f["rfilename"] == "README.md"]
                if kind == "models":
                    small += [f for f in files if f["rfilename"].endswith("train_meta.json")][:1]
                for file in small:
                    try:
                        with urllib.request.urlopen(base + urllib.parse.quote(file["rfilename"]), timeout=45) as response:
                            content = response.read(2_000_000)
                        (OUT / (repo.split("/")[-1] + "-" + file["rfilename"].replace("/", "-"))).write_bytes(content)
                    except Exception as exc:
                        record.setdefault("card_errors", []).append(str(exc))
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
        except Exception as exc:
            record = {"repo": repo, "error": f"{type(exc).__name__}: {exc}"}
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    summary = {"checked_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
               "scope": "Metadata and bounded access checks; R2 inference/training not executed", "resources": records}
    (ROOT / "results" / "resource_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
