# TFWM 面向 L3 金融世界模型的首轮审查

日期：2026-10-22（北京时间）。范围：**阶段一、阶段二、阶段三 R0**。本次没有进行 R1 结果图表重建、R2 真实公开数据与权重推理、R3 重训，也没有执行 L3 订单簿回放。

**后续 WSL 复核：**已在 D 盘建立独立 QuantLab 环境。Market-1T 为 66 项全部通过；TFWM 原 CUDA 锁定环境为 1151 通过、1 失败、0 错误、50 跳过，关键导入和 GPU 小张量前向／反向通过。主要 Windows 平台阻碍已解除，但 Kronos 外部模型加载路径尚未通过。下文第 6 节保留首次 Windows 基线；最新执行与边界见 [WSL 记录](WSL_SETUP.md) 和 [精简证据](results/wsl_r0.json)。

## 1. 执行摘要

TFWM 值得作为**市场状态表示与评价框架**借鉴。当前公开成果包含行情聚合管线、模型、部分历史数据、部分月份权重和保存的实验结果；不能将其等同于已经完成的 L3 交互式世界模型。

本轮已确认三项直接影响下一步决策的事实：

1. **公开数据覆盖和论文全部实验范围不同。**三个 HF 布局覆盖 2019-07–2020-12；已发布五个评价月份的编码器中，四个评价月具备公开的完整六个月训练窗口。论文 32 月主表尚不具备全部公开重训条件。
2. **论文概述与具体发布实现需要逐项核对。**论文描述 11 个行情字段，模型数据 schema 为 9 列；默认归一化为当前可见窗口的 `per_view`；dense 卡片与代码对 size 填充的描述存在差异。详见 [论文审查](references/paper_review.md)。
3. **本机原生 Windows 环境存在真实兼容问题。**Market-1T 按锁文件安装成功，但官方 66 项测试为 44 通过、22 失败。至少一处纳秒时间戳转换失败已证实与 Windows／NumPy 1.26 的 32 位默认整数有关；不能宣称全部管线通过。

TFWM 的 CPU 变体测试为 **508 通过、45 失败、20 跳过、44 项错误**；其中 37 项错误发生在收集阶段，7 项发生在用例准备阶段。独立进程验证确认关键模型／数据／评分模块受 `fcntl` 导入阻断。**本轮已完成 R0 验证与阻碍定位，R0 整体未通过。**环境偏离和证据见第 6 节及 [运行清单](results/run_manifest.json)。

**我们的建议：**先解决或明确接受运行平台限制，再开展一个公开评价月份的 R2；随后推进真实 L3 单场所数据的身份核验和状态机。L3 样本、授权及连续日期尚未在本仓库提供，当前无法评价其质量。

## 2. 任务目标与本轮完成边界

核心问题：TFWM 的哪些成果可用于我们的 L3 金融世界模型、公开资源可验证到哪里、还缺什么数据和模块。

| 阶段 | 本轮工作 | 交付与边界 |
| --- | --- | --- |
| 阶段一 | 论文正文、数据与评价附录审查，关键表格视觉核对 | [能力边界图、数据覆盖和评价协议](references/paper_review.md)，[主张—证据清单](results/tables/claim-evidence.md) |
| 阶段二 | 固定两个仓库及子模块，审查字段、处理、模型与评分入口；检查 HF 资源 | [版本清单](results/source_manifest.json)、[资源清单](results/resource_manifest.json)、第 5 节模块审查 |
| R0 | 安装依赖、运行官方测试、检查关键模块导入和本地合成路径 | 第 6 节，失败也如实记录；不等于复现论文指标 |
| R1–R3 | 未执行 | 本轮明确止于 R0 |
| 阶段四–六 | 未执行 | 没有 L3 回放、信息损失实测或采购结论 |

统一证据标签为：**论文声明／代码核实／本地实测／我们的建议**。结果状态为：**已实测通过／已实测失败／资源不足未执行／仅文献判断**；超出本轮授权层级的实验另标为“本轮范围外未执行”，不误写成资源不足。

## 3. 论文方法、贡献与能力边界

