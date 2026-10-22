# 主张—证据—L3 项目影响

版本锁定见 [source_manifest.json](../source_manifest.json)。当前 QuantLab 源码路径相对于仓库根目录的 `.cache/upstream/tfwm/` 或明确注明的 `.cache/upstream/market-1t/`；旧 `external/` 目录仅对应 Windows 首轮审查。本地运行状态以 [WSL 复核](../../WSL_SETUP.md) 和 [R0 报告](../../report.md) 为准。

| ID | 标签与结论 | 论文依据 | 固定版本代码依据 | 本地实测边界 | 对 L3 的影响 |
| --- | --- | --- | --- | --- | --- |
| C01 | 论文声明：贡献在市场状态表示 | 第 3、10 页 | `market_jepa/modeling/backbones/transformer.py`；`eval/checkpoints.py::load_encoder` | R0 不含真实发布模型评分 | 复用表示框架；动力学另建 |
| C02 | 代码核实：原始输入为 SIP 最优报价和成交 | 第 4、15 页 | `market-1t/src/market_1t/snapshot.py::QUOTE_COLUMNS,TRADE_COLUMNS` | 没有下载 Massive 原始文件 | 不能恢复订单簿队列 |
| C03 | 代码核实：发布训练特征是 9 列 | 第 4、16 页论文列 11 个字段 | `stable-finance/src/stable_finance/dataset/schema.py::MARKET_SCHEMA` | HF 卡片与源码一致；未解码真实分片 | 明确数据层次和特征映射 |
| C04 | 代码核实：信息 token 是额外 11 个视图元数据值 | 第 18 页 | `market_jepa/schemas.py::DatasetConfig`；`modeling/backbones/transformer.py` | 代表 checkpoint 元数据已读取 | 不能与 11 个行情特征混同 |
| C05 | 代码核实：按右端点 SIP 时间聚合 | 附录 A.3 | `market-1t/.../snapshot.py::_interval,aggregate_quotes,aggregate_trades` | 官方合成等价测试属于 R0 | L3 的 int64 时钟、场所序列另行维护 |
| C06 | 代码核实：保留 legacy 浮点数值行为 | 论文未充分展开数值细节 | `market-1t/docs/methodology.md`；`snapshot.py` | 合成等价测试不等于真实日回放 | 历史兼容与无损事件处理分开实现 |
| C07 | 代码核实：稀疏重建按 schema 分配 ffill/zero-fill | 附录 A.5 | `dataset/grid.py::sparse_to_dense_grid,SessionPreprocessor`；`schema.py` | dense 卡片 sizes 描述存在差异，未实测关闭 | 状态和流量分类可借鉴，订单生命周期不能 ffill 替代 |
| C08 | 代码核实：默认归一化按当前可见 view | 第 5、17 页训练统计表述；第 18 页信息 token | `dataset/transforms.py::normalize`；`schemas.py::DatasetConfig.norm_mode` | 代表 train_meta 记录 per_view | 核查窗口可见性及训练／评分一致性 |
| C09 | 论文声明：月度动态股票池使用上月信息 | 第 17 页 | `dataset/write_mds.py::load_metadata_filter` 消费外部预制 membership；`shard_months.py` 负责调度 | 本轮未找到并验证完整股票池阈值生成及原始参考元数据，未重算 universe | 避免前视和幸存者偏差，L3 还需场所映射 |
| C10 | 代码核实：存储、分片与模型部分解耦 | 附录 A.5 | `dataset/mds.py::open_shard`；`daystore.py::DayRecord` | R0 仅合成文件和导入 | 适配新 schema 后可借鉴 |
| C11 | 论文声明：探针与多 regime 评价重要 | 第 5–7、18 页 | `scripts/eval/probe_fit_size.py`；`stable_finance/metrics.py::grouped_rank_ic` | R1/R2 没有执行 | 复用评价框架并保留简单基线 |
| C12 | 代码核实：last/mean 两种 readout 用途不同 | 第 18 页 | `eval/checkpoints.py::load_encoder`；README 的 Score an encoder | 本轮不以读取权重片段声称加载成功 | 适配时显式设置 pooling |
| C13 | 代码核实：公开数据只支持部分训练月 | 数据公开范围另见仓库 | `market_jepa/market1t.py::RELEASED,LAYOUTS`；`examples/supervised_spread.py` | 元数据和代表 payload 的有界访问检查 | 4 个评价月可规划重训，32 月主表不具备完整公开条件 |
| C14 | 代码核实：event predictor 是文本条件预测头 | 非主文 L3 能力 | `modeling/event_predictor.py::EventEmbeddingBranch` | 未运行该扩展实验 | 不将其视为逐订单生成器 |
| C15 | 我们的建议：新增 L3 状态机和动作条件评价 | 从论文能力边界推断 | 当前已审查接口中未发现对应完整 L3 管线 | 阶段四以后未执行 | 保留逐订单数据，先正确性再增量价值实验 |
