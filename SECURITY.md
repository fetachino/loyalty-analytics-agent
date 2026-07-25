# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability or exposed credential. Contact
the repository owner privately with the affected component, reproduction steps, and potential
impact. Do not include real customer data, API keys, passwords, or session cookies.

## Credential handling

- Store local credentials only in `.env`; the file is intentionally excluded by `.gitignore`.
- Configure hosted credentials through the deployment platform's secret environment variables.
- Use separate development and production credentials with the minimum required permissions.
- Revoke and replace any credential that appears in source control, logs, screenshots, or chat.
- Never reuse the administrator password as `AUTH_SECRET_KEY`.

The repository includes `.env.example` with variable names and safe placeholders only.

## Supported version

Security fixes are applied to the latest release on `main`.
