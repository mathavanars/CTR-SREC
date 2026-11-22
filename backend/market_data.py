"""Fetch, validate and cache public market figures for educational examples."""

import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


LOGGER = logging.getLogger(__name__)
DEFAULTS_PATH = Path(__file__).parent / "data" / "market_defaults.json"
CACHE_HOURS = 24
FETCH_TIMEOUT_SECONDS = 1.0
MAX_SOURCE_BYTES = 1_000_000
SOURCE_URLS = {
    "repo_rate": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
    "cpi_inflation": "https://www.mospi.gov.in/press-release",
    "sbi_1y_fd_rate": "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits",
    "ppf_rate": "https://www.nsiindia.gov.in/InternalPage.aspx?Id_Pk=132",
    "government_10y_yield": "https://www.rbi.org.in/Scripts/Statistics.aspx",
    "nifty_pe": "https://www.niftyindices.com/Index_Dashboard/Index_Dashboard_NIFTY_50",
    "nifty_pe_10y_average": "https://www.niftyindices.com/reports/historical-data",
    "gold_1y_change": "https://ibjarates.com/",
}
BOOTSTRAP_VALUES = {
    "repo_rate": "6.50",
    "cpi_inflation": "5.22",
    "sbi_1y_fd_rate": "6.80",
    "ppf_rate": "7.10",
    "government_10y_yield": "6.80",
    "nifty_pe": "22.00",
    "nifty_pe_10y_average": "22.00",
    "gold_1y_change": "10.00",
}
VALUE_RANGES = {
    "repo_rate": (0, 20),
    "cpi_inflation": (0, 20),
    "sbi_1y_fd_rate": (0, 20),
    "ppf_rate": (0, 20),
    "government_10y_yield": (0, 20),
    "nifty_pe": (1, 100),
    "nifty_pe_10y_average": (1, 100),
    "gold_1y_change": (-100, 200),
}
SOURCE_GROUPS = {
    "rbi_policy": ("repo_rate",),
    "mospi_cpi": ("cpi_inflation",),
    "sbi_deposits": ("sbi_1y_fd_rate",),
    "small_savings": ("ppf_rate",),
    "rbi_yield": ("government_10y_yield",),
    "nifty_current": ("nifty_pe",),
    "nifty_history": ("nifty_pe_10y_average",),
    "ibja_gold": ("gold_1y_change",),
}
GROUP_URLS = {
    "rbi_policy": SOURCE_URLS["repo_rate"],
    "mospi_cpi": SOURCE_URLS["cpi_inflation"],
    "sbi_deposits": SOURCE_URLS["sbi_1y_fd_rate"],
    "small_savings": SOURCE_URLS["ppf_rate"],
    "rbi_yield": SOURCE_URLS["government_10y_yield"],
    "nifty_current": SOURCE_URLS["nifty_pe"],
    "nifty_history": SOURCE_URLS["nifty_pe_10y_average"],
    "ibja_gold": SOURCE_URLS["gold_1y_change"],
}
_cached_snapshot: dict[str, Any] | None = None
_cache_time: datetime | None = None


def _utc_now() -> datetime:
    """Return one timezone-aware UTC time for cache and date stamps."""
    return datetime.now(timezone.utc)


def _read_saved_snapshot() -> dict[str, Any]:
    """Read the last saved snapshot and fall back to the checked-in defaults."""
    try:
        with DEFAULTS_PATH.open(encoding="utf-8") as snapshot_file:
            snapshot = json.load(snapshot_file)
        if isinstance(snapshot, dict) and isinstance(snapshot.get("metrics"), dict):
            return snapshot
        raise ValueError("The market snapshot does not contain metrics.")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        LOGGER.error("Could not read the saved market snapshot: %s", error)
        return {"metrics": {}}


def _save_snapshot(snapshot: dict[str, Any]) -> None:
    """Save successful source values so later outages can use them."""
    try:
        DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEFAULTS_PATH.open("w", encoding="utf-8") as snapshot_file:
            json.dump(snapshot, snapshot_file, indent=2)
            snapshot_file.write("\n")
    except OSError as error:
        LOGGER.warning("Could not save refreshed market data: %s", error)


def _fetch_source(url: str) -> str:
    """Read a small public page with a short timeout and a clear user agent."""
    request = Request(
        url,
        headers={"User-Agent": "ArthMitra educational planner/1.0"},
    )
    with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        return response.read(MAX_SOURCE_BYTES).decode("utf-8", errors="replace")


