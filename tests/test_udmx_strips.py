import pytest

from udmx_strips import ColorError, DMXStrips, DummyDevice, parse_color
from udmx_strips.cli import main, parse_strip_spec


def test_named_and_hex_colors():
    assert parse_color("red") == (255, 0, 0)
    assert parse_color("White") == (255, 255, 255)
    assert parse_color("Warm White") == (255, 170, 80)
    assert parse_color("#ff8800") == (255, 136, 0)
    assert parse_color("f80") == (255, 136, 0)


def test_decimal_and_tuple_colors():
    assert parse_color("1,2,3") == (1, 2, 3)
    assert parse_color("1, 2, 3") == (1, 2, 3)
    assert parse_color((9, 8, 7)) == (9, 8, 7)


@pytest.mark.parametrize("bad", ["", "reed", "300,0,0", "1,2", "1,2,3,4", "#12345"])
def test_bad_colors(bad):
    with pytest.raises(ColorError):
        parse_color(bad)


def test_typo_suggestion():
    with pytest.raises(ColorError, match="red"):
        parse_color("reed")


def test_set_strip_channels():
    dev = DummyDevice()
    DMXStrips(device=dev).set_strip(3, "blue")
    assert dev.writes == [(7, [0, 0, 255])]


def test_set_all_single_transfer():
    dev = DummyDevice()
    DMXStrips(device=dev).set_all("red")
    assert dev.writes == [(1, [255, 0, 0] * 6)]


def test_start_channel_and_brightness():
    dev = DummyDevice()
    DMXStrips(device=dev, start_channel=17, brightness=0.5).set_strip(1, "red")
    assert dev.writes == [(17, [128, 0, 0])]


def test_set_colors():
    dev = DummyDevice()
    DMXStrips(device=dev, num_strips=4).set_colors(["red", "green"], first_strip=2)
    assert dev.writes == [(4, [255, 0, 0, 0, 255, 0])]


def test_blackout_and_validation():
    dev = DummyDevice()
    s = DMXStrips(device=dev)
    s.blackout()
    assert dev.writes == [(1, [0] * 18)]
    with pytest.raises(ValueError):
        s.set_strip(7, "red")
    with pytest.raises(ValueError):
        DMXStrips(device=dev, start_channel=510)


def test_strip_spec():
    assert parse_strip_spec("1,3,5-6", 6) == [1, 3, 5, 6]
    assert parse_strip_spec("all", 6) == [1, 2, 3, 4, 5, 6]


def test_cli_dry_run(capsys):
    assert main(["--dry-run", "red"]) == 0
    out = capsys.readouterr().out
    assert "CH1+18" in out and "all strips" in out
    assert main(["--dry-run", "-s", "2", "-b", "50", "blue"]) == 0
    assert "CH4+3" in capsys.readouterr().out
    assert main(["--dry-run", "--strips", "4", "red", "green", "blue"]) == 0
    assert "CH1+9" in capsys.readouterr().out


def test_cli_errors():
    with pytest.raises(SystemExit) as e:
        main(["--dry-run", "notacolor"])
    assert e.value.code == 2


def test_color_order_brg():
    dev = DummyDevice()
    s = DMXStrips(device=dev, color_order="brg")
    s.set_strip(1, "red")      # red must land on channel 2
    s.set_strip(1, "blue")     # blue on channel 1
    s.set_strip(1, "green")    # green on channel 3
    assert dev.writes == [(1, [0, 255, 0]), (1, [255, 0, 0]), (1, [0, 0, 255])]
    s.set_all("red")
    assert dev.writes[-1] == (1, [0, 255, 0] * 6)


def test_bad_color_order():
    with pytest.raises(ValueError):
        DMXStrips(device=DummyDevice(), color_order="RRG")


def test_cli_order(capsys):
    assert main(["--dry-run", "--order", "BRG", "-s", "1", "red"]) == 0
    assert "  0 255   0" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["--dry-run", "--order", "XYZ", "red"])
