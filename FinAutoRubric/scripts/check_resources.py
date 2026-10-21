"""Probe whether official FinAutoRubric artifacts exist yet.

Writes docs/resource_probe.json: one record per candidate surface, with the HTTP
status, the checked-at time and a bounded body prefix. This is a dated snapshot,
not a claim about the future: the paper says "Code and data will be publicly
released soon" (p. 3), so this probe is meant to be re-run before any official run.
"""
import datetime as dt
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "resource_probe.json"

CANDIDATES = [
    ("github_repo_search", "https://api.github.com/search/repositories?q=FinAutoRubric"),
    ("github_code_search", "https://api.github.com/search/code?q=FinAutoRubric"),
    ("hf_datasets_search", "https://huggingface.co/api/datasets?search=FinAutoRubric"),
    ("hf_models_search", "https://huggingface.co/api/models?search=FinAutoRubric"),
    ("hf_datasets_org", "https://huggingface.co/api/datasets?author=fin-ai-lab"),
    ("arxiv_abs", "https://arxiv.org/abs/2609.35744"),
    ("arxiv_pdf_head", "https://arxiv.org/pdf/2609.35744v1"),
]


def probe(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "finautorubric-audit/0.1", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(4000).decode("utf-8", "replace")
            return {"status": response.status, "bytes_read": len(body), "prefix": body[:1500]}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "error": exc.reason, "prefix": exc.read(500).decode("utf-8", "replace")}
    except Exception as exc:  # network policy, DNS, TLS
        return {"status": None, "error": f"{type(exc).__name__}: {exc}"[:300]}


def main():
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    records = []
    for name, url in CANDIDATES:
        result = probe(url)
        result.update({"name": name, "url": url, "checked_at": stamp})
        records.append(result)
        print(f"{name:22s} status={result.get('status')} {str(result.get('error',''))[:80]}")
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
