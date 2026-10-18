# Radix

**Offline number-base, bit-width and float toolkit in one stdlib Python file.**

Radix converts integers between bases 2 to 36, shows the division steps behind each
conversion, works out two's-complement patterns and overflow flags for any bit width,
decodes IEEE-754 floats field by field, and checks roman numerals strictly. Every command
is one line of text, so the same vocabulary works at the shell and in batch files that
gate CI with `expect` lines.

No servers, no accounts, no network calls, no third-party packages. Python 3 standard
library only (pytest is needed to run the tests).

## Features

- Convert any integer between bases 2 and 36, with `0x`, `0o` and `0b` prefixes read automatically.
- Explain a conversion step by step as the repeated division and remainders that produce the digits.
- Show one number as decimal, hex, octal and binary together (`literal`).
- Encode signed values as two's-complement patterns at any width from 1 to 512 bits, rejecting values that do not fit.
- Decode a bit pattern back to its signed and unsigned values.
- Run bitwise `and`, `or`, `xor`, `not`, logical and arithmetic shifts, `shl`, `shr` and `sar`.
- Run `add` and `sub` at a fixed width and report carry and signed overflow flags.
- Encode a decimal number as IEEE-754 float32 or float64, rounded to nearest.
- Decode any float bit pattern into sign, exponent, mantissa, kind (normal, subnormal, zero, infinity, NaN) and the exact stored value.
- Convert integers to roman numerals (1 to 3999) and back, rejecting non-standard spellings such as `IIII`.
- Run batch files of commands with `#` comments and line-numbered `file:line:` errors.
- Gate CI with `expect COMMAND = OUTPUT` lines: failed expectations are reported with the actual and wanted output.
- Exit codes for scripts: `0` clean, `1` batch errors or failed expectations, `2` bad usage or unreadable file.

## Quick start

Needs Python 3.8 or newer. No installation step.

```sh
python3 radix.py convert 255 16
```

Output:

```text
ff
```

A fuller example:

```sh
python3 radix.py untwos 11111011 8
python3 radix.py op add 127 1 8
python3 radix.py floatbits 32 0x3dcccccd
```

Output:

```text
-5 (bits=11111011 hex=0xfb unsigned=251 signed=-5)
bits=10000000 hex=0x80 unsigned=128 signed=-128 carry=0 overflow=1
sign=0 exponent=01111011 (unbiased -4) mantissa=10011001100110011001101 kind=normal value=0.10000000149011612
```

The `add` line shows the 8-bit overflow: 127 + 1 wraps to −128 with the signed overflow flag set.

## Command reference

| Command | Meaning |
| --- | --- |
| `convert VALUE TO_BASE [FROM_BASE]` | Change base. Decimal unless prefixed or `FROM_BASE` is given. |
| `steps VALUE TO_BASE` | Show the division steps behind a conversion. |
| `literal VALUE` | Decimal, hex, octal and binary forms together. |
| `twos VALUE WIDTH` | Two's-complement pattern of a signed value. |
| `untwos PATTERN WIDTH` | Signed value of a pattern. Binary unless prefixed. |
| `op NAME A [B] WIDTH` | `not`, `and`, `or`, `xor`, `shl`, `shr`, `sar`, `add`, `sub`. |
| `roman VALUE` | Integer to roman numeral. |
| `unroman TEXT` | Roman numeral to integer, strictly checked. |
| `float 32\|64 DECIMAL` | Encode a decimal as IEEE-754 and show its fields. |
| `floatbits 32\|64 PATTERN` | Decode a bit pattern. Hex unless prefixed. |
| `run FILE` | Run a batch file with `expect` checks. |

Run `python3 radix.py help` for the same list.

## Batch files

A batch file holds one command per line. Blank lines and lines starting with `#` are
skipped. An `expect` line runs a command and compares its output exactly.

```text
# examples/sample.radix (excerpt)
convert 255 16
expect convert 255 16 = ff
expect roman 1994 = MCMXCIV
```

```sh
python3 radix.py run examples/sample.radix
```

Each command prints `FILE:LINE: RESULT`. Errors and failed expectations are printed with
the same `FILE:LINE:` prefix, followed by a summary line.

## Running the sample

```sh
python3 radix.py run examples/sample.radix
```

This runs every command in the sample and then its five `expect` checks. It exits `0`
when they all pass.

## Testing

The tests use pytest and cover the parsers, base conversion, two's complement, overflow
flags, roman numerals, IEEE-754 decoding, the command dispatcher, batch-file exit codes
and the command-line entry point.

```sh
python3 -m pip install pytest
python3 -m pytest -q tests
```

## Project layout

```text
radix.py              the whole tool: parsing, maths, commands, batch runner, CLI
examples/sample.radix sample batch file with expect checks
tests/test_radix.py   pytest suite
README.md             this file
```

## Notes and limits

- Bit widths run from 1 to 512. Shift counts must be between 0 and the width.
- Floats follow the platform's `struct` module, which rounds to nearest. `float 32` values
  that overflow float32 are rejected rather than becoming infinity.
- Roman numerals are the standard subtractive form up to 3999 only.
