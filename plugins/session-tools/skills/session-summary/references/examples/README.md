# Close-out golden examples

Excerpts (frontmatter and the tail of the body) showing the two valid close-outs and the
violations the contract rules reject. These are the reference cases for anyone changing the
close-out rules in `../summary-contract.md`. A repository validator (`check_command`) applies
only where a contract is declared: it should accept `contract-close-out.md` and reject
`contract-violations.md`; `default-close-out.md` has no contract and therefore no validator.

| File | Verdict |
|------|---------|
| `default-close-out.md` | PASS — no contract file; ends with `## Unfinished Work` |
| `contract-close-out.md` | PASS — contract declared; ends with `## Board updated` in `closing_format` |
| `contract-violations.md` | FAIL — seven annotated ways a contract-governed summary goes wrong |
