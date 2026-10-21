# FinAutoRubric 初步检查与 WSL 环境建议

检查日期：2026-10-22。检查范围：现有 SUMMARY、资源核验、协议、Agent／评分代码、测试及合成夹具。仅运行本地测试和小型诊断；没有调用真实模型、修改 Agent 实现或迁移 WSL。

## 1. 结论

FinAutoRubric 当前是可运行的离线 mock 骨架，尚不是官方方法复现或真实模型基线。原生 Windows 下复跑 `FinAutoRubric/.venv/Scripts/python.exe -m pytest`，结果 **16 passed in 1.31s**。其当前主要阻碍是资源、真实模型适配与协议实现，不是 Windows。

TFWM 的主要运行阻碍则确有 Windows 成分：原生环境缺少 POSIX `fcntl`、Bash／Windows 路径不兼容，以及 Market-1T 锁定 NumPy 1.26.4 时默认整数为 32 位。建议转到 WSL 2 重新验证原始版本，暂不投入完整 Windows 移植。WSL 不能补齐未取得的数据、API 预算、许可或评测设计。

本次只读查询确认已有 `Ubuntu`，WSL VERSION 为 2，查询时处于 Stopped；另有 docker-desktop。默认沙箱内查询曾报 E_ACCESSDENIED，放开该只读查询后成功，因此不能将原访问失败解释为未安装 WSL。

## 2. FinAutoRubric 发现的问题

| 优先级 | 问题与证据 | 建议 |
| --- | --- | --- |
| 高 | `src/eval/runner.py::build_provider` 只接通 mock。`ToolCall` 没有调用 ID，provider 解析时丢弃 ID，loop 的消息历史没有保留 assistant 的结构化工具调用，工具回复也没有关联 ID。当前测试未覆盖真实模型多轮工具协议 | 接入真实模型前补齐消息结构与调用关联，先用伪 HTTP 响应做契约检查，再做小预算真实调用；不能称“真实模型基线不再受工程阻塞” |
| 高 | `configs/protocol.yaml` 和 `docs/protocol.md` 声称夹具不含截止日后信息；fc-02 实际包含 2025-02-20 新闻稿，截止日为 2025-02-04；工具可成功读取该文件 | 明确实验选择：预先过滤可见材料，或故意保留作为时间辨识干扰项。若采用后者，修正文档并增加独立的时间合规评价 |
| 高 | `loop.py` 只在模型调用之前检查 deadline。本地诊断中预算 0.005 秒、provider 延迟约 0.03 秒后提交，最终仍为 submitted（约 0.031 秒） | 模型请求使用剩余预算设置超时，调用后与每次工具执行前后核对时限；耗时计算工具需要单独限制 |
| 中 | 文档约定工具重试上限 1 次，但 `retries` 始终初始化为 0，没有上限执行逻辑。本地同一错误工具连续调用 3 次后仍可提交，errors=3、retries=0 | 定义什么算重试、按调用还是工具／参数计数，并实际执行约束 |
| 中 | `rubric.py::_find_numbers` 对 `1,234.56` 拆词，目标 1234.56±0.01 的数字检查返回 False；`number_within` 也未绑定指标、单位和时期 | 增加金融数字／单位解析及结构化字段检查；关键词和数字出现位置不能替代论证正确性判断 |
| 中 | 目前运行配置保存 question/rubric hash 和协议版本/hash，未保存证据文件清单/hash；没有完整 token／费用记录。`new_run_id` 只精确到秒，同题同 provider 同秒重跑可能覆盖 | 真实基线前固定证据 manifest、模型配置与代码版本，完善用量／费用和唯一 run ID |
| 中 | 资源文档将关键词搜索 0 命中表述成“不可取得”“无仓库则无代码”；GitHub 代码搜索实际为 403 | 改为“本次未定位到可确认的官方入口”。0 命中和受限搜索不能证明所有发布渠道都不存在；继续保留路径 B 是合理的工作假设 |

