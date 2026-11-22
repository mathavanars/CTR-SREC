# ArthMitra

ArthMitra is an educational investment learning and planning assistant. It helps people learn where to invest, how to invest, how regular investing may grow money, and how to pursue profit realistically without guaranteed-return promises.

The app includes sign-in, a five-step onboarding flow, a customizable monthly
investment plan, Decimal-based plan analysis, a comparison with a suggested
plan, and a dashboard journey with saved first-month tasks. It also includes a
risk quiz, readiness checks, ten investment learning cards, and a growth
projector. The dashboard summarizes saved income, expenses, goals, debts and
calculator estimates. The GroqCloud AI coach answers questions using the signed-in
user's saved data. The Goals page also keeps a dated, auditable monthly investment log,
shows actual or clearly labeled estimated progress, and lets users download
their history. ArthMitra's suggested plan uses goal timing, investor type, and
dated public market figures. It shows low, expected, and high scenarios as
assumptions, not guarantees; it never predicts market returns.

## Install

1. Open a terminal in this project folder.
2. Create a Python environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
5. In `.env`, set a unique `JWT_SECRET` and your GroqCloud `LLM_API_KEY`.
   Keep `.env` private; never put real credentials in `.env.example` or commit them.
   `CORS_ORIGINS` must contain the frontend origins, separated by commas (for
   example `http://127.0.0.1:5500,http://localhost:5500`). If you test from another
   device, add the exact frontend origin using this computer's LAN IP and port
   `5500`.

## Run the app

Start the backend from the project root:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open these addresses:

- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`
- Frontend: start a separate static server:
  ```bash
  cd frontend
  python3 -m http.server 5500 --bind 0.0.0.0
  ```
  Then open `http://127.0.0.1:5500`.

To open ArthMitra from another device on the same Wi-Fi network, use:

- Frontend: `http://<this-computer-IP>:5500`
- Backend: `http://<this-computer-IP>:8000`

Both servers listen on all network interfaces so another device on the same trusted
network can connect. The frontend automatically sends API requests to port 8000 on
the current host name. Do not expose these development servers to the public internet.

## Test

```bash
python3 -m pytest
```

## Folder guide

- `backend/` contains the Python API, database, calculations, and idea-matching rules.
- `backend/data/investment_ideas.json` is the single source for the investment-card facts.
- `backend/market_data.py` fetches public figures with timeouts and validates them.
- `backend/data/market_defaults.json` keeps the last snapshot for source outages; its bootstrap entries are examples and may be outdated.
- `backend/suggest.py` builds goal-aware parts and per-part scenarios using Decimal.
- `backend/suggestion_config.py` holds the risk ranges, mix, stress shocks, and return offsets.
- `frontend/` contains the browser HTML, CSS, and JavaScript.
- `backend/tests/` contains automated backend tests.

After login, use the profile menu to edit money details, change theme or text mode, open Reports, or log out. The Reports page can print the report or download a backend-created PDF and CSV. Use the side menu on desktop and bottom menu on mobile.

On the Goals page, use **Update this month's investment** to save an amount or
record a skipped month. Progress uses backend Decimal calculations from those
saved entries, and any estimate is labeled as an assumption. Enter a value from
your app or statement to replace an estimated value with an actual snapshot.
Edits and deletions remain in history; a deleted row can be restored for ten
seconds. The dashboard reminds you after the fifth of the month when a goal has
not been logged. <!-- Explain what the user's new goal log does. -->

The Growth projector shows only positive-share parts from the saved plan. It
calculates each part separately on the backend, then adds the displayed rows
for the exact total. <!-- Explain how the saved-plan projector avoids unchosen ideas. -->

### Smart monthly amount

The Step 4 plan form, dashboard, Profile page, and report show a Decimal-based
monthly amount suggestion. It compares what you want to invest, what may fit
your monthly budget, and what your nearest goal needs. Income stability changes
the suggested ranges. If your emergency fund is under three months or you have
debt above 15% interest, the suggestion puts money toward those basics first.
The rules of thumb live in `backend/suggestion_config.py`.

Use `GET /smart-monthly-amount` for the signed-in user's current suggestion,
`POST /smart-monthly-amount/preview` to compare a wanted amount or income
pattern, and `PATCH /profile/investment-capacity` to save those preferences.
The API recalculates the result from the latest profile, debt, goal, and saved
plan data. Optional 10% yearly step-up projections are calculated month by
month, with each selected plan part using its own return assumption.

On the dashboard, choose Comfortable, Recommended, Stretch, You want, or Your
own amount to compare a monthly amount. The growth charts and comparison table
use the signed-in user's saved plan shares and separate Low, Middle, and High
rates for each part. If there is no saved plan, ArthMitra uses its suggested
split. The expense slider sends a temporary expense value to the backend and
does not edit the profile. **Use this amount** asks for confirmation, saves the
new monthly total without changing plan percentages, and marks the plan for a
re-check. The Growth projector then uses that new total.

`GET /smart-amount/growth?amount=4200&years=10` returns the 1-to-30-year
projection, nearest-goal estimate, and expense limits. Add an `expenses`
parameter for a temporary what-if preview. The Report's Future Outlook includes
the current saved amount result, and the AI coach uses the same calculation for
questions such as “What if I invest Rs 3,000?” A missing emergency fund or debt
above 15% sends the selected amount to basics; investment growth is hidden until
those basics are ready. Expected outcomes are not guarantees.

The app's one shared `APP_CREDIT` setting is in `frontend/app-config.json`.
It supplies the login and page footer, About page, report and PDF credit, and
the HTML author tag. **ArthMitra is developed by CTR-SREC-HUB**.

### Full money report

The Reports page reads all report numbers from `GET /report/data?period=...`.
It supports Since I started, Last month, Last 3 months, and Last 6 months.
Saved progress snapshots let the report compare the earliest and latest values
in the selected period. A report request also saves one snapshot per UTC month,
so a new account can still open a complete report before it has logs or a plan.
Times are stored in UTC and shown in Asia/Kolkata.

The report uses the signed-in user's saved profile, plan, goals, debts, and
investment logs. Each chosen plan part is calculated separately with Decimal
math. It shows low, middle, and high assumptions, not predictions or promises.
Warnings use one backend rule list. The report does not ask an AI to create
financial numbers or wording.

Use **Download PDF** for a real A4 PDF made by the backend with ReportLab and
Matplotlib charts, or **Download data (CSV)** for report values. The PDF has a
page number and the learning disclaimer on each page. The JSON, PDF, and CSV
responses use `Cache-Control: no-store`; PDF creation is rate-limited.

New accounts finish money details and the risk quiz before choosing plan parts.
The plan review checks diversification, risk fit, goal timing, affordability,
and starting minimums; users can compare or edit the plan before confirming.
Login resumes incomplete onboarding. See [EXPLAIN.md](./EXPLAIN.md) for all
onboarding and plan API examples.

The plan asks whether the user wants ELSS considered for section 80C. A "yes"
does not confirm tax eligibility; users should check current rules. When public
market pages cannot be read or their numbers fail range checks, the backend
uses the saved snapshot and displays an outdated-data warning with source links.
The checked-in bootstrap figures are illustrative fallback examples, not live
quotes. No LLM supplies market numbers or the market summary.

Educational guidance only. Not licensed financial advice. Investments carry risk. Returns are not guaranteed.
