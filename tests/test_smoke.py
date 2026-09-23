"""Package import smoke test."""


def test_package_imports():
    import pydecay

    assert pydecay.__version__ == "0.2.0"
