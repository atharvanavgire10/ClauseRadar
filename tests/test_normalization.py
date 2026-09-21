"""Phase 19 — obligation normalization edge cases (unit)."""
from obligations.extractor import (
    extract_action,
    extract_actor,
    extract_frequency,
    has_obligation_language,
)


def test_actor_variants():
    assert extract_actor("The Supplier shall deliver goods.") == "Supplier"
    assert extract_actor("Client must pay on time.") == "Client"
    assert extract_actor("The Contractor agrees to finish the work.") == "Contractor"
    assert extract_actor("Either party may terminate with notice.") == "Either party"
    assert extract_actor("Invoices are due monthly.") == ""  # no party named


def test_modal_variants_detected():
    for text in ("Vendor shall insure.", "Vendor must insure.", "Vendor will insure.",
                 "Vendor agrees to insure.", "Vendor is required to insure.",
                 "Vendor are required to insure.", "Vendor is responsible for cover.",
                 "Vendor covenants to maintain cover."):
        assert has_obligation_language(text), text
    assert not has_obligation_language("Insurance is described in Exhibit B.")


def test_frequency_spectrum():
    assert extract_frequency("Reports are due daily here.") == "DAILY"
    assert extract_frequency("Reports are due weekly here.") == "WEEKLY"
    assert extract_frequency("Reports are due monthly here.") == "MONTHLY"
    assert extract_frequency("Reports are due quarterly here.") == "QUARTERLY"
    assert extract_frequency("Reports are due semi-annual here.") == "SEMI_ANNUAL"
    assert extract_frequency("Reports are due annually here.") == "ANNUAL"
    assert extract_frequency("Maintain cover throughout the term period.") == "CONTINUOUS"
    assert extract_frequency("Provide 60 days notice before renewal.") == "ONE_TIME"


def test_action_truncation_deterministic():
    long_text = "The Vendor shall " + "maintain very detailed comprehensive insurance coverage documentation " * 10
    action = extract_action(long_text)
    assert action.startswith("shall")
    assert len(action) <= 280
    # Same input → same output (deterministic).
    assert extract_action(long_text) == action


def test_action_without_modal_falls_back_to_prefix():
    assert extract_action("General statement of intent.") == "General statement of intent."
