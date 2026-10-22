# D 盘 QuantLab 环境与 R0 复核

日期：2026-10-22（北京时间）。本次采用独立发行版，保留现有 Ubuntu 和 Docker。

## 存储与隔离

| 对象 | 位置／状态 |
| --- | --- |
| 新发行版 | `QuantLab`，Ubuntu 24.04.5 LTS，WSL 2，默认用户 `quantlab` |
| Linux 虚拟磁盘 | `D:\WSL\QuantLab\ext4.vhdx` |
| Linux 工作副本 | `/home/quantlab/projects/quant-agent-lab` |
| TFWM 固定源码 | `~/projects/quant-agent-lab/.cache/upstream/tfwm` |
| Market-1T 固定源码 | `~/projects/quant-agent-lab/.cache/upstream/market-1t` |
| Linux uv | `~/.local/share/quant-lab-tools/bin/uv`，0.13.4；已加入 Bash 持久 PATH |
| 包缓存 | `~/.cache/uv`，在上述 D 盘虚拟磁盘内部 |
| Python | Linux CPython 3.12.3；三个项目各自使用 `.venv` |
| 原 Ubuntu | 仍在 C 盘，保持默认发行版，未迁移或注销 |
| docker-desktop | 仍在原位置，未修改 |

项目代码、环境、包缓存均放入 D 盘虚拟磁盘内部的 ext4 文件系统。`/mnt/d` 只用于引导脚本、Git bundle 和证据整理，不用来运行环境中的大量小文件任务。上游检出采用不含空格的 Linux 路径，避免其 Bash 测试未引用路径造成额外失败。Windows 的虚拟环境和 CPU torch overlay 没有搬用。

这不代表系统层面 C 盘完全零占用：现有 Ubuntu、Docker、WSL 系统组件和共享交换文件仍沿用原配置。本轮没有修改全局 `.wslconfig`、默认发行版、共享内存或交换设置。Linux `df` 显示的是虚拟磁盘逻辑容量，不能当作 D 盘物理剩余空间。

## 版本与变更边界

本轮安装命令如下，当前已经完成，无需再次创建发行版：

```powershell
wsl --install Ubuntu-24.04 --name QuantLab --location D:\WSL\QuantLab --no-launch
wsl --manage QuantLab --set-default-user quantlab
```

发行版内以 root 安装了 `ca-certificates git curl python3 python3-venv build-essential rsync`，创建 `quantlab` 用户，再以该用户建立 uv 工具环境和项目工作副本。Git bundle 从 Windows 当前提交传入，远端仍指向原 GitHub 仓库；没有从旧远端克隆而遗漏未推送成果。没有设置 Git 全局通配信任或改装 Linux 显示驱动。

迁移前提交整理成果：`c3ef78e29fc37b401dd72f10d0d6f87d0d88bd96`。

WSL 首次运行发现 FinAutoRubric 的 pytest 配置依赖预先存在的 `.cache` 父目录，7 项通过、9 项准备错误。已以 `9c28a01f5cf43b0398f03dee22fbdc8b03b86a64` 修复：通过 `pytest_configure` 创建项目内临时目录，并尊重用户显式指定的 `--basetemp`。Windows 与 Linux 均复核 16 项通过。

| 上游 | 固定提交 |
| --- | --- |
| TFWM | `e739329a630c14cdb1ed2834a2461bfbfe17e8b5` |
| stable-finance 子模块 | `a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6` |
| Market-1T | `38da67c065c12e0373a5d56a52a2685d6eccf660` |
| stable-pretraining 锁定依赖 | `e5c81f6cc800ad7cd726894f4d595f7956d06817` |

三个环境均按各自原始 `uv.lock` 安装，没有改上游源码或锁文件。TFWM Linux 环境使用锁定的 CUDA 版本，Windows 基线使用 CPU 依赖变体，因此比较同时包含平台和依赖差异，不能将每一项变化都严格归因于操作系统。

## 使用方法

在 PowerShell 进入专用环境：

```powershell
wsl -d QuantLab
```

进入后，按需要运行一个项目；不要跨环境混用依赖：

已为 QuantLab 用户的 `.bashrc` 和登录启动文件配置带标记、可重复执行的 PATH 设置。**重新打开 VS Code 的 WSL 终端后可直接执行 `uv --version` 和 `uv sync`**。已有 Bash 终端执行 `source ~/.bashrc` 即可立即生效。验证脚本仍显式设置 PATH，以支持不读取 Bash 启动文件的非交互调用。

新建发行版时可用以下脚本重建同样设置，脚本仅允许在 QuantLab 普通用户下执行，并从干净的系统 PATH 验证登录与交互 Bash：

```bash
python3 "$HOME/projects/quant-agent-lab/Financial World Modeling/scripts/configure_wsl_shell.py"
```

2026-10-22 已实际执行配置：全新 `bash -lc` 与 `bash -ic` 在初始 PATH 仅为 `/usr/bin:/bin` 时，均找到 `/home/quantlab/.local/share/quant-lab-tools/bin/uv` 并返回 `uv 0.13.4`。上游目录以仓库根目录的 `.cache/upstream/` 为准；原 Windows `Financial World Modeling/external/` 目录在此工作副本中无需有内容。

