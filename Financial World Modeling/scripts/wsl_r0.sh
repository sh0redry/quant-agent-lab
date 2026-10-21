#!/usr/bin/env bash
# Run inside the dedicated QuantLab distro as quantlab. No Windows venv reuse.
set -euo pipefail
action=${1:?action required}
lab_root="$HOME/projects/quant-agent-lab"
tfwm_root="$lab_root/.cache/upstream/tfwm"
market_root="$lab_root/.cache/upstream/market-1t"
uv_bin="$HOME/.local/share/quant-lab-tools/bin/uv"
export PATH="$(dirname "$uv_bin"):$PATH"
export UV_CACHE_DIR="$HOME/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$HOME/.local/share/uv/python"
export UV_NO_PROGRESS=1
export UV_LINK_MODE=hardlink
export WANDB_MODE=offline
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
unset PYTHONPATH

case "$action" in
bootstrap)
    python3 -m venv "$HOME/.local/share/quant-lab-tools"
    "$HOME/.local/share/quant-lab-tools/bin/python" -m pip install --disable-pip-version-check uv==0.13.4
    if [[ ! -d "$lab_root/.git" ]]; then
        git clone --branch main '/mnt/d/project/Financial Agent/quant-agent-lab/.cache/wsl/project.bundle' "$lab_root"
        git -C "$lab_root" remote set-url origin https://github.com/sh0redry/quant-agent-lab.git
    fi
    if ! git -C "$lab_root" rev-parse --verify HEAD >/dev/null 2>&1; then
        git -C "$lab_root" checkout --track origin/main
    fi
    git -C "$lab_root" rev-parse --verify HEAD
    mkdir -p "$lab_root/.cache/wsl"
    "$uv_bin" --version
    ;;
sources)
    mkdir -p "$lab_root/.cache/upstream"
    tfwm="$tfwm_root"
    market="$market_root"
    if [[ ! -d "$tfwm/.git" ]]; then
        git clone --no-checkout https://github.com/fin-ai-lab/tfwm.git "$tfwm"
        git -C "$tfwm" checkout --detach e739329a630c14cdb1ed2834a2461bfbfe17e8b5
        git -C "$tfwm" submodule update --init --recursive
    fi
    if [[ ! -d "$market/.git" ]]; then
        git clone --no-checkout https://github.com/fin-ai-lab/market-1t.git "$market"
        git -C "$market" checkout --detach 38da67c065c12e0373a5d56a52a2685d6eccf660
    fi
    test "$(git -C "$tfwm" rev-parse HEAD)" = e739329a630c14cdb1ed2834a2461bfbfe17e8b5
    test "$(git -C "$market" rev-parse HEAD)" = 38da67c065c12e0373a5d56a52a2685d6eccf660
    test "$(git -C "$tfwm/stable-finance" rev-parse HEAD)" = a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6
    ;;
update-project)
    bundle=${2:-'/mnt/d/project/Financial Agent/quant-agent-lab/.cache/wsl/fixed-project.bundle'}
    git -C "$lab_root" fetch "$bundle" main
    git -C "$lab_root" merge --ff-only FETCH_HEAD
    ;;
sync-fin)
    cd "$lab_root/FinAutoRubric"
    "$uv_bin" sync --locked --python 3.12
    ;;
sync-market)
    cd "$market_root"
    "$uv_bin" sync --locked
    ;;
sync-tfwm)
    cd "$tfwm_root"
    "$uv_bin" sync --locked
    ;;
test-fin)
    cd "$lab_root/FinAutoRubric"
    .venv/bin/python -m pytest -ra --tb=short --junitxml="$lab_root/.cache/wsl/fin-pytest.xml"
    ;;
test-market)
    cd "$market_root"
    .venv/bin/python -m pytest -ra --tb=short --junitxml="$lab_root/.cache/wsl/market-pytest.xml"
    ;;
test-tfwm)
    cd "$tfwm_root"
    .venv/bin/python -m pytest -ra --tb=short --continue-on-collection-errors --junitxml="$lab_root/.cache/wsl/tfwm-pytest.xml"
    ;;
environment)
    cat /etc/os-release
    uname -r
    id
    df -hT "$HOME"
    free -h
    "$uv_bin" --version
    git -C "$lab_root" rev-parse HEAD
    ;;
summary)
    python3 '/mnt/d/project/Financial Agent/quant-agent-lab/Financial World Modeling/scripts/wsl_evidence.py'
    ;;
external-cache)
    cd "$tfwm_root"
    .venv/bin/python - <<'PY'
import json
from huggingface_hub import hf_hub_download
result = {}
for repo in ['NeoQuasar/Kronos-base', 'NeoQuasar/Kronos-Tokenizer-base']:
    try:
        result[repo] = hf_hub_download(repo, 'config.json', local_files_only=True)
    except Exception as exc:
        result[repo] = {'exception': type(exc).__name__, 'message': str(exc)}
print(json.dumps(result, indent=2))
PY
    ;;
imports)
    cd "$tfwm_root"
    .venv/bin/python "$lab_root/Financial World Modeling/scripts/diagnose_platform.py" torch market_jepa.modeling stable_finance.dataset market_jepa.training.streaming_dataset market_jepa.eval.checkpoints
    ;;
gpu)
    cd "$tfwm_root"
    /usr/lib/wsl/lib/nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
    .venv/bin/python - <<'PY'
import json, torch
r = {'torch': torch.__version__, 'cuda_build': torch.version.cuda,
     'cuda_available': torch.cuda.is_available()}
assert r['cuda_available'], 'CUDA unavailable'
r['device'] = torch.cuda.get_device_name(0)
r['capability'] = torch.cuda.get_device_capability(0)
torch.manual_seed(0)
x = torch.randn(256, 256, device='cuda', requires_grad=True)
loss = (x @ x.T).square().mean()
loss.backward()
torch.cuda.synchronize()
assert torch.isfinite(loss) and torch.isfinite(x.grad).all()
r.update(loss=float(loss.detach()), gradient_finite=True,
         allocated_peak_bytes=torch.cuda.max_memory_allocated())
print(json.dumps(r, indent=2))
PY
    ;;
git-state)
    for repo in "$lab_root" "$tfwm_root" "$tfwm_root/stable-finance" "$market_root"; do
        echo "$repo"
        git -C "$repo" rev-parse HEAD
        git -C "$repo" status --short
    done
    ;;
*) echo "Unknown action: $action" >&2; exit 2 ;;
esac
