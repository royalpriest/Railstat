import pytest

from report_tool.privacy import display_name, mask_name


@pytest.mark.parametrize(
    ("name", "masked"),
    [("Maria Gonzalez", "M. G•••••••"), ("Ann Mary Lee", "A. L••"), ("Cher", "C•••"), ("  ", "")],
)
def test_mask_name(name, masked):
    assert mask_name(name) == masked


def test_display_name():
    assert display_name("Ann Lee", show_names=True) == "Ann Lee"
    assert display_name("Ann Lee", show_names=False) == "A. L••"
