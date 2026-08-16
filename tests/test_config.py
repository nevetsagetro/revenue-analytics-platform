import pytest

from revenue_analytics.config import GeneratorConfig


def test_profiles_are_explicit() -> None:
    assert GeneratorConfig.from_profile("demo", 3).n_transactions == 2_000
    assert GeneratorConfig.from_profile("portfolio", 3).n_transactions == 250_000


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        GeneratorConfig.from_profile("huge", 42)
