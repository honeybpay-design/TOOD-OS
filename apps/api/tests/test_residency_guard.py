import pytest
from app.ai_gateway.residency import ResidencyError, check_endpoint


def test_uk_eu_regions_are_allowed():
    check_endpoint("eu-west-2")
    check_endpoint("UK-South")


@pytest.mark.parametrize("region", ["us-east-1", "global", "", "ap-southeast-1"])
def test_other_regions_are_rejected(region):
    with pytest.raises(ResidencyError):
        check_endpoint(region)
