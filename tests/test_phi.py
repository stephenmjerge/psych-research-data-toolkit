from __future__ import annotations
import pandas as pd
import pytest
from prdt.phi import scan_phi_columns, PhiOptions
from prdt.cli import _guard_against_phi


def test_ignore_columns_skips_phi_scan():
    df = pd.DataFrame({"contact": ["alice@example.com", None], "note": ["ok", None]})
    cleaned, flagged, quarantine = scan_phi_columns(df, PhiOptions(ignore_columns=["contact"]))
    assert "contact" in cleaned.columns
    assert not flagged
    assert quarantine is None


def test_allow_columns_flags_but_keeps_data():
    df = pd.DataFrame({"contact": ["bob@example.com", "carol@example.org"]})
    cleaned, flagged, quarantine = scan_phi_columns(df, PhiOptions(allow_columns=["contact"]))
    assert "contact" in cleaned.columns
    assert quarantine is None
    assert flagged and flagged[0]["column"] == "contact"
    assert any(match["pattern"] == "email" for match in flagged[0]["matches"])


def test_custom_pattern_quarantines_matches():
    df = pd.DataFrame({"notes": ["demo_123", "none"], "score": [1, 2]})
    cleaned, flagged, quarantine = scan_phi_columns(df, PhiOptions(extra_patterns=[r"demo_\d+"]))
    assert "notes" not in cleaned.columns
    assert quarantine is not None
    assert list(quarantine.columns) == ["notes"]
    assert flagged and flagged[0]["column"] == "notes"
    assert any(match["pattern"] == "custom_1" for match in flagged[0]["matches"])


def test_keyword_column_name_triggers_flag():
    df = pd.DataFrame({"guardian_name": ["Alice", "Bob"]})
    cleaned, flagged, quarantine = scan_phi_columns(df, PhiOptions(keywords=["guardian"]))
    assert "guardian_name" not in cleaned.columns
    assert quarantine is not None and "guardian_name" in quarantine.columns
    assert flagged and flagged[0]["column"] == "guardian_name"
    assert any(match["pattern"] == "column_name" for match in flagged[0]["matches"])


def test_phi_guardrail_message_mentions_allow_flag():
    quarantine = pd.DataFrame({"contact": ["a@example.com"]})
    with pytest.raises(SystemExit) as excinfo:
        _guard_against_phi(quarantine, [{"column": "contact"}], allow_export=False)
    message = str(excinfo.value)
    assert "contact" in message
    assert "--allow-phi-export" in message
