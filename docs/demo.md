# Guided portfolio demonstration

This guide presents the project in a focused five-to-seven-minute walkthrough. The Render free
service may take about a minute to wake after inactivity.

## 1. Establish the product

Open the [live application](https://loyalty-analytics-agent.onrender.com/) and sign in with the
administrator account.

On **Overview**, call out:

- program-wide customer, purchase, points, and redemption KPIs;
- category-level spending and loyalty-tier distribution;
- Snowflake as the deployed analytics provider with PostgreSQL fallback;
- CSV reporting and the authenticated AI analyst.

Do not expose credentials, session cookies, private keys, or Render environment values during a
recording or screen share.

## 2. Demonstrate an operational write

Open **Manage data** and create a clearly labeled demo customer using a non-personal example email.
Record a small purchase and show that the customer selector reflects the credited points. Redeem a
reward within the available balance and show the deduction.

Explain that:

- write endpoints are administrator-only;
- validation happens at the API boundary;
- customer rows are locked during points changes;
- PostgreSQL is the transactional system of record.

Avoid repeatedly creating customers in the shared hosted demo. One prepared record is enough for
an interview walkthrough.

## 3. Show warehouse synchronization

Open the repository's **Actions → Snowflake synchronization** page. Point out the successful
scheduled or manual run and the scoped workflow:

- GitHub receives only the synchronization token;
- Snowflake credentials remain in Render;
- the application performs the controlled PostgreSQL-to-Snowflake copy;
- the Snowflake role has only the required warehouse, schema, and table grants.

Return to the dashboard and refresh to show the warehouse-backed metrics.

## 4. Explain the AI safety boundary

In **AI Analyst**, ask an aggregate question such as:

```text
Which spending category generates the most revenue?
```

Then explain that the model selects from approved aggregate tools and cannot query arbitrary SQL
or individual customer records. Mention the deterministic classifier, limited retries, durable
LangGraph checkpoints, and human review for sensitive requests.

Do not intentionally send requests containing real personal data or secrets.

## 5. Show engineering evidence

In GitHub, briefly show:

- the README architecture diagram;
- `src/loyalty_analytics/` layering;
- Alembic migrations;
- the 36-case evaluation dataset;
- CI quality and container jobs;
- the passing Snowflake workflow;
- test coverage above the enforced 85% threshold.

## Suggested screenshots

Capture these at desktop width after removing unrelated browser tabs and notifications:

1. Executive overview with the four KPI cards and charts
2. Administrator workspace showing empty forms, with no personal data
3. AI Analyst with one aggregate question and grounded response
4. GitHub Actions page showing green CI and Snowflake synchronization runs
5. Snowflake Snowsight showing table names or aggregate counts, never credentials or key material

Store selected images under `docs/images/` and link them from the README only after checking every
image for email addresses, tokens, account identifiers, private keys, and browser profile details.

## Closing statement

> This project demonstrates the full path from secure operational writes to warehouse analytics
> and constrained AI analysis, with automated quality gates, reproducible deployment, and
> production troubleshooting evidence.
