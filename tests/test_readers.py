import pytest
from viv.viv import _read_metadata_block, _uses_viv, _Viv_Mode

RUN_METADATA_SCRIPT = """
#!/usr/bin/env -S viv run -s
# /// script
# requires-python = ">3.10"
# dependencies = [
#   "rich"
# ]
# ///
"""

USE_SCRIPT = """
#!/usr/bin/env python3
__import__("viv").use("rich")

from rich import print
print("pretty!")
"""


def test_metadata():
    metadata = _read_metadata_block(RUN_METADATA_SCRIPT)
    assert metadata == {"requires-python": ">3.10", "dependencies": ["rich"]}


def test_uses():
    assert _uses_viv(RUN_METADATA_SCRIPT) == _Viv_Mode.NONE
    assert (
        _uses_viv(RUN_METADATA_SCRIPT + """\n__import__("viv").run()\n""")
        == _Viv_Mode.RUN
    )
    assert _uses_viv(USE_SCRIPT) == _Viv_Mode.USE
    assert _uses_viv("# from viv import use") == _Viv_Mode.NONE


def test_uses_fail(caplog):
    with pytest.raises(SystemExit):
        _uses_viv("""__import__("viv").run()\n__import__("viv").use()""")
    with pytest.raises(SystemExit):
        _uses_viv("""__import__("viv").unknown()""")

    assert [
        (
            "viv",
            40,
            "Unexpected number of viv references in script.\n"
            "Expected only 1, found: run, use",
        ),
        ("viv", 40, "Unknown function unknown associated with viv."),
    ] == caplog.record_tuples
