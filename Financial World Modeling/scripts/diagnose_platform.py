"""Small platform checks to distinguish numeric-width and import failures."""
import importlib
import json
import sys
import traceback
import subprocess


def check_import(name):
    result = {}
    try:
        module = importlib.import_module(name)
        result[name] = "import OK"
        if name == "torch":
            result["torch_version"] = module.__version__
            result["torch_cuda_build"] = module.version.cuda
            result["cpu_tensor_sum"] = module.arange(4).sum().item()
        if name == "market_jepa.modeling":
            import torch
            config = module.TransformerConfig(hidden_size=32, num_hidden_layers=2,
                num_attention_heads=4, intermediate_size=64, patch_size=4, drop_path_rate=0.0)
            model = module.TransformerBackbone(config, n_features=9, d_embedding=16, pool="last").eval()
            with torch.no_grad():
                output = model(torch.randn(2, 9, 64))
            result["synthetic_model_output"] = {"shape": list(output.shape), "finite": bool(torch.isfinite(output).all())}
    except Exception as exc:
        result[name] = f"{type(exc).__name__}: {exc}"
        result[name + "_traceback"] = traceback.format_exc()
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "--import-one":
        result = check_import(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
        return int(any(key.endswith("_traceback") for key in result))
    import numpy as np
    import pandas as pd
    result = {"python": sys.version, "numpy": np.__version__, "pandas": pd.__version__,
              "numpy_default_int_bits": np.dtype(int).itemsize * 8}
    values = pd.Series(["1785740693712443934"], dtype=object)
    for dtype in [int, "int64"]:
        try:
            result[f"pandas_astype_{dtype}"] = values.astype(dtype).tolist()
        except Exception as exc:
            result[f"pandas_astype_{dtype}"] = f"{type(exc).__name__}: {exc}"
    for name in sys.argv[1:]:
        # Failed imports can leave partly initialized packages in sys.modules.
        # Every module must therefore be checked in a fresh process.
        process = subprocess.run([sys.executable, __file__, "--import-one", name],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        result.update(json.loads(process.stdout))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(any(key.endswith("_traceback") for key in result))


if __name__ == "__main__":
    sys.exit(main())