**论文声明：**Market-1T 将 SIP 最优报价和成交聚合为 1 Hz 数据；在统一骨干、历史训练窗口及评价协议下比较 18 种编码器训练策略。预测评价包括 900 秒后的 return、volatility change、spread change；潜空间评价包括日期、股票、行业组织与统计因子结构。

预测 readout 为 last patch，潜空间 readout 为 mean。重要基线是未训练 Random ViT，不能默认自监督训练有效。论文表 2 中 multihead 的 return/volatility/spread IC 为 0.0311/0.0941/0.2455，Random ViT 为 0.0170/0.0694/0.1692；这些是**论文声明，未在本轮重新计算**。

**代码核实：**输入行情 schema 是 `bid_price, vwap_all, high, low, ask_price, bid_size, ask_size, volume, n`。额外 11 个视图信息值用于归一化统计与窗口几何，并非 11 列原始行情。

能力边界、归一化差异、股票池筛选、时间划分与待核验问题详见 [完整论文审查记录](references/paper_review.md)。15 项可追溯主张见 [证据矩阵](results/tables/claim-evidence.md)。

**我们的建议：**借鉴多目标表示、语义聚合和跨 regime 评价；新增逐订单状态机、队列、场所标识、动作条件动力学及成交反馈。秒级 NBBO 与成交不能逆向恢复订单新增／撤销路径或队列优先级。

## 4. 数据公开范围、资源大小与复现条件

### 4.1 资源身份和可取得性

**本地实测通过：**HF API 返回三个数据布局和 18 个 `tfwm-*` 模型仓库的元数据。本轮固定了 HF revision、文件数、总大小及卡片许可标识。三个行情 payload 的代表文件、一个 supervised-spread 编码器主体及 head 的前 1,024 字节访问均返回 HTTP 206。

这证明代表入口当前可访问；没有验证全部分片的完整下载、校验和、解压或模型可用性。不是 R2。

| 布局 | 公开全部文件大小（十进制 GB） | 2019-07–2020-01 七个月下载量（GB） | 同七个月 MDS 解压体积（GB） | 主要用途 |
| --- | --- | --- | --- | --- |
| dense | 23.532 | 6.104 | 57.231 | 常规时段 ticker-day，SSL 与探针 |
| sparse | 28.839 | 7.393 | 29.698 | 源稀疏秒级记录、重建策略、公开扩展时段 |
| daystore | 27.125 | 7.285 | 本轮未逐日求和 | 同日横截面监督训练 |

大小按固定 revision 的元数据和 14 个月度 MDS 索引计算。三个布局是同源数据的不同组织方式，不能简单加总为三份独立观测。daystore 一个已读取的 2019-07-01 `meta.json` 给出未压缩 features 为 513,021,728 字节；实际每日报价股票数不同，不能直接乘固定日数视作精确总量。

为 2020-01 端到端配置同时暂存三个布局，下载侧约 **20.782 GB**，还需解压数据、目标表、模型、临时分片和缓存空间。若 dense/sparse 全部物化，二者本身约 86.928 GB。实际流式／缓存配置可能降低峰值，需在 R2 中测量。

### 4.2 可复现范围

| 内容 | 当前判断 | 证据与限制 |
| --- | --- | --- |
| R0 官方测试 | 可尝试且本轮已实际执行 | 原生 Windows 兼容问题见第 6 节 |
| R1 保存结果重建 | 代码和结果快照在仓库中 | `plots/core/regen.sh`；`paths.py` 已核实具备仓内压缩快照回退，因此旧 core README 的外部 lab 限制说明已经过时；本轮未运行生成器 |
| R2 公开模型推理／探针 | 有公开入口，尚未验证端到端 | 需要完整分片、权重、目标表、正确 pooling／窗口与运行平台 |
| R3 单配置重训 | 2020-01、2020-08、2020-09、2020-12 的六个月窗口位于公开区间内 | 是具备数据范围条件，不等于已重训成功 |
| 2019-09 checkpoint 重训 | 公开子集不足 | 训练始于 2019-03，早于公开起点 2019-07 |
| 32 月主表完整重训 | 公开资源不足 | 其余 27 个评价月权重未公开，历史完整原始数据取得条件未满足 |

### 4.3 授权与成本前提

