# FinAutoRubric 资源核验记录

- **核验日期：**2026-10-22
- **核验范围：**`plan.md` §4.1 的九类资源
- **依据：**本地论文 PDF（`2609.35744v1.pdf`，35 页，SHA-256 `398aa25c5e8cade5d0f8b0d096a488df1e142b06d681825b276e689dadbaeb9f`，许可 CC BY 4.0）＋线上探测（`scripts/check_resources.py`，原始记录见 `docs/resource_probe.json`）
- **状态口径：**已取得／仅论文描述／待核验／不可获得。探测只读元数据，不下载数据。

## 1. 结论

截至 2026-10-22，**官方题目、逐题 rubric、评分代码、裁判提示词与执行轨迹均不可取得**，只能看到论文中的描述与少量示例。三条独立证据：

1. 论文第 3 页脚注原文：**"Code and data will be publicly released soon."**
2. 论文第 24 页表 10 说明提示词 **"to be released under `prompts/generation/` with the code"**；正文另称原则库将以 `bank/principles.md` 随代码发布。
3. 线上探测（同日）：GitHub 仓库搜索 `FinAutoRubric` 的 `total_count = 0`；Hugging Face datasets/models 搜索均 0 条；`fin-ai-lab` 组织下只有 Market-1T 与 TFWM 资产，与本论文无关。

因此**本仓库不能声称"FinAutoRubric 官方复现"**。判定与后果见 `docs/decision.md`。

## 2. 九类资源逐项状态

| # | 资源 | 状态 | 证据 |
|---|---|---|---|
| 1 | 官方题目与题目 ID（100 条分析员问题） | **不可获得** | 论文 p.3、p.9 称 "We release all 100 queries with their rubrics"，但无发布入口；探测 0 命中 |
| 2 | 逐题评分规则及权重 | **不可获得** | 仅有论文表 1、附表 D（表 15–17）的 3 个示例 rubric，非全量；生成产物未曾公开 |
| 3 | 题目信息截止时间（information cutoff） | **仅论文描述** | 论文 p.4、p.24 说明每条 query 固定一个 cutoff，示例给出 2026-03-01、2025-02-04 等；逐题清单未发布 |
| 4 | 官方评分代码与裁判提示词 | **不可获得** | p.24 表 10 明示 "to be released"；附录 B 描述三裁判集成但无代码 |
| 5 | Agent 运行框架与工具定义 | **仅论文描述** | 写作侧用 Codex harness、评审侧用 Claude Code harness（p.24，附录 B）；二者均为商业产品，工具集未公开 |
| 6 | 模型、推理设置、预算及终止规则 | **仅论文描述** | 求解器为 GPT-5.6 Sol、Claude Opus 5、DeepSeek V4.1-Flash 等（p.9、附录 B）；题目级预算与终止规则只作概述 |
| 7 | 示例答案、执行轨迹与结果 | **部分** | 表 3 给出 6 个求解器的四维分数（p.9）；附表 D 有 3 组 expert/generated rubric 对照；无原始 trace 文件 |
| 8 | 数据与代码使用许可 | **部分** | 论文本身 CC BY 4.0（PDF 元数据）；代码与数据许可因未发布而**未知**，不能推定与论文同许可 |
| 9 | 三个外部基准的题目 | **部分可取得** | BigFinanceBench 50 题公开；Finance Agent Benchmark v2 公开 27 题（vals.ai）；FrontierFinance 取 48 题子集（p.6）。三者 rubric 均为各自作者发布，许可需逐一核对 |

## 3. 路径 B 的替代材料

| 基准 | 论文用量 | 公开性 | 我们可做什么 |
|---|---|---|---|
| BigFinanceBench | 全部 50 题，按已发布 trace 评分 | 题目与部分 trace 公开 | 可做**检索/计算类**评测，但 rubric 需自建 |
| Finance Agent Benchmark v2 | 公开 27 题，专家逐项检查 | 题目公开 | 逐项检查最接近逐题 rubric，适合做裁判对照 |
| FrontierFinance | 48 题（每类取前 8） | 需核对发布状态 | 作为信息截止与单位口径的难点补充 |

注意：论文对这三个基准是**用其专家 rubric 给同一批回答打分**来比较 rubric 来源，不是让 Agent 重新做题。我们要做的是 Agent 端评测，协议需重新定义（见 `docs/protocol.md`）。

## 4. 探测记录摘要

| 探测点 | HTTP | 结果 |
|---|---|---|
| GitHub 仓库搜索 `/search/repositories?q=FinAutoRubric` | 200 | `total_count = 0` |
| GitHub 代码搜索 `/search/code` | 403 | 匿名限流，未能判定；不影响结论（无仓库则无代码） |
| HF datasets `?search=FinAutoRubric` | 200 | 0 条 |
| HF models `?search=FinAutoRubric` | 200 | 0 条 |
| HF `?author=fin-ai-lab`（datasets） | 200 | 仅 Market-1T 三个数据集与 BeanCounter-v2 |
| arXiv `/abs/2609.35744` | 200 | 摘要页可访问，未见代码链接 |
| arXiv `/pdf/2609.35744v1` | 200 | 与本地 PDF 为同一版本 |

## 5. 复检方式与触发条件

```bash
.venv/Scripts/python.exe scripts/check_resources.py   # 重写 docs/resource_probe.json
```

以下任一情况出现时必须重跑并重新判定路径：

- 论文更新到 v2 或新增 comments 链接；
- GitHub/HF 出现官方组织或仓库；
- 导师提供内部访问权限。

在取得**题目＋逐题 rubric＋评分代码**三者之前，一律维持路径 B。
