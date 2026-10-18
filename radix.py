"""Radix: offline number-base, two's-complement, bit-op, roman and float toolkit.

Every command works on one line of text, so the same vocabulary serves the
command line (``python3 radix.py convert 255 16``) and batch files checked in CI
(``python3 radix.py run examples/sample.radix``).
"""

import math
import struct
import sys
from operator import and_, or_, xor

DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
PREFIXES = {"0b": 2, "0o": 8, "0x": 16}
ROMAN_TABLE = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
BIT_LOGIC = {"and": and_, "or": or_, "xor": xor}
SHIFTS = {"shl", "shr", "sar"}
ARITHMETIC = {"add", "sub"}
UNARY_OPS = {"not"}
BINARY_OPS = set(BIT_LOGIC) | SHIFTS | ARITHMETIC
# format code for struct, exponent bits, mantissa bits
FLOAT_LAYOUT = {32: (">f", 8, 23), 64: (">d", 11, 52)}
MAX_WIDTH = 512


def _check_base(base):
    if not 2 <= base <= 36:
        raise ValueError(f"base must be between 2 and 36, not {base}")


def _check_width(width):
    if not 1 <= width <= MAX_WIDTH:
        raise ValueError(f"width must be between 1 and {MAX_WIDTH}, not {width}")


def _int_arg(text, what):
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{what} {text!r} is not a whole number") from None


def parse_int(text, base=None):
    """Parse an integer. With no base, a 0x/0o/0b prefix is honoured, else decimal."""
    stripped = text.strip()
    if base is None:
        base = PREFIXES.get(stripped.lstrip("+-")[:2].lower(), 10)
    _check_base(base)
    try:
        return int(stripped, base)
    except ValueError:
        raise ValueError(f"{text!r} is not a valid base-{base} integer") from None


def to_base(n, base):
    """Render an integer in any base from 2 to 36, using lowercase digits."""
    _check_base(base)
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    m = abs(n)
    out = []
    while m:
        m, r = divmod(m, base)
        out.append(DIGITS[r])
    return sign + "".join(reversed(out))


def division_steps(n, base):
    """Explain a conversion as the repeated division that produces its digits."""
    _check_base(base)
    if n < 0:
        raise ValueError("steps needs a non-negative value")
    if n == 0:
        return ["0 has no division steps; its only digit is 0"]
    lines = []
    m = n
    while m:
        q, r = divmod(m, base)
        lines.append(f"{m} / {base} = {q} remainder {r} -> digit {DIGITS[r]}")
        m = q
    lines.append(f"read the digits bottom-up: {to_base(n, base)}")
    return lines


def _check_fits(n, width, what="value"):
    lo, hi = -(1 << (width - 1)), (1 << width) - 1
    if not lo <= n <= hi:
        raise ValueError(f"{what} {n} does not fit in {width} bits ({lo} to {hi})")


def to_twos(n, width):
    """Two's-complement bit pattern of a signed value in the given width."""
    _check_width(width)
    lo, hi = -(1 << (width - 1)), (1 << (width - 1)) - 1
    if not lo <= n <= hi:
        raise ValueError(f"{n} does not fit in {width} signed bits ({lo} to {hi})")
    return n & ((1 << width) - 1)


def from_twos(pattern, width):
    """Signed value of a two's-complement bit pattern."""
    _check_width(width)
    if not 0 <= pattern < (1 << width):
        raise ValueError(f"pattern {pattern} is not a {width}-bit value")
    return pattern - (1 << width) if pattern >> (width - 1) else pattern


def describe_pattern(pattern, width):
    digits = math.ceil(width / 4)
    return (
        f"bits={pattern:0{width}b} hex=0x{pattern:0{digits}x} "
        f"unsigned={pattern} signed={from_twos(pattern, width)}"
    )


def _pattern(n, width):
    _check_fits(n, width)
    return n & ((1 << width) - 1)


def bit_op(name, a, width, b=None):
    """Bitwise, shift and add/sub operations on width-bit values.

    Returns (result_pattern, flags). Add and sub report carry and overflow.
    """
    _check_width(width)
    mask = (1 << width) - 1
    pa = _pattern(a, width)
    flags = {}
    if name == "not":
        return pa ^ mask, flags
    if name in SHIFTS:
        if not 0 <= b <= width:
            raise ValueError(f"shift count must be between 0 and {width}, not {b}")
        if name == "shl":
            return (pa << b) & mask, flags
        if name == "shr":
            return pa >> b, flags
        return (from_twos(pa, width) >> b) & mask, flags
    pb = _pattern(b, width)
    if name in BIT_LOGIC:
        return BIT_LOGIC[name](pa, pb), flags
    top = 1 << (width - 1)
    sa, sb = bool(pa & top), bool(pb & top)
    if name == "add":
        raw = pa + pb
        result = raw & mask
        flags["carry"] = int(raw > mask)
        flags["overflow"] = int(sa == sb and bool(result & top) != sa)
    else:
        raw = pa - pb
        result = raw & mask
        flags["carry"] = int(pa < pb)
        flags["overflow"] = int(sa != sb and bool(result & top) != sa)
    return result, flags


