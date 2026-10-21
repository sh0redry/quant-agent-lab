import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    """Use a repository-local temp directory, including on a fresh checkout."""
    if config.option.basetemp is None:
        temporary_root = ROOT / ".cache"
        temporary_root.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(temporary_root / "pytest-tmp")
