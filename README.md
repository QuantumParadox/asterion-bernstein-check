# ASTERION Bernstein Check, version 0.1.0

A small Python standard-library checker for rational, univariate polynomial bounds on the normalized interval [0,1]. This isolated utility is released under the MIT license; see LICENSE.

## Use

With Python 3.10 or newer, open a terminal in this extracted directory:

```text
python -B replay.py
python -B checker.py qutrit_denominators.json
```

No installation, API keys, provider accounts or network access are required. Exit code 0 means the supplied certificate was accepted; 1 means rejection. A rejected certificate may describe a true statement that this particular certificate cannot establish. Rejection is not a proof that the proposed inequality is false.

## What is established

For degree n and rational coefficients c[k], the checker expands

    p(x) = sum(c[k] * binomial(n,k) * x^k * (1-x)^(n-k), k=0..n).

It compares every resulting power coefficient with the supplied polynomial using exact rational arithmetic. It then checks lower <= c[k] <= upper for every coefficient. Bernstein basis terms are nonnegative and sum to 1 on [0,1], so the two bounds hold for every real x in that interval. This familiar convex-hull property is established mathematics, not a novel theorem.

The 40 shipped cases are primal-denominator polynomials from ASTERION's existing qutrit study. Their variable is a normalized interpolation coordinate, not the original measurement parameter t. `source_bindings.json` preserves the original t intervals and coefficients. This package verifies the polynomials; it does not establish the physical reduction, Choi positivity, qutrit compatibility threshold, or the full uniform sensitivity theorem.

## Format

`schema` is `asterion.univariate-bernstein.v1`. `cases` is a nonempty list of at most 128 objects. Each case has exactly `id`, `domain`, `power`, `bernstein`, `lower`, `upper`. Coefficients in `power` are in ascending power order. Degree is one less than the Bernstein coefficient count, with maximum 16. Power coefficients may be padded implicitly by zeros.

Every number is a canonical rational string, such as `"0"`, `"-2"` or `"3/7"`. Reduced fractions with positive denominators are required. JSON numbers, duplicate keys, unknown fields, nonfinite values and other domains are rejected. The input limit is 2,000,000 bytes and 16 nesting levels; rational numerator and denominator are limited to 256 bits. An id is 1 to 64 ASCII letters, digits, underscores or hyphens.

## Verification and trust

Tests cover the 40 recorded polynomials, a second basis-conversion algorithm on 400 deterministic synthetic examples, exact point evaluations, degree elevation, invalid inputs and six semantic corruptions per recorded polynomial. The synthetic cases are development tests, not unseen AI evaluation tasks. No model performance, new discovery or external human review is claimed.

Python, its rational arithmetic and this checker remain in the trusted computing base. The new checker itself is not formally verified. A prior Lean run for the original 40 polynomial identities and lower bounds is recorded separately; Lean is not recompiled here. Same-agent implementation and tests do not constitute independent human review.

`replay.py` also checks the file-set manifest. SHA-256 detects changed bytes relative to that manifest, but an editable manifest is not a signature or proof of authorship. Obtain the ZIP digest through a trusted channel. The fresh-extraction receipt outside this package records release checks, including a semantic corruption with its manifest deliberately recomputed.

## Prior art and attribution

Cesar Munoz and Anthony Narkawicz, "Formalization of a Representation of Bernstein Polynomials and Applications to Global Optimization," Journal of Automated Reasoning 51(2), 151-196 (2013). NASA's PVS Bernstein library already handles substantially broader multivariate problems: https://shemesh.larc.nasa.gov/fm/pvs/Bernstein/

This candidate includes no code from that library. The utility being assessed is a small interchange format, explicit rejection behavior and easy offline replay. Novelty, publication suitability, user adoption and comparative performance remain unestablished.

## Release status

See `RELEASE_STATUS.md` and `VALIDATION.json`. MIT applies to this repository only. The full MIRANDA and ASTERION platforms have not been relicensed. This utility does not certify those platforms.