**代码核实：**两个仓库代码为 MIT。所检查的数据和模型卡片标为 `license: other`、`license_name: derived-market-data`，不能套用代码 MIT 许可。完整构建需要 Massive 的 flat-file S3 Access Key ID／Secret Access Key，REST API key 不等价。本轮没有读取私人密钥、开通服务、采购或下载 Massive 全量原始行情。

Market-1T README 给出的示例成本是 2026 年单日原始压缩文件约 12 GB、转换 Parquet 约 4.5 GB、1 Hz 快照约 1.7 GB；64 核 Linux 下耗时约 90 秒。这是**上游说明，非本机测量**，也不是逐订单 L3 数据的成本估计。

## 5. 官方代码结构与 L3 复用审查

所有上游源码保留原样，通过固定 commit 恢复，不将第三方源码复制进本仓库。**当前 QuantLab 的实际检出目录位于仓库根目录的 `.cache/upstream/tfwm/` 和 `.cache/upstream/market-1t/`**，均由 Git 忽略；`Financial World Modeling/external/` 是 Windows 首轮审查的旧目录约定，在 Linux 工作副本中可以为空。以下模块路径以 `.cache/upstream/tfwm/` 为基准，Market-1T 单独注明；历史 Windows 日志中的 `external/` 路径保留原样。

| 模块／入口 | 已核实实现 | 对 L3 的处理建议 | 验证边界 |
| --- | --- | --- | --- |
| `market-1t/.../convert.py::ticker_partitions,convert_file` | gzip CSV 到 ticker hash 分区 Parquet，锁定 Polars hash 版本 | 借鉴分片／批处理；新建 MBO parser 和跨场所键 | 官方转换测试包含合成等价检查 |
| `market-1t/.../scheduler.py::run_tasks` | spawn 进程池、预算内存、worker 恢复、线程上限 | 可复用调度思路；Windows 内存／RSS 回退待适配 | 不是 L3 状态恢复 |
| `market-1t/.../snapshot.py::aggregate_quotes,aggregate_trades,merge_snapshot` | NBBO 状态与成交流分别聚合，合并并填充 | 金融聚合规则可借鉴；订单生命周期另建 | 官方等价测试存在失败 |
| `market-1t/.../conditions.py` | CTA/UTP 条件筛选，价格与量资格分开 | 各场所／供应商逐事件规则重写 | 不能把 SIP 成交过滤直接移植到 MBO |
| `stable-finance/.../schema.py::FeatureSchema,MarketSession` | 特征语义、填充、聚合与 session 校验 | 可作为派生状态接口，扩展 schema | 当前 schema 只含 9 个市场特征 |
| `stable-finance/.../grid.py::SessionPreprocessor` | 会话边界、稀疏重建、LRU 缓存 | 只用于派生采样视图；先保留订单事件原件 | size 填充描述差异未实测关闭 |
| `stable-finance/.../transforms.py::aggregate,normalize` | 语义粗化与分组 per-view 归一化 | 需要为深度、队列及事件字段另定义操作 | 不应平均订单 ID 或随意重排事件 |
| `stable-finance/.../mds.py::open_shard`、`daystore.py::DayRecord` | 分片解压和 day-major 数据读取 | 可借鉴存储与 memmap，调整样本组织 | 并非已验证真实发布数据 |
| `stable-finance/.../outcomes.py`、`targets.py::AnchorTargetStats` | 前向标签与横截面变换 | 评价式标签可复用；L3 增加成交／排队等任务 | 必须重检时钟与未来窗口边界 |
| `market_jepa/modeling/backbones/transformer.py` | 1D patch embedding、ViT、信息 token、pooling | 数值状态编码可适配；事件输入需新设计 | CPU 合成测试不验证 pretrained 品质 |
| `market_jepa/schemas.py`、`training/pretrain.py` | Hydra 配置、模式切换、训练入口 | 训练框架可参考；不直接照搬事件增强 | 官方 recipe 与本轮 CPU 变体需区分 |
| `market_jepa/eval/checkpoints.py::load_encoder` | checkpoint 架构恢复与编码适配 | 重用加载框架，检查输入宽度与 pool | 本轮没有完整下载发布权重 |
| `scripts/eval/probe_fit_size.py`、`stable_finance/metrics.py::grouped_rank_ic` | embedding、ridge、按 cell 的排名评价 | 优先借鉴评价口径和基线 | 本轮未计算论文 IC |
| `market_jepa/modeling/event_predictor.py` | 文本事件 embedding 加到预测头 | 可供以后研究文本条件信息 | 不等于逐订单事件生成或市场交互 |
| L3 订单簿／动作条件转移 | 已审查的数据接口和主实验不覆盖 | 新增订单状态机、快照恢复、场所映射、队列与动作评价 | 本轮未实现 |

