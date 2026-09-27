"""
NetAlertX app.conf String Escaping Tests

Runs the real PHP encode_python_string() (front/php/server/app_conf_encode.php)
through the PHP CLI, embeds its output in app.conf-style Python source the same
way util.php saveSettings() does, and checks that the source compiles without
warnings and parses back to the typed value (with ' mapped to {s-quote}).

License: GNU GPLv3
"""

import json
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

ENCODER_PHP = Path(__file__).resolve().parents[2] / "front" / "php" / "server" / "app_conf_encode.php"
PHP_BIN = shutil.which("php") or shutil.which("php83")

pytestmark = pytest.mark.skipif(PHP_BIN is None, reason="PHP CLI (php or php83) not available")

# Reads {"path": ..., "cases": [...]} from stdin and prints the encoded cases as JSON.
PHP_RUNNER = (
    '$in = json_decode(stream_get_contents(STDIN), true);'
    'require $in["path"];'
    'echo json_encode(array_map("encode_python_string", $in["cases"]));'
)

CASES = {
    "ordinary_text": "hello world",
    "doc_regex": r"192\.0\.2\..*",
    "consecutive_backslashes": r"a\\b",
    "backslashes_only": "\\" * 3,
    "trailing_backslash": "trail" + "\\",
    "existing_s_quote": "x{s-quote}y",
    "literal_single_quote": "it's",
    "regex_with_quote": r"\d+\s*'",
    "backslash_before_quote": r"a\'b",
}


@pytest.fixture(scope="module")
def encoded():
    """Return {case_id: encoded} produced by one PHP CLI run of encode_python_string()."""
    payload = json.dumps({"path": str(ENCODER_PHP), "cases": list(CASES.values())})
    result = subprocess.run(
        [PHP_BIN, "-r", PHP_RUNNER],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return dict(zip(CASES.keys(), json.loads(result.stdout)))


def parse_app_conf(source):
    """Compile source with all warnings as errors and exec it like the backend app.conf readers."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        code = compile(source, "app.conf", "exec")
    conf = {}
    exec(code, {"__builtins__": {}}, conf)
    return conf


def test_warning_check_rejects_unescaped_backslash():
    """The warnings-as-errors compile rejects the unescaped regex source that util.php emitted before escaping."""
    with pytest.raises(SyntaxError):
        parse_app_conf(r"X='192\.0\.2\..*'")


@pytest.mark.parametrize("case_id", CASES.keys())
def test_scalar_string_round_trip(encoded, case_id):
    """A scalar string setting (X='<encoded>') compiles cleanly and parses back to the typed value."""
    typed = CASES[case_id]
    conf = parse_app_conf(f"X='{encoded[case_id]}'\n")
    assert conf["X"] == typed.replace("'", "{s-quote}")


@pytest.mark.parametrize("case_id", CASES.keys())
def test_array_string_round_trip(encoded, case_id):
    """An array setting element (X=['plain','<encoded>']) compiles cleanly and parses back to the typed value."""
    typed = CASES[case_id]
    conf = parse_app_conf(f"X=['plain','{encoded[case_id]}']\n")
    assert conf["X"] == ["plain", typed.replace("'", "{s-quote}")]


def test_doc_regex_exact_source(encoded):
    """The documentation regex is emitted with doubled backslashes and parses back unchanged."""
    source = f"ICMP_IN_REGEX='{encoded['doc_regex']}'"
    assert source == r"ICMP_IN_REGEX='192\\.0\\.2\\..*'"
    assert parse_app_conf(source)["ICMP_IN_REGEX"] == r"192\.0\.2\..*"
