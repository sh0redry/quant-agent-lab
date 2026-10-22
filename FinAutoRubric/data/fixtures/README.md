# 合成夹具（fixture）

这三道题（fc-01..fc-03）里的公司、数字和披露文件**全部是虚构的**，只为验证"读证据 → 计算 → 提交 → 按 rubric 评分"这条链路。

- 它们**不是** FinAutoRubric 的题目，也不来自任何基准；
- 它们的分数**不能**写进任何研究结论；
- 真实开发题在路径 B 下另建，来源与许可逐条记录。

每道题包含：`question.json`（题干与 as_of）、`evidence/`（虚构证据文件）、`rubric.json`（我写的评分表）、`mock_script.json`（离线脚本，用于无模型复现）。

## 截止日干扰项

fc-02 故意包含一份晚于 `as_of` 的新闻稿（`press_release_2025-02-20.md`），用来测试 Agent 是否遵守信息截止时间。该文件登记在 `question.json` 的 `post_cutoff_material` 中，运行结束会在 `score.json` 产出 `cutoff_compliance`。这不是夹具错误，而是设计的一部分。