文件名中的 `...` 表示所属包路径；完整路径和逐文件身份来自固定 commit。证据矩阵列出可检索的实际函数。源码文件的存在仅作为“代码核实”，实际通过情况见 R0。

## 6. R0：环境与官方测试

### 6.1 本机环境

**本地实测：**Windows 11 build 26200；Intel Core Ultra 9 275HX，24 个逻辑处理器；物理内存约 31.42 GiB，测量时可用约 8.86 GiB；D 盘可用约 597.26 GiB。GPU 为 RTX 5070 Ti Laptop，显存 12,227 MiB，驱动 616.92。驱动报告的 CUDA 版本不等于已经验证 PyTorch GPU 训练。

系统默认 Python 是 3.14.3；两个上游环境均选择已安装的 Python 3.12.10。uv 0.13.4 仅安装到项目 `.tools/`。Market-1T 限定 Python `<3.13` 且锁 NumPy 1.26.4；TFWM 要求 NumPy ≥2.4.1，两者使用独立虚拟环境。

硬件 WMI 与 WSL 查询最初受到访问限制；硬件通过只读 Win32 API／注册表／`nvidia-smi` 补足。没有将 WSL 查询失败解释为没有安装 Linux，也没有安装或更改 WSL。

### 6.2 Market-1T 原始锁文件结果

**已实测通过：**`uv sync --locked` 安装 23 个包；`market_1t.cli` 与 `market_1t.snapshot` 可导入。

**已实测失败：**官方完整 `pytest -ra` 收集并执行 66 项，**44 passed、22 failed**，测试阶段约 331.59 秒。失败集中在 snapshot/reference 字节等价比较和两项端到端转换／快照比较；另有字符串整数转换测试发生 `OverflowError`。

**本地实测诊断：**在 NumPy 1.26.4 + Windows 下 `np.dtype(int).itemsize == 4`，pandas 对纳秒时间戳字符串 `1785740693712443934` 使用 `.astype(int)` 抛出 `OverflowError`，显式 `.astype('int64')` 可正确保留。legacy 参考实现多个时间戳／区间路径使用 `.astype(int)`。这证明一个平台差异；其余 schema／数值／行数差异尚未逐项归因。没有修改参考实现、放宽容差或把失败改成跳过。

### 6.3 TFWM 安装、导入与官方测试

**已实测通过：**按原始 `uv.lock` 安装除 torch／torchvision 外的依赖；随后在独立 `.tools/cpu-torch/` 安装 `torch==2.11.0+cpu`、`torchvision==0.26.0+cpu`，通过 `PYTHONPATH` 用于 R0。Python 为 3.12.10，NumPy 2.4.1，pandas 2.3.3，pytest 9.0.2。CPU 张量 `arange(4).sum()` 返回 6。

这是**CPU 依赖变体**，不是完整官方 CUDA 锁定环境的通过证明。原锁文件要求 `torch==2.11.0+cu128`／`torchvision==0.26.0+cu128`；大型 CUDA 下载被主动停止，源锁文件和源码均未改动。没有测试 GPU 张量或训练显存。

**已实测失败：**官方测试目录使用以下参数执行：

```text
python -m pytest -ra --tb=short --continue-on-collection-errors --junitxml=../../results/tfwm-pytest.xml
```

为继续执行未被收集错误阻断的用例，额外使用 `--continue-on-collection-errors`。CPU 线程限制为 4，W&B 离线，HF／Transformers 离线。最终 **508 passed、45 failed、20 skipped、44 errors**，pytest 报告耗时 134.78 秒，包含启动的命令墙钟耗时 147.687 秒。

