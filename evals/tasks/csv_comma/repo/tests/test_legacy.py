from billing.export import round_currency


def test_bankers_rounding_legacy():
    # Known failing before the agent starts. Tracked separately, not part of the issue.
    assert round_currency(2.675) == 2.68
