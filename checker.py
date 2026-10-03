"""Bounded exact checker for univariate Bernstein certificates on [0, 1].

No network, third-party packages, model calls, eval, or production integrations.
See README.md for the mathematical claim and trust boundary.
"""
import argparse
from fractions import Fraction
import json
from math import comb
from pathlib import Path
import re

MAX_BYTES = 2_000_000
MAX_CASES = 128
MAX_DEGREE = 16
MAX_BITS = 256
SCHEMA = "asterion.univariate-bernstein.v1"


class Rejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected), "unexpected object fields")


def rational(value):
    require(type(value) is str and len(value) <= 160, "rational must be a bounded string")
    require(re.fullmatch(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?", value) is not None,
            "invalid rational syntax")
    q = Fraction(value)
    require(max(q.numerator.bit_length(), q.denominator.bit_length()) <= MAX_BITS,
            "rational exceeds bit limit")
    require(str(q) == value, "rational is not canonical")
    return q


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def forbidden_number(value):
    raise Rejected("JSON numbers are forbidden; use canonical rational strings")


def loads(data):
    require(type(data) is bytes and len(data) <= MAX_BYTES, "input exceeds byte limit")
    # Reject excessive nesting before the JSON implementation allocates it.
    depth, quoted, escaped = 0, False, False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            require(depth <= 16, "JSON nesting exceeds limit")
        elif byte in (93, 125):
            depth -= 1
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates,
                          parse_float=forbidden_number, parse_int=forbidden_number,
                          parse_constant=forbidden_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Rejected("invalid UTF-8 JSON") from exc


def read(path):
    with Path(path).open("rb") as stream:
        return loads(stream.read(MAX_BYTES + 1))


def verify_case(case):
    keys(case, ("id", "domain", "power", "bernstein", "lower", "upper"))
    require(type(case["id"]) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", case["id"]),
            "invalid case id")
    require(case["domain"] == ["0", "1"], "only normalized domain [0,1] is supported")
    require(type(case["bernstein"]) is list and 1 <= len(case["bernstein"]) <= MAX_DEGREE + 1,
            "invalid Bernstein degree")
    degree = len(case["bernstein"]) - 1
    require(type(case["power"]) is list and 1 <= len(case["power"]) <= degree + 1,
            "invalid power coefficient count")
    power = list(map(rational, case["power"]))
    bern = list(map(rational, case["bernstein"]))
    lower, upper = rational(case["lower"]), rational(case["upper"])
    require(lower <= upper, "reversed bounds")
    # Expand c_k * binom(n,k) * x^k * (1-x)^(n-k).
    # This is the reverse direction of the existing producer's basis conversion.
    rebuilt = [Fraction(0) for _ in range(degree + 1)]
    for k, coefficient in enumerate(bern):
        for j in range(degree - k + 1):
            rebuilt[k+j] += coefficient * comb(degree, k) * comb(degree-k, j) * (-1)**j
    require(rebuilt == power + [Fraction(0)] * (degree+1-len(power)),
            "polynomial identity failed")
    require(min(bern) >= lower and max(bern) <= upper, "coefficient enclosure failed")
    return {"id": case["id"], "degree": degree, "lower": str(lower), "upper": str(upper)}


def verify(document):
    keys(document, ("schema", "cases"))
    require(document["schema"] == SCHEMA, "unknown schema")
    cases = document["cases"]
    require(type(cases) is list and 1 <= len(cases) <= MAX_CASES, "invalid case count")
    checked = [verify_case(case) for case in cases]
    require(len({case["id"] for case in checked}) == len(checked), "duplicate case id")
    return {"status": "VERIFIED_POLYNOMIAL_ENCLOSURES", "cases": checked,
            "scope": "Only the supplied polynomial bounds on [0,1]; no physical-model claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path)
    args = parser.parse_args()
    try:
        result = verify(read(args.certificate))
    except (Rejected, OSError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
