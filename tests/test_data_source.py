"""Tests for where the portfolio is loaded from, and how failures behave."""
import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import data_source
from data_source import DataSourceError, fetch_remote_portfolio, load_portfolio

TOKEN = "test-token-value"
TX = [{"ticker": "AAPL", "shares": "1", "price": "100", "date": "2025-01-01"}]


def github_response(body):
    response = MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    return response


def http_error(code):
    return urllib.error.HTTPError("https://api.github.com", code, "error", {}, io.BytesIO())


@pytest.fixture(autouse=True)
def fresh_cache():
    load_portfolio.clear()
    yield
    load_portfolio.clear()


class TestFetchRemotePortfolio:
    def test_returns_transactions(self, mocker):
        urlopen = mocker.patch("urllib.request.urlopen", return_value=github_response(json.dumps(TX).encode()))
        assert fetch_remote_portfolio(TOKEN) == TX
        request = urlopen.call_args.args[0]
        assert request.full_url.endswith("/repos/SutheeraP/port-oreo-data/contents/portfolio.json")
        assert request.get_header("Authorization") == f"Bearer {TOKEN}"

    @pytest.mark.parametrize("code, expected", [
        (401, "rejected"),
        (403, "can't read"),
        (404, "can't read"),
        (500, "500"),
    ])
    def test_http_errors(self, mocker, code, expected):
        mocker.patch("urllib.request.urlopen", side_effect=http_error(code))
        with pytest.raises(DataSourceError, match=expected) as error:
            fetch_remote_portfolio(TOKEN)
        assert TOKEN not in str(error.value)

    @pytest.mark.parametrize("failure", [urllib.error.URLError("down"), TimeoutError()])
    def test_network_errors(self, mocker, failure):
        mocker.patch("urllib.request.urlopen", side_effect=failure)
        with pytest.raises(DataSourceError, match="reach GitHub"):
            fetch_remote_portfolio(TOKEN)

    @pytest.mark.parametrize("body", [b"not json", b"[]", b"{}", b'[{"no": "ticker"}]'])
    def test_rejects_bad_content(self, mocker, body):
        mocker.patch("urllib.request.urlopen", return_value=github_response(body))
        with pytest.raises(DataSourceError):
            fetch_remote_portfolio(TOKEN)

    def test_blank_token(self, mocker):
        urlopen = mocker.patch("urllib.request.urlopen")
        with pytest.raises(DataSourceError, match="empty"):
            fetch_remote_portfolio("  ")
        urlopen.assert_not_called()


class TestLoadPortfolio:
    @pytest.fixture
    def local_files(self, tmp_path, monkeypatch):
        real = tmp_path / "portfolio.json"
        sample = tmp_path / "portfolio.sample.json"
        sample.write_text('[{"ticker": "SAMPLE"}]')
        monkeypatch.setattr(data_source, "PORTFOLIO", real)
        monkeypatch.setattr(data_source, "PORTFOLIO_SAMPLE", sample)
        return real

    def test_token_uses_github(self, mocker, monkeypatch, local_files):
        local_files.write_text('[{"ticker": "LOCAL"}]')
        monkeypatch.setattr(data_source, "_github_token", lambda: TOKEN)
        mocker.patch("urllib.request.urlopen", return_value=github_response(json.dumps(TX).encode()))
        assert load_portfolio() == (TX, "github")

    def test_failed_read_never_falls_back(self, mocker, monkeypatch, local_files):
        local_files.write_text('[{"ticker": "LOCAL"}]')
        monkeypatch.setattr(data_source, "_github_token", lambda: TOKEN)
        mocker.patch("urllib.request.urlopen", side_effect=http_error(401))
        with pytest.raises(DataSourceError):
            load_portfolio()

    def test_no_token_uses_local_file(self, monkeypatch, local_files):
        local_files.write_text('[{"ticker": "LOCAL"}]')
        monkeypatch.setattr(data_source, "_github_token", lambda: None)
        assert load_portfolio() == ([{"ticker": "LOCAL"}], "local")

    def test_no_token_or_file_uses_sample(self, monkeypatch, local_files):
        monkeypatch.setattr(data_source, "_github_token", lambda: None)
        assert load_portfolio() == ([{"ticker": "SAMPLE"}], "sample")


def test_missing_secrets_means_no_token(mocker):
    secrets = mocker.patch.object(data_source.st, "secrets")
    secrets.get.side_effect = FileNotFoundError
    assert data_source._github_token() is None
