import importlib.util
from pathlib import Path


def test_generated_main_exists() -> None:
    path = Path("workshop_dir/main.py")
    assert path.exists(), "Generated output file workshop_dir/main.py does not exist"


def test_generated_main_imports_and_has_main() -> None:
    path = Path("workshop_dir/main.py")
    assert path.exists(), "Generated output file workshop_dir/main.py does not exist"

    spec = importlib.util.spec_from_file_location("generated_main", path)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main"), "Generated module must define a main() function"