收集到 580 项用例，另有 37 项收集错误；580 项中有 7 项准备阶段错误。因此 JUnit 总条目为 617，不能把 37 个收集错误占位条目当成已执行测试。

| 问题类别 | 本地证据 | 当前结论 |
| --- | --- | --- |
| POSIX 文件锁导入 | 44 项错误均包含 `No module named 'fcntl'`；45 项失败中 25 项也包含该错误 | `stable_finance.dataset.panel_cache` 顶层导入向模型／训练／评分模块传播；原生 Windows 阻碍已确认 |
| Bash／集群脚本假设 | 部分测试的 Bash `source D:\...` 返回 127；部分预期脚本输出为空 | 当前 Windows 路径和 shell 环境未通过；未将所有剩余失败逐项修复或归因 |
| 跳过用例 | 20 项，包含离线环境未缓存的外部 checkpoint 及可选模型检查 | 没有验证这些外部模型，不能将跳过计为通过 |
| 成功用例 | 508 项官方测试通过，包括多种配置、损失与部分模型路径 | 仅说明对应测试路径通过，不能覆盖失败的干净导入和整个数据管线 |

**独立导入复核：**每个模块在新 Python 进程内导入，排除失败导入遗留的 `sys.modules` 状态。`torch` 及 CPU 张量检查通过；`market_jepa.modeling`、`stable_finance.dataset`、`market_jepa.training.streaming_dataset`、`market_jepa.eval.checkpoints` 均因 `fcntl` 失败。计划中的干净模型合成输入检查因导入阻碍未执行，没有模型输出结果。

**我们的建议：**下一步先在可用 Linux 环境验证原始版本，或独立审查 Windows 文件锁适配补丁；本轮没有添加 `fcntl` 假模块、调整参考实现、隐藏失败或改动上游源码。

### 6.4 失败与环境调整的处理原则

网络初始沙箱代理连接失败、Git cache dubious ownership、Git shell 管道限制属于环境阻碍，已保留归纳记录。只对本次检出的精确仓库／缓存路径设进程级 Git 信任，没有设置全局 `safe.directory=*`。

R0 发现的问题不自动在本轮扩展为完整 Windows 移植。任何额外 CPU 变体测试均标注依赖差异；没有向官方仓库提交修改，没有训练模型。

### 6.5 R0 最终判定

| 对象 | 通过 | 失败 | 错误 | 跳过 | 结论 |
| --- | --- | --- | --- | --- | --- |
| Market-1T，原始锁文件 | 44 | 22 | 0 | 0 | 已执行，未全部通过；参考实现整数宽度差异已发现 |
| TFWM，CPU 依赖变体 | 508 | 45 | 44 | 20 | 已执行，未全部通过；含 37 项收集错误和 7 项准备错误 |

阶段一／二的审查产出已完成；R0 的环境检查、官方测试尝试与阻碍定位已完成，但“当前平台可完整运行代码”的验收标准未满足。三个上游检出在结束时均保持干净且 HEAD 未变。后续 R2／R3 需要先解除或绕过平台阻碍。

## 7. L3 样本、管线与质量

**本轮范围外未执行。**当前仓库仅有两份论文、解读与计划，没有计划中提到的 AAPL/MSFT MBO 两天样本及其他 RA 采购材料。没有实际检查订单 ID、快照、清簿、交易状态、序列跳号或跨场所覆盖。

下一步最低输入是：明确场所和数据集版本的原始小样本、对应事件规范、标的映射、快照／增量与状态记录。先验证单场所重建正确性，再考虑第二场所。

## 8. L3 → L2 → L1 信息损失

**仅文献判断／我们的建议：**秒级最优报价丢失了逐订单 ID、队列、深度及秒内路径；但本轮没有量化事件合并数、最优价不变的订单事件比例、撤单活动或订单寿命。不能据此宣称 L3 特征必然改善预测。

这些应在阶段四数据管线正确后，用同一段真实数据派生多种视图，再完成 T4 图表。两天样本适合正确性与信息损失分析，不足以支持跨 regime 泛化结论。

## 9. 多场所与世界模型的数据需求

