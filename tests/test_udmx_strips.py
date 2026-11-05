import pytest

from udmx_strips import ColorError, DMXStrips, DummyDevice, parse_color
from udmx_strips.cli import main, parse_strip_spec


def test_named_and_hex_colors():
    assert parse_color("red") == (255, 0, 0, 0)
    assert parse_color("Warm White") == (255, 120, 40, 200)
    assert parse_color("#ff8800") == (255, 136, 0, 0)
    assert parse_color("f80") == (255, 136, 0, 0)
    assert parse_color("ff880040") == (255, 136, 0, 64)


def test_decimal_and_tuple_colors():
    assert parse_color("1,2,3") == (1, 2, 3, 0)
    assert parse_color("1, 2, 3, 4") == (1, 2, 3, 4)
    assert parse_color((9, 8, 7)) == (9, 8, 7, 0)


@pytest.mark.parametrize("bad", ["", "reed", "300,0,0", "1,2", "#12345"])
def test_bad_colors(bad):
    with pytest.raises(ColorError):
        parse_color(bad)


def test_typo_suggestion():
    with pytest.raises(ColorError, match="red"):
        parse_color("reed")


def test_set_strip_channels():
    dev = DummyDevice()
    DMXStrips(device=dev).set_strip(3, "blue")
    assert dev.writes == [(9, [0, 0, 255, 0])]


def test_set_all_single_transfer():
    dev = DummyDevice()
    DMXStrips(device=dev).set_all("red")
    assert dev.writes == [(1, [255, 0, 0, 0] * 6)]


def test_start_channel_and_brightness():
    dev = DummyDevice()
    DMXStrips(device=dev, start_channel=17, brightness=0.5).set_strip(1, "red")
    assert dev.writes == [(17, [128, 0, 0, 0])]


def test_blackout_and_validation():
    dev = DummyDevice()
    s = DMXStrips(device=dev)
    s.blackout()
    assert dev.writes == [(1, [0] * 24)]
    with pytest.raises(ValueError):
        s.set_strip(7, "red")
    with pytest.raises(ValueError):
        DMXStrips(device=dev, start_channel=500)


def test_strip_spec():
    assert parse_strip_spec("1,3,5-6", 6) == [1, 3, 5, 6]
    assert parse_strip_spec("all", 6) == [1, 2, 3, 4, 5, 6]


def test_cli_dry_run(capsys):
    assert main(["--dry-run", "red"]) == 0
    out = capsys.readouterr().out
    assert "CH1+24" in out and "all strips" in out
    assert main(["--dry-run", "-s", "2", "-b", "50", "blue"]) == 0
    assert "CH5+4" in capsys.readouterr().out


def test_cli_errors(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--dry-run", "notacolor"])
    assert e.value.code == 2