def _plain_text(page: str) -> str:
    """Remove page markup so simple source labels can be matched safely."""
    without_scripts = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", page, flags=re.I | re.S)
    return unescape(re.sub(r"<[^>]+>", " ", without_scripts))


def _sbi_one_year_rate(page: str) -> float | None:
    """Read the revised public rate from SBI's one-year deposit table row."""
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, flags=re.I | re.S):
        cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)
        if not cells:
            continue
        label = re.sub(r"\s+", " ", _plain_text(cells[0])).strip().lower()
        if "non-callable" in label or not re.search(r"\b1\s*year\b", label):
            continue
        rates = [
            float(match.group(1))
            for cell in cells[1:]
            for match in re.finditer(r"([0-9]{1,2}(?:\.[0-9]+)?)\s*%", _plain_text(cell))
        ]
        if rates:
            return rates[1] if len(rates) > 1 else rates[0]
    return None


def _first_number(patterns: list[str], text: str) -> float | None:
    """Find the first number that follows one of the source's named labels."""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            return float(match.group(1).replace(",", ""))
    return None


def _parse_source(group: str, page: str) -> dict[str, float]:
    """Read only the requested labelled figure from a public source page."""
    text = _plain_text(page)
    if group == "sbi_deposits":
        sbi_rate = _sbi_one_year_rate(page)
        return {"sbi_1y_fd_rate": sbi_rate} if sbi_rate is not None else {}
    patterns = {
        "rbi_policy": [
            r"(?:policy\s+)?repo\s+rate[^0-9]{0,80}([0-9]+(?:\.[0-9]+)?)\s*%",
        ],
        "mospi_cpi": [
            r"(?:CPI|consumer price index)[^0-9]{0,100}(?:inflation|combined)?[^0-9]{0,50}([0-9]+(?:\.[0-9]+)?)\s*%",
            r"inflation[^0-9]{0,60}([0-9]+(?:\.[0-9]+)?)\s*%",
        ],
        "small_savings": [
            r"(?:Public\s+Provident\s+Fund|PPF)[^0-9]{0,100}([0-9]+(?:\.[0-9]+)?)\s*%",
        ],
        "rbi_yield": [
            r"(?:10|ten)[-\s]?year(?:\s+government|\s+G-?Sec)?[^0-9]{0,100}([0-9]+(?:\.[0-9]+)?)\s*%",
        ],
        "nifty_current": [
            r"(?:NIFTY\s*50.{0,50}?)?(?:P\s*/\s*E|PE\s+ratio)[^0-9]{0,50}([0-9]+(?:\.[0-9]+)?)",
        ],
        "nifty_history": [
            r"(?:10[-\s]?year|10\s+years?)[^0-9]{0,80}(?:average|mean)[^0-9]{0,50}([0-9]+(?:\.[0-9]+)?)",
        ],
        "ibja_gold": [
            r"(?:1[-\s]?year|12[-\s]?month).{0,80}?(?:change|return|growth)[^0-9+-]{0,30}([+-]?[0-9]+(?:\.[0-9]+)?)\s*%",
            r"(?:change|return|growth).{0,80}?(?:1[-\s]?year|12[-\s]?month)[^0-9+-]{0,30}([+-]?[0-9]+(?:\.[0-9]+)?)\s*%",
        ],
    }
    key = SOURCE_GROUPS[group][0]
    value = _first_number(patterns[group], text)
    return {key: value} if value is not None else {}


