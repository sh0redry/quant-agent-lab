"""Check representative payload prefixes and estimate seven-month staging sizes."""
import json
from pathlib import Path
import sys
import urllib.request
from check_resources import probe

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "references" / "huggingface"
MONTHS = ["2019/07", "2019/08", "2019/09", "2019/10", "2019/11", "2019/12", "2020/01"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    records = []
    for name in ["Market-1T-1Hz-2019H2-2020-dense", "Market-1T-1Hz-2019H2-2020-sparse", "Market-1T-1Hz-2019H2-2020-daystore", "tfwm-supervised-spread"]:
        meta = json.loads((HF / (name + ".json")).read_text(encoding="utf-8"))
        is_dataset = name.startswith("Market-")
        base = f"https://huggingface.co/{'datasets/' if is_dataset else ''}fin-ai-lab/{name}/resolve/{meta['sha']}/"
        files = meta["siblings"]
        candidates = [f for f in files if f["rfilename"].endswith((".mds.zstd", "features.npy.zst", "backbone.pt"))]
        selected = min(candidates, key=lambda f: f["size"])
        record = {"repo": name, "file": selected["rfilename"], "file_bytes": selected["size"], "probe": probe(base + selected["rfilename"])}
        if is_dataset:
            record["seven_month_download_bytes"] = sum(f.get("size", 0) for f in files if any('/' + m + '/' in f["rfilename"] for m in MONTHS))
            if name.endswith(("dense", "sparse")):
                raw_bytes = 0
                for file in files:
                    filename = file["rfilename"]
                    if filename.endswith("/index.json") and any('/' + m + '/' in filename for m in MONTHS):
                        with urllib.request.urlopen(base + filename, timeout=45) as response:
                            data = response.read()
                        (HF / (name + "-" + filename.replace("/", "-"))).write_bytes(data)
                        index = json.loads(data)
                        raw_bytes += sum(s["raw_data"]["bytes"] for s in index["shards"])
                record["seven_month_mds_uncompressed_bytes"] = raw_bytes
            else:
                sample = next(f for f in files if f["rfilename"].endswith("meta.json"))
                with urllib.request.urlopen(base + sample["rfilename"], timeout=45) as response:
                    data = response.read()
                (HF / (name + "-sample-meta.json")).write_bytes(data)
                record["sample_meta_file"] = sample["rfilename"]
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    (ROOT / "results" / "payload_checks.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
