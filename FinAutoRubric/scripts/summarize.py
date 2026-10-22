"""Aggregate run artifacts into runs/summary.md (and print the same table)."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_runs(runs_root):
    rows = []
    for run_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        score_path = run_dir / "score.json"
        trace_path = run_dir / "trace.json"
        if not (score_path.is_file() and trace_path.is_file()):
            continue
        score = json.loads(score_path.read_text(encoding="utf-8-sig"))
        trace = json.loads(trace_path.read_text(encoding="utf-8-sig"))
        cfg_path = run_dir / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig")) if cfg_path.is_file() else {}
        rows.append({"run_id": run_dir.name, "score": score, "trace": trace, "config": cfg})
    return rows


def main():
    runs_root = ROOT / "runs"
    rows = load_runs(runs_root)
    if not rows:
        print("no runs found under", runs_root, file=sys.stderr)
        return 1

    lines = ["# 运行汇总", "", "由 `scripts/summarize.py` 生成；逐次运行的原始记录见各 `runs/<run_id>/`。", ""]
    lines.append(
        "| run_id | 题目 | 协议 | 状态 | 分数 | 通过项 | 截止日合规 | steps | 工具 | 重试 | 错误 | tokens | 耗时(s) |"
    )
    lines.append("|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        score, trace = row["score"], row["trace"]
        passed = sum(1 for item in score["items"] if item["passed"])
        usage = trace["counters"].get("usage") or {}
        tokens = (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
        compliance = (score.get("cutoff_compliance") or {}).get("status", "-")
        protocol = (row["config"].get("protocol") or {}).get("version", "-")
        lines.append(
            "| %s | %s | %s | %s | %d/%d | %d/%d | %s | %d | %d | %d | %d | %d | %.2f |"
            % (
                row["run_id"],
                trace["question_id"],
                protocol,
                trace["status"],
                score["score"],
                score["max_score"],
                passed,
                len(score["items"]),
                compliance,
                trace["counters"]["steps"],
                trace["counters"]["tool_calls"],
                trace["counters"].get("retries", 0),
                trace["counters"]["errors"],
                tokens,
                trace["elapsed_seconds"],
            )
        )
    lines.append("")
    lines.append("## 逐项判定")
    lines.append("")
    for row in rows:
        lines.append("### %s (%s, 协议 %s)" % (
            row["trace"]["question_id"], row["run_id"],
            (row["config"].get("protocol") or {}).get("version", "-")))
        lines.append("")
        lines.append("| 项 | 权重 | 结果 | 要求 |")
        lines.append("|---|---:|---|---|")
        for item in row["score"]["items"]:
            lines.append(
                "| %s | %d | %s | %s |"
                % (item["id"], item["weight"], "pass" if item["passed"] else "FAIL", item["requirement"])
            )
        compliance = row["score"].get("cutoff_compliance") or {}
        if compliance.get("post_cutoff_material"):
            read = ", ".join(compliance.get("read_by_agent") or []) or "none"
            lines.append("")
            lines.append("截止日之后的材料：%s；工具暴露的材料（读取或搜索）：%s。" % (", ".join(compliance["post_cutoff_material"]), read))
        lines.append("")
    text = "\n".join(lines) + "\n"
    (runs_root / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
