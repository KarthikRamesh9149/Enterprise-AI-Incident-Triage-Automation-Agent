# Evaluation

The local eval runner stores evaluation runs and cases. Current deterministic dataset covers:

- Redaction: secrets are replaced with `[REDACTED]`.
- Prompt injection: suspicious runbook instructions are flagged.
- Approval gate: mock external actions require approval.

Run with:

```bash
make evals
```

Or as admin in the UI from Evals.