def _valid_value(name: str, value: object) -> bool:
    """Reject missing, non-finite or out-of-range market figures."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    low, high = VALUE_RANGES[name]
    return number == number and low <= number <= high


def _valid_metric_entry(name: str, entry: object) -> bool:
    """Check that a saved metric has a believable value and its source details."""
    return (
        isinstance(entry, dict)
        and _valid_value(name, entry.get("value"))
        and isinstance(entry.get("source_url"), str)
        and bool(entry.get("source_url"))
        and isinstance(entry.get("fetched_at"), str)
    )


def _bootstrap_metric(name: str) -> dict[str, str]:
    """Keep a dated example value available if both live and saved data fail."""
    entry = {
        "value": BOOTSTRAP_VALUES[name],
        "source_url": SOURCE_URLS[name],
        "fetched_at": "2025-01-01",
    }
    if name == "repo_rate":
        entry["direction"] = "steady"
    return entry


def _date_only(value: object) -> str:
    """Show a short date even when a source saved a full timestamp."""
    text = str(value or "unknown")
    return text[:10] if len(text) >= 10 else "unknown"


def _refresh_snapshot() -> dict[str, Any]:
    """Fetch each public figure, validate it and keep saved values after failures."""
    saved = _read_saved_snapshot()
    old_metrics = saved.get("metrics", {})
    now = _utc_now()
    checked_at = now.isoformat(timespec="seconds")
    metrics: dict[str, Any] = {}
    stale_names: list[str] = []
    for group, names in SOURCE_GROUPS.items():
        try:
            parsed = _parse_source(group, _fetch_source(GROUP_URLS[group]))
        except (OSError, TimeoutError, URLError, ValueError) as error:
            LOGGER.warning("Market source %s could not be fetched: %s", group, error)
            parsed = {}
        for name in names:
            value = parsed.get(name)
            if value is not None and _valid_value(name, value):
                entry: dict[str, Any] = {
                    "value": f"{value:.2f}",
                    "source_url": SOURCE_URLS[name],
                    "fetched_at": checked_at,
                }
                if name == "repo_rate":
                    old_entry = old_metrics.get(name)
                    old_value = (
                        float(old_entry["value"])
                        if _valid_metric_entry(name, old_entry)
                        else value
                    )
                    entry["direction"] = (
                        "rising" if value > old_value
                        else "falling" if value < old_value
                        else "steady"
                    )
                metrics[name] = entry
                continue
            old_entry = old_metrics.get(name)
            if _valid_metric_entry(name, old_entry):
                metrics[name] = deepcopy(old_entry)
            else:
                metrics[name] = _bootstrap_metric(name)
            stale_names.append(name)
            if value is not None:
                LOGGER.warning("Rejected implausible market value for %s: %r", name, value)
    result = {
        "_note": "Saved public figures are educational assumptions and may be outdated.",
        "metrics": metrics,
        "stale": bool(stale_names),
        "stale_metrics": stale_names,
        "fetched_at": checked_at,
    }
    if metrics:
        saved["metrics"] = metrics
        _save_snapshot(saved)
    return result


def get_market_snapshot(refresh: bool = False) -> dict[str, Any]:
    """Return a 24-hour cached snapshot or refresh it with saved-value fallbacks."""
    global _cached_snapshot, _cache_time
    now = _utc_now()
    if (
        not refresh
        and _cached_snapshot is not None
        and _cache_time is not None
        and now - _cache_time < timedelta(hours=CACHE_HOURS)
    ):
        return deepcopy(_cached_snapshot)
    _cached_snapshot = _refresh_snapshot()
    _cache_time = now
    metrics = _cached_snapshot["metrics"]
    dates = [
        _date_only(entry.get("fetched_at"))
        for entry in metrics.values()
        if isinstance(entry, dict)
    ]
    _cached_snapshot["data_as_of"] = min(dates) if dates else "unknown"
    if _cached_snapshot["stale"]:
        old_dates = [
            _date_only(metrics[name].get("fetched_at"))
            for name in _cached_snapshot["stale_metrics"]
            if name in metrics
        ]
        last_checked = min(old_dates) if old_dates else _cached_snapshot["data_as_of"]
        _cached_snapshot["message"] = (
            f"Data may be outdated (last checked: {last_checked}). "
            "Bootstrap figures may be unverified."
        )
    else:
        _cached_snapshot["message"] = f"Data as of { _cached_snapshot['data_as_of'] }."
    return deepcopy(_cached_snapshot)


def market_summary(snapshot: dict[str, Any]) -> str:
    """Write three plain-English sentences using saved market numbers only."""
    metrics = snapshot["metrics"]
    inflation = metrics["cpi_inflation"]["value"]
    fd_rate = metrics["sbi_1y_fd_rate"]["value"]
    bond = metrics["government_10y_yield"]["value"]
    pe = metrics["nifty_pe"]["value"]
    average = metrics["nifty_pe_10y_average"]["value"]
    gold = metrics["gold_1y_change"]["value"]
    repo_direction = metrics["repo_rate"].get("direction", "steady")
    return (
        f"India inflation is {inflation}% and the one-year SBI deposit rate is {fd_rate}%. "
        f"The RBI repo rate is {repo_direction}, while the 10-year government bond yield is {bond}%. "
        f"Nifty 50 P/E is {pe} compared with its 10-year average of {average}, and gold changed {gold}% in one year."
    )