补充：仅看最终答案与查看 trace 是不同测量方式，不能直接称前者“更严格”。现有 16 项测试验证了部分骨架行为，尚不足以证明协议已落实。裁判既不检查工具使用证据，也不能可靠评估自然语言论证质量；合成 mock 分数仍只能解释为流程检查。

## 3. 推荐环境方案

采用现有 **WSL 2 Ubuntu + Linux 文件系统内工作目录 + uv + 独立虚拟环境**。本轮不需要先引入 Docker 或重装系统。

1. 先整理并提交需要保留的工作区内容，再在 WSL 内建立 Linux 工作副本。当前 FinAutoRubric 的代码和 TFWM 审查资料仍有未提交内容，直接从旧基线重新 clone 会遗漏它们。
2. 工作目录建议 `~/projects/quant-agent-lab`。代码、虚拟环境、uv 缓存、MDS 解压和训练热数据放在 Linux 文件系统；Windows 编辑器可通过 WSL 集成访问。若需要 D 盘容量，可规划 Ubuntu 虚拟磁盘的位置，同时保持项目位于其 Linux 文件系统内部。
3. 使用 Linux 版 uv 和 Python 3.12，分别建立 FinAutoRubric、TFWM、Market-1T 的 `.venv`。Windows 的 `.venv`、uv 二进制、CPU torch overlay 不搬用；Market-1T 的 NumPy 1.26 与 TFWM 的 NumPy 2.4 要隔离。
4. TFWM 和 Market-1T 固定本轮清单中的 commit／子模块，先用上游锁文件复跑测试和独立导入。区分平台问题消失、仍失败的代码问题以及外部模型跳过；不预设 WSL 会全绿。
5. 然后验证 GPU：WSL 内 `nvidia-smi`，再检查 PyTorch CUDA 可用性和小张量运算。使用 Windows 主机 NVIDIA 驱动提供的 WSL 支持；不要在 WSL 内另装 Linux 显示驱动。
6. FinAutoRubric 先修消息协议、cutoff、预算与裁判，再接真实模型；TFWM 在 R0 改善后进入单个公开月份 R2，最后决定是否 R3。

本机约 32 GiB 内存，可先将 WSL 上限设为 16 GB、8–12 个逻辑处理器，按实际负载调整；这是初始建议，不是实测最优参数。12 GB 笔记本 GPU 是否满足某配置，需要先测显存和吞吐，不根据设备名称直接保证完整训练。

审计辅助脚本也需要迁移检查：例如本仓库 `Financial World Modeling/scripts/collect_evidence.py` 的硬件采集使用 Windows API，不能原样作为 Linux 硬件探测工具。优先复用上游标准测试命令，再适配辅助留痕脚本。

## 4. 验收顺序与留痕

- **环境验收：**Linux Python／Bash／文件锁、独立导入、官方测试；与 Windows 结果按问题类型对比。
- **GPU 验收：**驱动可见、CUDA 张量、小规模前向／反向；不将其等同完整配置重训。
- **FinAutoRubric 工程验收：**真实 provider 多轮工具消息、截止日策略、预算约束、数字与单位检查、证据版本和用量记录。
- **实验验收：**固定题目与 rubric、模型与预算后，再报告真实模型基线。

仅保留本检查记录、最终测试摘要、关键失败和必要配置。临时探测、重复 mock 轨迹和下载缓存不逐次提交。现有 FinAutoRubric `.gitignore` 还没有排除重复 `runs/mock-*`，后续可将重复运行放入 `.cache/`，只精选一组代表轨迹作为 fixture 或归档。

## 5. 官方参考

- [Microsoft：WSL 文件位置与性能](https://learn.microsoft.com/en-us/windows/wsl/filesystems)：Linux 命令行工作建议将项目存于 Linux 文件系统。
- [Microsoft：WSL 基本命令](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)。
- [Microsoft：WSL 内存与处理器配置](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)。
- [NVIDIA：CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)：WSL 2 GPU 支持和主机驱动要求。
