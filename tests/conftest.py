import shutil
from pathlib import Path

import pytest

from codeagent.sandbox import LocalSandbox

TASKS = Path(__file__).resolve().parents[1] / "evals" / "tasks"
TEST_CMD = "python -m pytest -q -rf -p no:cacheprovider"


@pytest.fixture
def csv_repo(tmp_path: Path) -> Path:
    dest = tmp_path / "csv_repo"
    shutil.copytree(TASKS / "csv_comma" / "repo", dest)
    return dest


@pytest.fixture
def sandbox(csv_repo: Path, tmp_path: Path):
    sb = LocalSandbox(csv_repo, root=tmp_path / "sbx")
    yield sb
    sb.close()