```bash
cd ~/projects/quant-agent-lab
UV="$HOME/.local/share/quant-lab-tools/bin/uv"
# 非交互脚本可显式设置；已配置的新 Bash 终端无需手动执行。
export PATH="$(dirname "$UV"):$PATH"

# FinAutoRubric
cd ~/projects/quant-agent-lab/FinAutoRubric
"$UV" sync --locked --python 3.12
.venv/bin/python -m pytest -ra

# Market-1T
cd ~/projects/quant-agent-lab/.cache/upstream/market-1t
"$UV" sync --locked
.venv/bin/python -m pytest -ra

# TFWM：离线测试，不自动下载外部模型
cd ~/projects/quant-agent-lab/.cache/upstream/tfwm
"$UV" sync --locked
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 WANDB_MODE=offline \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m pytest -ra --continue-on-collection-errors
```

完整复核使用 [wsl_r0.sh](scripts/wsl_r0.sh)；Windows 侧 [wsl_run.py](scripts/wsl_run.py) 将逐次日志放在忽略的 `.cache/wsl/`。最后运行 `summary`，由 [wsl_evidence.py](scripts/wsl_evidence.py) 从 JUnit XML、环境包版本和 Git 状态提取精简证据，写入 [wsl_r0.json](results/wsl_r0.json)。

首次安装期间发生一次会话中断，遗留零字节 wheel 元数据和包含空引用的 Git 依赖缓存。清理新发行版的生成缓存及两个未完成 `.venv` 后按原锁文件重建；没有删除源码或原发行版的数据。原始重试输出仅保存在本地缓存，不逐次提交。

验证工具也完成两处修正：运行前生成不可变 Bash 脚本副本，避免长任务期间编辑脚本影响收尾；显式将 Linux uv 加入 PATH，使上游子 Bash 能找到它。WSL 的 localhost 代理提示和 Linux 输出编码不同，留痕工具分别处理；本次依赖下载实际成功，没有修改全局代理网络模式。

## 结果与后续边界

| 对象 | Windows 基线 | D 盘 QuantLab 复核 |
| --- | --- | --- |
| FinAutoRubric | 16 通过 | 16 通过 |
| Market-1T | 44 通过、22 失败 | **66 通过，0 失败** |
| TFWM | CPU 变体：508 通过、45 失败、44 错误、20 跳过 | 原 CUDA 锁：**1151 通过、1 失败、0 错误、50 跳过** |
| 关键模块独立导入 | 模型、数据、训练数据和评分模块因 `fcntl` 失败 | 全部通过；模型合成输出 `[2, 16]`，所有值有限 |
| CUDA | 原基线未测 | RTX 5070 Ti Laptop，12227 MiB，驱动 616.92；torch 2.11.0+cu128，CUDA 12.8；前向、反向和梯度有限值检查通过 |

TFWM 在 Linux 收集了 1202 项用例，Windows 只收集 580 项，另有 37 项模块收集错误；更多模块可导入后才能收集其内部用例，不能将两个通过数简单视作一一对应的增量。Linux TFWM 最终 pytest 耗时 128.16 秒，Market-1T 最终 40.89 秒。三个上游检出及子模块均保持干净，提交未变。

TFWM 首次完整 Linux 测试为 1145 通过、7 失败、50 跳过。其中 6 项是子 Bash 找不到 `uv`，通过设置 PATH 解决，最终仍有 1 项失败：

`tests/test_tsfm_info_grid_width.py::test_info_grid_gives_the_same_features_as_a_bare_panel[kronos]`

它调用 `Kronos.from_pretrained` 后出现构造函数缺少 11 个参数的错误。本地只读缓存检查确认 Kronos 模型及 tokenizer 的 `config.json` 均缺失，返回 `LocalEntryNotFoundError`。本轮采用离线策略，因此该路径未完成验证；不能据此断言联网补齐配置／权重后必然通过，也不能直接归类为纯模型算法错误。没有通过改测试、伪造权重或忽略失败来取得全绿。

50 项跳过中，32 项依赖本地未提供的 2023 mosaic 数据，15 项依赖未缓存的 TimesFM／Sundial／Chronos 外部模型，3 项为同样的 Kronos 加载错误。这些均不计入通过。**原生 Windows 的主要平台阻碍已解除，但 R0 全套测试仍未全部通过。**

磁盘观察时 `ext4.vhdx` 文件约 11.8 GiB，D 盘剩余约 537.4 GiB；这是包含环境和缓存的时点值，不是未来训练空间上限。CUDA 检查仅使用 256×256 张量，不能据此承诺完整配置的训练显存或吞吐。

本次仅复跑 R0，再做 CUDA 小张量前向／反向检查；没有开展真实数据推理、完整训练或 L3 回放。FinAutoRubric 的真实 provider 消息协议、cutoff、预算和数字解析等问题仍见 [工程审查](../FinAutoRubric/docs/review.md)，不会因环境迁移自动解决。下一步若推进 TFWM，应先补齐计划使用的外部模型或数据，再进入一个公开评价月份的 R2；FinAutoRubric 则先完成协议与预算修正。
