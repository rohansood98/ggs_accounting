import pytest
from ggs_accounting.utils import camel_case


def test_camel_case():
    assert camel_case("john doe") == "John Doe"
    assert camel_case("APPLE") == "Apple"
