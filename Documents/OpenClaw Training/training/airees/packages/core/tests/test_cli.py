from click.testing import CliRunner
from airees.cli.main import app


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Airees" in result.output


def test_cli_init(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--path", str(tmp_path / "myproject")])
    assert result.exit_code == 0
    assert (tmp_path / "myproject" / "airees.yaml").exists()
