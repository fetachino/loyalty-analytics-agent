# Deployment guide

The repository includes a Render Blueprint for a reproducible portfolio deployment consisting of
the Dockerized FastAPI service and a managed PostgreSQL database.

## Before deploying

You need:

- a Render account connected to the GitHub repository;
- an OpenAI API key with available API credit;
- an administrator email address;
- a unique administrator password of at least 12 characters.

Do not reuse your GitHub, email, or OpenAI password as the administrator password.

## Create the deployment

1. Merge the deployment-readiness pull request into `main`.
2. In the Render dashboard, select **New**, then **Blueprint**.
3. Connect `fetachino/loyalty-analytics-agent`.
4. Render detects `render.yaml` and displays the web service and PostgreSQL database.
5. Enter `OPENAI_API_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` when prompted.
6. Review the selected Free instance types and apply the Blueprint.
7. Follow the deploy logs until the service health check succeeds.
8. Open the generated `onrender.com` URL and sign in with the administrator credentials.

The Blueprint generates `AUTH_SECRET_KEY` inside Render. It is never stored in Git. Database
migrations and administrator reconciliation run before each service start. The portfolio seed runs
only if the customer table is empty, so restarts never replace existing data. This also makes a
password reset deterministic: update `ADMIN_PASSWORD` in Render and deploy the latest commit.

## Production configuration

The deployment sets:

- `APP_ENV=production`, enabling strict configuration validation;
- `AUTH_COOKIE_SECURE=true`, restricting sessions to HTTPS;
- a generated signing key of at least 32 characters;
- the managed database's private connection string;
- `RUN_MIGRATIONS=true`, applying migrations before the single Free instance starts;
- `BOOTSTRAP_ADMIN=true`, reconciling the configured administrator before startup;
- `SEED_DEMO_DATA=true`, loading sample analytics only when the database has no customers;
- `/health/ready` as the platform health check.

Render terminates the deployment early if required production security settings are missing.

## Free-tier limitations

The included Blueprint intentionally selects Free instances for a low-cost portfolio demo. Render
Free web services spin down after inactivity and can take about a minute to wake. Free PostgreSQL
databases expire 30 days after creation, have no backups, and are not suitable for production data.

Before using the application for a real workload:

- move the web service and PostgreSQL database to paid instance types;
- configure database backups;
- move migrations to the platform's paid pre-deploy command;
- rotate all credentials used during evaluation;
- configure a custom domain and monitoring.

## Updating and troubleshooting

The service deploys from `main` only after linked GitHub checks pass. Inspect the Render deploy logs
if a build or health check fails. Common causes are an invalid OpenAI key, an administrator password
shorter than 12 characters, or missing environment variables.

To check the deployed service:

```text
GET /health/live
GET /health/ready
```

Never paste Render environment values, deploy hook URLs, session cookies, or API keys into issues,
pull requests, screenshots, or chat messages.