**我们的建议：**订单键至少包含场所／instrument／订单 ID；保留供应商时间、交易所时间和序列等原始含义；分别恢复各场所状态后才构造有覆盖说明的合并视图。

单场所 L1 不能称为全市场 NBBO；跨场所时间戳排序也不能自动证明全市场因果顺序。动作条件动力学、隐藏流动性和成交优先级需要独立的数据与评价设计。

## 10. 下一步建议与未解决问题

1. 首先处理平台：建议在明确可用的 Linux 环境重跑未修改的官方锁文件与失败测试，区分 Windows 差异和算法问题；若继续原生 Windows，则维护显式 int64、文件锁等可审查补丁，另行做等价验证。
2. R2 优先一个公开评价月，例如 2020-01；固定 HF revision、取所需月份和一个编码器，实测下载／解压／推理峰值，再决定 R3。R2 不是全 32 月复现。
3. 取得真实 L3 小样本及数据字典；新增事件解析、订单状态机和快照恢复，首先实施 T2/T3。
4. 保留 Random ViT、简单模型和公平预算，待连续日期充分后再比较 L1/L2/L3 衍生特征。
5. 采购规模由后续训练任务和实测存储／吞吐决定。本轮不提出四年全市场的采购结论。

未解决问题包括：论文／代码的 11/9 列、per-view 与训练统计口径、dense size 填充说明、32 月实际清单、原始宇宙元数据、数据／权重许可的细节，以及 GPU 训练可用性。它们详列于 [论文审查第 7 节](references/paper_review.md#7-面向-l3-的待补模块与待核验问题)。

## 11. 附录：版本、命令与留痕

### 11.1 版本锚点

| 对象 | 固定版本 |
| --- | --- |
| 本项目工作前基线 commit | `6cccb23`：论文、FinAutoRubric 解读与 TFWM 计划归档 |
| TFWM | `e739329a630c14cdb1ed2834a2461bfbfe17e8b5` |
| Market-1T | `38da67c065c12e0373a5d56a52a2685d6eccf660` |
| stable-finance 子模块 | `a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6` |
| stable-pretraining Git 依赖 | `e5c81f6cc800ad7cd726894f4d595f7956d06817` |
| 论文 | `arXiv:2610.09048v2`，SHA-256 `3bce2e009c7d89a32685718b980aecc97d036748336f2498c9280195e531cc76` |

### 11.2 保留哪些记录

按用户要求，Git 只保留有决策价值的报告、证据矩阵、精简版本／资源／运行清单及复核脚本。第三方检出、虚拟环境、缓存、HF 大型 metadata、论文提取文本、核对截图、原始 JUnit XML 和逐次重试日志均忽略。

保留入口：

- [source_manifest.json](results/source_manifest.json)：仓库、子模块、论文身份、依赖锁文件 hash 和硬件快照。
- [resource_manifest.json](results/resource_manifest.json)：HF revision、大小、许可标识、代表下载访问与解压估算。
- [run_manifest.json](results/run_manifest.json)：执行命令、cwd、时间、耗时、退出码，官方测试统计及代表性失败。
- [scripts/](scripts/)：命令留痕、来源核对、公开资源检查、平台诊断与摘要生成脚本。

原始日志仅为本地排查缓存；精简清单中的 hash 用于标识当时输出，不代表这些临时文件会随 Git 发布。运行清单可能包含失败重试命令，复核时先看最终状态和诊断结论。

### 11.3 官方来源

- [论文 v2 HTML](https://arxiv.org/html/2610.09048v2)，本地已归档 PDF。
- [固定 TFWM 仓库](https://github.com/fin-ai-lab/tfwm/tree/e739329a630c14cdb1ed2834a2461bfbfe17e8b5)。
- [固定 Market-1T 仓库](https://github.com/fin-ai-lab/market-1t/tree/38da67c065c12e0373a5d56a52a2685d6eccf660)。
- [固定 stable-finance 子模块](https://github.com/galilai-group/stable-finance/tree/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6)。
- [HF dense](https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-dense)、[sparse](https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse)、[daystore](https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-daystore)、[supervised-spread](https://huggingface.co/fin-ai-lab/tfwm-supervised-spread)。各自实际检查的 revision 以资源清单为准。
