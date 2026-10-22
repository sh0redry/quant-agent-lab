# v0.1 修改复核记录

日期：2026-10-22。范围：对照 `review.md` 检查本次未提交修改；不调用真实 API，不修改被审查实现。

## 验证结果

初次复核 Windows：**37 passed in 7.28s**，但以下四项存在未覆盖问题。后续已按用户要求修复，协议升级至 **v0.2**。回归测试扩展至 **56 项**，Windows 和 QuantLab Linux 均通过；3 道 v0.2 mock 夹具均完成，分数为 70／70／40，fc-02 的信息暴露标记为 `violated`。未调用真实 API。

最终测试记录：Windows **56 passed in 4.83s**；QuantLab Linux **56 passed in 0.15s**。测试机器和临时目录不同，耗时不作为性能比较。

## 原始问题与复现证据（已修复，保留审查记录）

1. **工具执行后与重试前未检查 deadline。** `src/agent/loop.py` 的工具尝试循环不核对截止时间，成功 `submit` 后立即接受答案。离线用例预算 0.005 秒、工具耗时约 0.032 秒，最终仍为 `submitted` 且保留答案。应在每次尝试前后检查 deadline，超时后不重试、不接受提交；如需硬时限，还需限制工具本身的执行。

2. **数字解析与指标关联仍会误判。** `src/eval/rubric.py` 的负向字符检查包含 Unicode `\w`，因此 `营业收入为498.0百万元` 提取不到任何数字，正确答案不通过。另一方面，80 字符 `near` 窗口使 `营业收入为100百万元，员工人数为 498.0 人` 对目标营业收入 498.0 的检查返回通过。应兼顾中文数字边界，并把指标、单位和期间关联的能力边界写清；邻近关键词不能作为已解决语义归属的证明。

3. **截止日检查会漏报实际暴露的材料。** `src/eval/runner.py::cutoff_compliance` 只比较 `read_evidence` 的原始参数与登记路径字符串。实测成功读取 `./press_release_2025-02-20.md` 后仍显示 `clean`；`search_evidence` 返回该文件内容时也不记录。应规范化路径并纳入搜索结果的证据来源，区分信息暴露与最终答案实际使用的判断。

4. **空题集会被 CLI 当作成功。** `scripts/run_eval.py` 先创建输出目录，再用目录是否存在判断有没有命中题目，这个条件不会触发。实测 `python scripts/run_eval.py --only does-not-exist` 无输出、退出码 0，旧版的空结果检查发生退化。应恢复实际题目计数，并明确如何使用已累计但未消费的 `failures`。

## 文档口径

`SUMMARY.md` 已移除“目前只缺 API key”，`review-response.md` 标注为 v0.1 历史回应。正式题目来源、开发集、独立评价集和模型预算仍需确定；当前没有真实模型端到端验证。

## 修复与验证

- `test_tool_past_deadline_cannot_submit_or_retry`：使用可控时钟，覆盖工具成功／失败时跨越 deadline；晚到答案不接受，不继续重试，未完成评分为 0。协作式截止不强杀执行中的工具，这个限制已写入协议。
- `test_metric_number_binding`、`test_chinese_adjacent_thousands_and_fullwidth_dates`、`test_explicit_unit_constraint`：覆盖中文无空格数值、串入员工人数、跨分句、千分位及全角日期。`near` 改为同分句内紧邻标签的保守语法，`unit` 可显式约束单位；不声称解决一般财务语义或期间指代。
- `test_cutoff_normalizes_read_paths`、`test_cutoff_tracks_search_exposure`：规范化路径，纳入搜索结果来源；`read_by_agent` 兼容字段现在包含搜索暴露，另存 `exposure_sources`。暴露与最终答案实际使用分开解释。
- `tests/test_cli.py`：无匹配题目返回 1，运行全部完成返回 0，含 timeout/error 返回 1；低分且正常完成仍返回 0。

复核命令（仓库根目录）：

```powershell
FinAutoRubric/.venv/Scripts/python.exe -m pytest FinAutoRubric/tests -ra
FinAutoRubric/.venv/Scripts/python.exe FinAutoRubric/scripts/run_eval.py
```

WSL 使用 QuantLab 的 Linux `.venv` 测试同一工作区内容的隔离快照，避免提交前覆盖 Linux 主工作副本。临时脚本、快照与重复 mock 原始产物均在 Git 忽略范围内，仅保留此记录、回归测试和汇总；历史 R0 清单中的 16 项测试仍代表当时基线，不改写为本轮结果。
