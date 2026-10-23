import json
import subprocess
import sys
from pathlib import Path

SAMPLE_PATH = Path(__file__).parent / "sample_data" / "sample_837p.edi"


def test_cli_stdin_to_stdout():
    text = SAMPLE_PATH.read_text()
    result = subprocess.run(
        [sys.executable, "-m", "x12_837_to_json.cli"],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["interchanges"][0]["header"]["interchange_control_number"] == "000000905"


def test_cli_file_argument(tmp_path):
    output_file = tmp_path / "out.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "x12_837_to_json.cli",
            str(SAMPLE_PATH),
            "-o",
            str(output_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    data = json.loads(output_file.read_text())
    assert data["interchanges"][0]["functional_groups"][0]["transaction_sets"][0]["header"][
        "transaction_set_id_code"
    ] == "837"


def test_cli_reports_parse_errors():
    result = subprocess.run(
        [sys.executable, "-m", "x12_837_to_json.cli"],
        input="not x12 at all",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "error" in result.stderr.lower()
