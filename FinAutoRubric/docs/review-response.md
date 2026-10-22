# 对 `docs/review.md` 的逐条回应

> 以下保留 v0.1 初轮回应。后续复核发现“全部已修”的表述过强，已在 v0.2 修复四项遗漏并校正文档；最终验证与限制以 [review-followup.md](review-followup.md) 和当前协议为准。

- 回应日期：2026-10-22
- 协议版本：v0 → **v0.1**（`configs/protocol.yaml`、`docs/protocol.md`）
- 测试：**16 → 37 项**，全部通过
- 范围：只改 `FinAutoRubric/`，未触碰 `Financial World Modeling/`

## 1. 处理结果

| # | review 问题 | 结论 | 修复位置 | 验证方式 |
|---|---|---|---|---|
| 1 | `build_provider` 只接 mock；`ToolCall` 无 ID；历史未保留 assistant 的 tool_calls；工具回复无 ID 关联 | **已修** | `src/agent/providers.py`、`src/agent/loop.py`、`src/eval/runner.py` | `tests/test_provider_contract.py`、`tests/test_loop.py::test_history_keeps_structured_tool_calls_and_ids` |
| 2 | 协议称夹具不含截止日后信息，但 fc-02 含 2025-02-20 新闻稿 | **已修（改协议，不改夹具）** | `docs/protocol.md` §3、`configs/protocol.yaml`、`data/fixtures/fc-02/question.json` | 运行输出 `cutoff=violated`；`tests/test_runner.py::test_runner_writes_manifest_usage_and_compliance` |
| 3 | `loop.py` 只在模型调用前检查 deadline | **已修** | `src/agent/loop.py` | `tests/test_loop.py::test_slow_provider_past_deadline_is_a_timeout`、`test_deadline_is_passed_to_the_provider` |
| 4 | `retries` 恒为 0，无上限执行逻辑 | **已修** | `src/agent/loop.py`、`configs/mock_run.yaml` | `test_tool_error_is_recorded_and_shown`、`test_no_retry_budget_means_single_attempt`、`test_retry_recovers_a_transient_tool_failure` |
| 5 | `_find_numbers` 拆坏 `1,234.56`；`number_within` 不绑定指标/单位/期间 | **已修** | `src/eval/rubric.py` | `tests/test_rubric.py` 新增 7 项 |
| 6 | 运行配置缺证据清单/hash、token/费用记录；run ID 只到秒 | **已修** | `src/eval/runner.py`、`src/common.py` | `test_runner_writes_manifest_usage_and_compliance`、`test_run_id_is_unique_within_a_second` |
| 7 | 资源文档把"0 命中"写成"不可获得" | **已修（改措辞）** | `docs/resources.md`、`docs/decision.md` | 复核文本，见下 |

## 2. 各项的具体改动

**① 消息协议。** `ToolCall` 增加 `id`；mock 脚本没给 ID 时自动生成 `call_<turn>_<n>`；loop 写入历史时使用 OpenAI 结构：

```json
{"role": "assistant", "content": "", "tool_calls": [{"id": "...", "type": "function",
  "function": {"name": "read_evidence", "arguments": "{\"path\": \"a.md\"}"}}]}
{"role": "tool", "tool_call_id": "...", "content": "..."}
```

`OpenAICompatibleProvider` 解析响应中的 `id`/`usage`，并把剩余预算作为 `timeout` 传给 `urlopen`（与自身超时取较小者）。**限制：没有 API key，因此只做了假 HTTP 契约测试，未做真实调用。**

**② 截止日。** 选择"保留干扰项、修正文档"：`question.json` 新增 `post_cutoff_material`，运行结束后在 `score.json` 记录 `cutoff_compliance`（Agent 实际读过哪些截止日后文件）。fc-02 因此显示 `violated`，而这正是 R3 要测的行为。协议里删掉了"夹具不含截止日后信息"的错误表述。

**③ 超时。** 三个时点检查：调用前、模型返回后、每次工具调用前。剩余时间传入 provider；provider 超时或 deadline 被越过都记为 `status = timeout`，不再接受该轮提交。

**④ 重试。** 只对工具错误重试，每个工具调用最多 1 次；重试不重复计一次 `tool_calls`，单独计入 `counters.retries`；重试后仍失败才计入 `errors`。trace 里每次调用保存 `attempts` 数组。

**⑤ 数字解析。** 重写为 `iter_numbers()`：支持千分位、括号负数、全角数字；ISO 日期先掩码再解析（保持字符偏移）；`number_within` 新增可选 `near` 关键词窗口。fc-02 的 R2 已用 `near: ["营业收入","营收","revenue"]`，避免"498.0 出现在人数里"也算对。

**⑥ 运行清单。** `config.json` 现在包含证据文件清单（相对路径 + 字节数 + SHA-256）、usage、定价估算（无定价为 `null`）、provider 类型/模型；`new_run_id` 加入微秒与 6 位随机后缀，50 次调用无重复。

**⑦ 措辞。** "不可获得"改为"本次未定位到"，并明确：GitHub 代码搜索 403、arXiv 无代码链接，因此这是检索限制的结论，不是存在性证明。

## 3. 未解决 / 明确保留

| 项 | 状态 | 原因 |
|---|---|---|
| 真实模型调用 | **未做** | 无 API key；只做了假 HTTP 契约测试 |
| 看 trace 与只看答案的对照 | 未做 | 需要真实模型响应；协议已写明两者是不同测量，不再称"更严格" |
| token 费用 | 结构已就绪 | mock 不产生 usage；接真实模型后自动填充 |
| 证据文件清单 | 已做 | 每次运行记录 `evidence[]` |

## 4. 复现

```bash
.venv/Scripts/python.exe -m pytest          # 37 passed
.venv/Scripts/python.exe scripts/run_eval.py
.venv/Scripts/python.exe scripts/summarize.py
```

`runs/` 中保留了 v0 与 v0.1 各一轮（协议列可区分）；同一版本的重复 mock 重跑已删除，因为结果确定可复现。