def roman_encode(n):
    if not 1 <= n <= 3999:
        raise ValueError(f"roman numerals cover 1 to 3999, not {n}")
    out = []
    for value, symbol in ROMAN_TABLE:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)


def roman_decode(text):
    s = text.strip().upper()
    if not s or any(c not in ROMAN_VALUES for c in s):
        raise ValueError(f"{text!r} has characters that are not roman numerals")
    total = 0
    for i, c in enumerate(s):
        v = ROMAN_VALUES[c]
        if i + 1 < len(s) and v < ROMAN_VALUES[s[i + 1]]:
            total -= v
        else:
            total += v
    if not 1 <= total <= 3999:
        raise ValueError(f"{text!r} is outside the roman range 1 to 3999")
    if roman_encode(total) != s:
        raise ValueError(f"{text!r} is not standard; write it as {roman_encode(total)}")
    return total


def float_encode(value, bits):
    """IEEE-754 bit pattern of a decimal value, rounded to nearest."""
    code, _, _ = FLOAT_LAYOUT[bits]
    try:
        raw = struct.pack(code, value)
    except OverflowError:
        raise ValueError(f"{value} is too large for float{bits}") from None
    return int.from_bytes(raw, "big")


def describe_float(pattern, bits):
    """Split an IEEE-754 pattern into sign, exponent, mantissa and exact value."""
    code, ebits, mbits = FLOAT_LAYOUT[bits]
    if not 0 <= pattern < (1 << bits):
        raise ValueError(f"pattern {pattern} is not a {bits}-bit value")
    bias = (1 << (ebits - 1)) - 1
    sign = pattern >> (bits - 1)
    efield = (pattern >> mbits) & ((1 << ebits) - 1)
    mfield = pattern & ((1 << mbits) - 1)
    if efield == (1 << ebits) - 1:
        kind = "nan" if mfield else "infinity"
        exponent = "n/a"
    elif efield == 0:
        kind = "zero" if mfield == 0 else "subnormal"
        exponent = str(1 - bias)
    else:
        kind = "normal"
        exponent = str(efield - bias)
    value = struct.unpack(code, pattern.to_bytes(bits // 8, "big"))[0]
    return (
        f"sign={sign} exponent={efield:0{ebits}b} (unbiased {exponent}) "
        f"mantissa={mfield:0{mbits}b} kind={kind} value={value!r}"
    )


def _arity(args, low, high, usage):
    if not low <= len(args) <= high:
        raise ValueError(f"usage: {usage}")


def _float_width(text):
    bits = _int_arg(text, "float width")
    if bits not in FLOAT_LAYOUT:
        raise ValueError("float width must be 32 or 64")
    return bits


def _bits_arg(text, default_base):
    base = PREFIXES.get(text.strip().lstrip("+-")[:2].lower(), default_base)
    value = parse_int(text, base)
    if value < 0:
        raise ValueError(f"bit pattern {text!r} cannot be negative")
    return value


def cmd_convert(args):
    _arity(args, 2, 3, "convert VALUE TO_BASE [FROM_BASE]")
    from_base = _int_arg(args[2], "base") if len(args) == 3 else None
    value = parse_int(args[0], from_base)
    return to_base(value, _int_arg(args[1], "base"))


def cmd_steps(args):
    _arity(args, 2, 2, "steps VALUE TO_BASE")
    value = parse_int(args[0])
    return "; ".join(division_steps(value, _int_arg(args[1], "base")))


def cmd_literal(args):
    _arity(args, 1, 1, "literal VALUE")
    n = parse_int(args[0])
    sign, m = ("-" if n < 0 else ""), abs(n)
    return (
        f"decimal {n}  hex {sign}0x{to_base(m, 16)}  "
        f"oct {sign}0o{to_base(m, 8)}  bin {sign}0b{to_base(m, 2)}"
    )


def cmd_twos(args):
    _arity(args, 2, 2, "twos VALUE WIDTH")
    width = _int_arg(args[1], "width")
    return describe_pattern(to_twos(parse_int(args[0]), width), width)


def cmd_untwos(args):
    _arity(args, 2, 2, "untwos PATTERN WIDTH")
    width = _int_arg(args[1], "width")
    _check_width(width)
    pattern = _bits_arg(args[0], 2)
    return f"{from_twos(pattern, width)} ({describe_pattern(pattern, width)})"


def cmd_op(args):
    if not args:
        raise ValueError("usage: op NAME A [B] WIDTH")
    name = args[0].lower()
    if name in UNARY_OPS:
        _arity(args, 3, 3, "op not A WIDTH")
        a, b, width = parse_int(args[1]), None, _int_arg(args[2], "width")
    elif name in BINARY_OPS:
        _arity(args, 4, 4, f"op {name} A B WIDTH")
        a, b, width = parse_int(args[1]), parse_int(args[2]), _int_arg(args[3], "width")
    else:
        raise ValueError(
            f"unknown op {name!r}; use not, and, or, xor, shl, shr, sar, add or sub"
        )
    result, flags = bit_op(name, a, width, b)
    extra = "".join(f" {key}={value}" for key, value in flags.items())
    return describe_pattern(result, width) + extra


def cmd_roman(args):
    _arity(args, 1, 1, "roman VALUE")
    return roman_encode(parse_int(args[0]))


def cmd_unroman(args):
    if not args:
        raise ValueError("usage: unroman TEXT")
    return str(roman_decode(" ".join(args)))


def cmd_float(args):
    _arity(args, 2, 2, "float 32|64 DECIMAL")
    bits = _float_width(args[0])
    try:
        value = float(args[1])
    except ValueError:
        raise ValueError(f"{args[1]!r} is not a decimal number") from None
    return describe_float(float_encode(value, bits), bits)


def cmd_floatbits(args):
    _arity(args, 2, 2, "floatbits 32|64 PATTERN")
    bits = _float_width(args[0])
    return describe_float(_bits_arg(args[1], 16), bits)


COMMANDS = {
    "convert": cmd_convert,
    "steps": cmd_steps,
    "literal": cmd_literal,
    "twos": cmd_twos,
    "untwos": cmd_untwos,
    "op": cmd_op,
    "roman": cmd_roman,
    "unroman": cmd_unroman,
    "float": cmd_float,
    "floatbits": cmd_floatbits,
}


def run_command(tokens):
    """Run one command given as a list of words and return its text result."""
    if not tokens:
        raise ValueError("empty command")
    name = tokens[0].lower()
    handler = COMMANDS.get(name)
    if handler is None:
        raise ValueError(f"unknown command {name!r}; try: {', '.join(COMMANDS)}")
    return handler(tokens[1:])


def run_file(path):
    """Run a batch file. Returns 0 when clean, 1 on errors or failed expectations, 2 if unreadable."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        print(f"radix: cannot read {path}: {exc.strerror}", file=sys.stderr)
        return 2
    errors = checks = failed = 0
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            if line.startswith("expect "):
                command, sep, wanted = line[len("expect "):].partition("=")
                if not sep:
                    raise ValueError("expect needs '= expected output' after the command")
                checks += 1
                got = run_command(command.split())
                if got != wanted.strip():
                    failed += 1
                    print(f"{path}:{lineno}: expect failed: got {got!r}, wanted {wanted.strip()!r}")
            else:
                print(f"{path}:{lineno}: {run_command(line.split())}")
        except ValueError as exc:
            errors += 1
            print(f"{path}:{lineno}: error: {exc}")
    print(f"{path}: {checks} expectations, {failed} failed, {errors} errors")
    return 1 if errors or failed else 0


USAGE = """usage: radix COMMAND ARGS...
       radix run FILE

commands:
  convert VALUE TO_BASE [FROM_BASE]   change base (2-36); 0x/0o/0b prefixes are read
  steps VALUE TO_BASE                 show the division steps behind a conversion
  literal VALUE                       decimal, hex, octal and binary forms together
  twos VALUE WIDTH                    two's-complement pattern of a signed value
  untwos PATTERN WIDTH                signed value of a pattern (binary unless prefixed)
  op NAME A [B] WIDTH                 not, and, or, xor, shl, shr, sar, add, sub with flags
  roman VALUE                         integer to roman numeral (1-3999)
  unroman TEXT                        roman numeral to integer, strictly checked
  float 32|64 DECIMAL                 IEEE-754 fields and exact stored value
  floatbits 32|64 PATTERN             decode a bit pattern (hex unless prefixed)
  run FILE                            batch file with 'expect CMD = OUTPUT' checks

exit codes: 0 ok, 1 batch errors or failed expectations, 2 bad usage or unreadable file
"""


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    if argv[0] == "run":
        if len(argv) != 2:
            print("usage: radix run FILE", file=sys.stderr)
            return 2
        return run_file(argv[1])
    try:
        print(run_command(argv))
    except ValueError as exc:
        print(f"radix: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
