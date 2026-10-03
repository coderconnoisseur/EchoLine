import subprocess
import sys
from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent / "main.py"


def run_main_with_app_returning(behaviour):
    script = f"""
import runpy, sys, types

class EchoLineApp:
    def run(self):
{behaviour}

sys.modules['app'] = types.SimpleNamespace(EchoLineApp=EchoLineApp)
runpy.run_path({str(MAIN)!r}, run_name='__main__')
"""
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)


def test_exit_code_from_app_is_propagated():
    result = run_main_with_app_returning("        return 3")

    assert result.returncode == 3


def test_unexpected_error_exits_with_failure():
    result = run_main_with_app_returning("        raise RuntimeError('boom')")

    assert result.returncode == 1
    assert "boom" in result.stdout
