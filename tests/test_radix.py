import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import radix  # noqa: E402


def test_parse_int_detects_prefixes_and_decimal():
    assert radix.parse_int("0xff") == 255
    assert radix.parse_int("0b1010") == 10
    assert radix.parse_int("-0o17") == -15
    assert radix.parse_int("1994") == 1994


def test_parse_int_rejects_bad_digits_for_base():
    with pytest.raises(ValueError, match="not a valid base-10"):
        radix.parse_int("ff", 10)


def test_to_base_round_trips_through_every_base():
    for base in range(2, 37):
        for n in (0, 1, 35, 36, 255, 65535, -4096):
            assert radix.parse_int(radix.to_base(n, base), base) == n


def test_division_steps_show_remainders_bottom_up():
    lines = radix.division_steps(10, 2)
    assert lines[0] == "10 / 2 = 5 remainder 0 -> digit 0"
    assert lines[-1].endswith("1010")


def test_twos_complement_encodes_and_decodes():
    assert radix.to_twos(-5, 8) == 0b11111011
    assert radix.from_twos(0b11111011, 8) == -5
    assert radix.to_twos(127, 8) == 127
    with pytest.raises(ValueError, match="does not fit"):
        radix.to_twos(128, 8)


def test_add_reports_carry_and_signed_overflow():
    result, flags = radix.bit_op("add", 127, 8, 1)
    assert result == 0x80
    assert flags == {"carry": 0, "overflow": 1}


def test_sub_borrow_and_arithmetic_shift():
    result, flags = radix.bit_op("sub", 0, 8, 1)
    assert result == 0xFF and flags == {"carry": 1, "overflow": 0}
    assert radix.bit_op("sar", 0b10000000, 8, 1)[0] == 0b11000000
    assert radix.bit_op("shr", 0b10000000, 8, 1)[0] == 0b01000000


def test_roman_round_trip_and_strict_decoding():
    assert radix.roman_encode(1994) == "MCMXCIV"
    assert radix.roman_decode("mmxxvi") == 2026
    with pytest.raises(ValueError, match="not standard"):
        radix.roman_decode("IIII")
    with pytest.raises(ValueError):
        radix.roman_encode(4000)


def test_float32_encode_matches_struct_and_describes_fields():
    pattern = radix.float_encode(0.1, 32)
    assert pattern == int.from_bytes(struct.pack(">f", 0.1), "big")
    text = radix.describe_float(pattern, 32)
    assert "sign=0" in text and "unbiased -4" in text and "kind=normal" in text


def test_float_special_values_are_classified():
    assert "kind=infinity" in radix.describe_float(radix.float_encode(float("inf"), 64), 64)
    assert "kind=nan" in radix.describe_float(radix.float_encode(float("nan"), 32), 32)
    assert "kind=zero" in radix.describe_float(0, 32)


def test_run_command_dispatches_and_reports_unknown():
    assert radix.run_command(["convert", "255", "16"]) == "ff"
    assert radix.run_command(["literal", "0xff"]).startswith("decimal 255")
    with pytest.raises(ValueError, match="unknown command"):
        radix.run_command(["frobnicate"])


def test_batch_file_passes_and_fails_with_exit_codes(tmp_path, capsys):
    good = tmp_path / "good.radix"
    good.write_text("# comment\nconvert 255 16\nexpect convert 255 16 = ff\n", encoding="utf-8")
    assert radix.run_file(str(good)) == 0

    bad = tmp_path / "bad.radix"
    bad.write_text("expect convert 255 16 = 0f\nconvert 1 99\n", encoding="utf-8")
    assert radix.run_file(str(bad)) == 1
    out = capsys.readouterr().out
    assert f"{bad}:1: expect failed" in out
    assert f"{bad}:2: error: base must be between 2 and 36" in out


def test_batch_file_unreadable_returns_two(tmp_path, capsys):
    assert radix.run_file(str(tmp_path / "missing.radix")) == 2


def test_sample_file_passes(capsys):
    sample = os.path.join(os.path.dirname(__file__), "..", "examples", "sample.radix")
    assert radix.run_file(sample) == 0


def test_main_cli_usage_and_single_command(capsys):
    assert radix.main(["convert", "10", "2"]) == 0
    assert capsys.readouterr().out.strip() == "1010"
    assert radix.main(["convert"]) == 2
    assert radix.main([]) == 0
