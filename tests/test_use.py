import sys

import pytest
from viv import use


def test_use():
    with pytest.raises(ImportError):
        import pyjokes  # noqa

    use("pyjokes")
    import pyjokes  # noqa

    with pytest.raises(ImportError):
        from sample.simple import add_one  # noqa

    assert len([p for p in sys.path if "site-packages" in p]) == 1
