from viv.viv import SpecifierSet, Version, toml_loads


def test_packaging():
    assert Version("3.6") in SpecifierSet(">=3.6")


def test_tomli():
    assert {"requires-python": ">3.6", "dependencies": ["rich", "typer"]} == toml_loads(
        """
    requires-python = ">3.6"
    dependencies = [
        "rich",
        "typer"
    ]
    """
    )
