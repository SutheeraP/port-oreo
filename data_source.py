"""Decide where the app's portfolio comes from.

Order of preference:
  1. Private GitHub repo, when a GITHUB_TOKEN secret is set (the hosted app).
  2. Local portfolio.json (running on your own machine).
  3. portfolio.sample.json, always with a visible warning.

Once a token is configured the app never falls back to local or sample data:
a failed read stops the page, so sample numbers can't pass as the real portfolio.

Hosted setup: add `GITHUB_TOKEN = "..."` to the app's secrets. Use a fine-grained
token limited to the data repo with read-only Contents access.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).parent
PORTFOLIO = _ROOT / "portfolio.json"
PORTFOLIO_SAMPLE = _ROOT / "portfolio.sample.json"

DATA_REPO = "SutheeraP/port-oreo-data"
DATA_PATH = "portfolio.json"
REQUEST_TIMEOUT_SECONDS = 15


class DataSourceError(Exception):
    """The private portfolio could not be read. Messages are safe to display."""


def _github_token():
    """Return the configured token, or None when no secrets are set up."""
    try:
        return st.secrets.get("GITHUB_TOKEN")
    except Exception:  # Streamlit raises when no secrets file exists at all.
        return None


def fetch_remote_portfolio(token: str) -> list:
    """Read the portfolio from the private repo. Raises DataSourceError on failure."""
    if not str(token).strip():
        raise DataSourceError("GITHUB_TOKEN is set but empty.")

    request = urllib.request.Request(
        f"https://api.github.com/repos/{DATA_REPO}/contents/{DATA_PATH}",
        headers={
            "Accept": "application/vnd.github.raw+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "port-oreo",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            message = "GitHub rejected the token. It may be expired or revoked."
        elif e.code in (403, 404):
            message = f"The token can't read {DATA_REPO}. Check its repository access."
        else:
            message = f"GitHub returned an error ({e.code})."
        raise DataSourceError(message) from None
    except (urllib.error.URLError, TimeoutError):
        raise DataSourceError("Couldn't reach GitHub. Try again in a moment.") from None

    try:
        portfolio = json.loads(body)
    except ValueError:
        raise DataSourceError(f"{DATA_PATH} in the data repo isn't valid JSON.") from None

    if not (
        isinstance(portfolio, list)
        and portfolio
        and all(isinstance(tx, dict) and "ticker" in tx for tx in portfolio)
    ):
        raise DataSourceError(f"{DATA_PATH} in the data repo has no transactions.")
    return portfolio


@st.cache_data(ttl=300, show_spinner=False)
def load_portfolio() -> tuple:
    """Return (portfolio, source), where source is 'github', 'local' or 'sample'."""
    token = _github_token()
    if token is not None:
        return fetch_remote_portfolio(token), "github"
    if PORTFOLIO.exists():
        return json.loads(PORTFOLIO.read_text()), "local"
    return json.loads(PORTFOLIO_SAMPLE.read_text()), "sample"


def require_portfolio() -> list:
    """Load the portfolio for a page, stopping the page if it can't be read."""
    try:
        portfolio, source = load_portfolio()
    except DataSourceError as e:
        st.error(f"Couldn't load your portfolio. {e}")
        st.stop()
    if source == "sample":
        st.warning("Showing sample data, not your real portfolio.")
    return portfolio
