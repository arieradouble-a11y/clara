## What and why

<!-- What does this change, and what problem does it solve? -->

## Checklist

- [ ] `python -m pytest -q` passes (tests added/updated if behavior changed)
- [ ] Keeps the deterministic faithfulness check intact
- [ ] No fabricated data — unvalidated formulas/coefficients ship as partial with
      the gap documented (e.g. `grade_coeffs = None`), not invented
- [ ] Any new dependency is behind an optional extra with a graceful fallback
- [ ] For a language pack: readability source cited; registered; tests added
