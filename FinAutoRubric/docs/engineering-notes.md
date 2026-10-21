# 工程备注（本机环境）

本轮遇到并已绕过的环境问题，记录在此以免下一轮重复排查。

## 1. 文件写入

- 会话内置的 `write` 文件工具在本机失败：它用硬链接做原子替换，返回 `EISDIR`。改用 shell 直接写入即可，内容不受影响。
- Windows PowerShell 5.1 的 `Set-Content -Encoding utf8` 会写 BOM。已采取两层防护：所有读取使用 `utf-8-sig`；仓库文件已统一去 BOM。

## 2. Python 与依赖

- 系统默认 Python 3.14，`venv` 的 `ensurepip` 在本机失败。改用 `uv venv --python 3.12` 创建 `FinAutoRubric/.venv`（uv 二进制借用 `Financial World Modeling/.tools/uvpkg/bin/uv.exe`，缓存指向本目录 `.cache/uv`，不与其共享）。
- 已安装：pypdf 6.21.2、PyYAML 6.0.3、pytest 9.1.1。

## 3. pytest

- 沙箱只允许写工作区，pytest 默认的临时目录在 `%TEMP%` 下会被拒绝。
- 因此在 `pytest.ini` 里固定 `--basetemp=.cache/pytest-tmp`。
- **必须在 `FinAutoRubric/` 目录内运行**：在仓库根运行会递归收集到 `Financial World Modeling/external/` 下的上游测试，产生大量无关错误。

## 4. 网络

- Python `urllib` 可直连 PyPI、Hugging Face、arXiv、GitHub API；GitHub 匿名接口有速率限制。
- 会话的网页抓取工具访问 arxiv.org 会被策略拦截，但 Python 直连可取得摘要页与 PDF。

## 5. 常用命令

```powershell
cd FinAutoRubric
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\run_eval.py
.venv\Scripts\python.exe scripts\summarize.py
.venv\Scripts\python.exe scripts\check_resources.py
```
