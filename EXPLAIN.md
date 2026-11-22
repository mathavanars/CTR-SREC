# ArthMitra project guide

This file explains the project in plain English. It will grow as later phases add files and pages.

## Project files

- `.gitignore` keeps private settings, databases, caches, and environment folders out of Git.
- `.env.example` shows the configuration names without storing real secrets.
- `requirements.txt` lists Python packages used by the backend.
- `README.md` explains what ArthMitra is and how to install and run it.

## Backend

- `backend/main.py` creates the FastAPI app and the first health-check route.
- `backend/tests/` is reserved for automated backend tests.
- `backend/calculators.py` performs every money calculation with Python `Decimal`.
- `backend/tests/test_calculators.py` checks SIP, lump sum, required SIP and health calculations.
- `backend/database.py` opens SQLite safely for each web request.
- `backend/models.py` stores users and one profile per user.
- `backend/auth.py` hashes passwords and validates JWT login tokens.
- `backend/schemas.py` validates account and profile input.
- `backend/data/investment_ideas.json` stores the ten learning cards, risk notes, assumptions, and quizzes.
- `backend/investment_ideas.py` scores ideas using the user's saved type, goals, monthly amount, and readiness.
- `backend/chat_tools.py` gives the coach real idea-match and monthly-split results.
- `backend/market_data.py` fetches, range-checks and caches public market figures for 24 hours.
- `backend/data/market_defaults.json` stores fallback figures; its bootstrap values are examples, not live quotes.
- `backend/suggest.py` makes goal-aware suggestions and separately calculates the low, expected and high cases for every part.
- `backend/suggestion_config.py` keeps risk bands, the equity risk premium, scenario offsets and stress shocks in one commented file.
- `backend/suggestion_config.py` also stores the simple monthly amount rules of thumb and steady-income factors.
- `backend/app_config.py` reads the shared `APP_CREDIT` and version from `frontend/app-config.json` for report data and PDFs.
- `frontend/bootstrap.js` loads that shared public config before starting the browser app, and fills the page author tag and common footer.

### `GET /api/health`

Purpose: confirm that the backend is running.

Sample request:

```text
GET /api/health
```

Sample response:

```json
{
  "status": "ok",
  "message": "ArthMitra backend is ready."
}
```

### `POST /auth/register`

Purpose: create one account and return a signed-in token.

Sample request:

```json
{"email": "demo@example.com", "password": "strongpassword"}
```

Sample response:

```json
{"access_token": "signed-jwt", "token_type": "bearer"}
```

### `POST /auth/login`

Purpose: check an email and password and return a signed-in token.

Sample request:

```json
{"email": "demo@example.com", "password": "strongpassword"}
```

Sample response:

```json
{"access_token": "signed-jwt", "token_type": "bearer"}
```

### `GET /profile`

Purpose: read the signed-in user's saved money profile. Send `Authorization: Bearer signed-jwt`.

Sample response:

```json
{
  "income": "30000",
  "expenses": "20000",
  "savings": "60000",
  "debts": [],
  "goals": []
}
```

### `PUT /profile`

Purpose: validate and save the signed-in user's money profile.

Sample request:

```json
{
  "income": "30000",
  "expenses": "20000",
  "savings": "60000",
  "debts": [{"name": "Loan", "amount": "200000", "interest_rate": "12", "emi": "5000"}],
  "goals": [{"name": "Home", "amount": "1000000", "years": 5}]
}
```

The response uses the same shape as `GET /profile`.

### Smart monthly amount

The calculator `suggest_monthly_amount(profile)` in `backend/calculators.py`
compares the amount the user wants, the amount that may fit the monthly budget,
and the amount needed for the nearest goal. It uses `Decimal` throughout. The
rule-of-thumb shares and steady, sometimes-changing, or irregular income
multipliers are in `backend/suggestion_config.py`.

When the emergency fund is below three months or any debt rate is above 15%,
the calculator recommends Rs 0 for investing and shows the suggested basics
amount instead. The returned result includes the three suggested ranges,
goal need, goal chance, whole-month goal timeline, budget breakdown, wanted
amount verdict, and flat versus step-up plan projections.

- `GET /smart-monthly-amount` calculates a fresh result for the signed-in user.
- `POST /smart-monthly-amount/preview` previews an income pattern or wanted amount without saving it.
- `PATCH /profile/investment-capacity` saves the user's income pattern and preferred amount.

The Step 4 form, dashboard, Profile page, report, and AI coach use the same
backend calculation. The optional yearly step-up is calculated month by month
and keeps separate return assumptions for each selected plan part.

The dashboard Smart monthly amount card lets the user compare Comfortable,
Recommended, Stretch, You want, and a custom amount. The values for the growth
charts, expense limit, goal chance, and room-left table all come from the
backend. `GET /smart-amount/growth` uses the caller's saved shares and calculates
each chosen part with its own Low, Middle, and High rates. If there is no saved
plan, the endpoint uses ArthMitra's goal-aware suggested split. It returns 30
year points, with the selected 1-to-30-year total and money earned.

```text
GET /smart-amount/growth?amount=4200&years=10
GET /smart-amount/growth?amount=0&years=10&expenses=16000
```

The optional `expenses` value is only a what-if preview. The response includes
the amount left after income, EMI, basics and expenses, rounded down to Rs 100;
it never saves the changed expenses. When there is no monthly surplus, the
response contains tips but no growth series. When the emergency fund is under
three months or debt is above 15%, the response shows the basics timeline and
does not return investment growth.

`PUT /smart-amount` saves a selected amount after the browser confirms it:

```json
{"choice":"recommended","amount":"4200"}
```

The choice can be `comfortable`, `recommended`, `stretch`, `want`, or `custom`.
All choices except `want` must be whole Rs 100 steps. Saving changes the plan's
monthly total and the profile's wanted amount, leaves the saved percentage
shares alone, and marks the plan for a re-check. Only the authenticated user's
profile and plan are queried.

The Future Outlook section of `GET /report/data` includes
`smart_amount_growth`. The AI coach calls the same calculation with the
`get_amount_growth` tool for questions such as “What if I invest Rs 3,000?”.
The Report PDF also includes the selected amount's 10-year result.

The exact developer credit is stored once as `APP_CREDIT` in
`frontend/app-config.json`. The browser bootstrap uses it for the HTML author
tag and shared footer; the backend reads the same file for the About/report
views and every PDF page. The visible text is **ArthMitra is developed by
CTR-SREC-HUB**.

The Goals page uses `PATCH /profile/goals` with `{"goals":[{"name":"Home","amount":"2000000","years":3}]}`; the Debts page uses `PATCH /profile/debts` with `{"debts":[{"name":"Loan","amount":"40000","interest_rate":"12","emi":"2000"}]}`. Each route replaces only its named list and leaves other profile fields and `onboarding_step` unchanged. The response includes the updated profile, readiness, health score, monthly money left, refreshed plan analysis, a save message, and a plan-review reminder when a saved plan exists. <!-- Explain the section-only profile updates and refreshed values. -->

### Monthly goal investment log

The Goals page has a separate monthly log for each goal. Use `GET /goals` to
read the signed-in user's goal IDs and start dates. Record an amount, including
zero for a skipped month, with `POST /goals/{goal_id}/logs`:

```json
{
  "month": "2026-11-01",
  "amount": "6000.00",
  "part_id": "index-sip",
  "note": "November contribution"
}
```

The selected month cannot be in the future or before the goal's start month.
If the user already has an active entry for that month, the API asks whether to
add another entry or edit one. Each saved amount and snapshot uses Decimal
arithmetic. Log creation, edits and soft deletes are stored in UTC; the browser
converts timestamps to the user's time zone for display.

- `GET /goals/{goal_id}/progress` calculates invested total, actual or estimated
  value, plan comparison, goal chance, catch-up amount, consistency and streak.
  Each saved plan part keeps its own assumed rate. The Goals page focuses on
  progress and logs, without investment charts.
- `GET /goals/{goal_id}/logs?month=11&year=2026&page=1` returns ten newest-first
  history rows and supports month and year filters.
- `PUT /logs/{log_id}` edits an entry and records old and new values in
  `log_history`.
- `DELETE /logs/{log_id}` marks a row as deleted without erasing its history.
  `POST /logs/{log_id}/undo` restores it during the ten-second undo window.
- `POST /goals/{goal_id}/value` saves a dated value from an investment app or
  statement. The newest value is used as the actual base, then later log
  entries are added with their separate plan-part rates.
- `GET /goals/{goal_id}/logs/export` downloads the full history as CSV.

Every query checks both the logged-in user and the goal or log owner. Another
user's IDs return 404. Monthly estimates, future values, and chances are
assumptions, not guarantees. <!-- Explain the security, history and estimate rules. -->

### `POST /risk-quiz`

Purpose: save seven 1-to-5 answers and calculate an investor type.

Sample request:

```json
{"answers": [3, 3, 3, 3, 3, 3, 3]}
```

Sample response:

```json
{
  "investor_type": "balanced",
  "score": 21,
  "explanation": "You accept some ups and downs and want a mix of growth and safety."
}
```

### `GET /readiness`

Purpose: show whether emergency savings, high-interest debt and savings rate are ready.

### `GET /asset-mix`

Purpose: return a starting allocation for the saved investor type. Returns are expected assumptions, never guarantees.

### `GET /market-snapshot` and `POST /market-snapshot/refresh`

Purpose: return the latest cached public market snapshot or request an immediate
refresh. Each market value has a source URL and fetched date. The backend checks
repo rate, CPI inflation, SBI one-year FD rate, PPF rate, 10-year government
bond yield, Nifty 50 P/E and its 10-year average, and one-year gold change. It
uses short HTTP timeouts, rejects values outside configured believable ranges,
and falls back to `backend/data/market_defaults.json` after fetch or validation
failures. A fallback response includes `stale: true` and
`Data may be outdated (last checked: date).`

The checked-in bootstrap figures are illustrative fallbacks whose original
values have not been independently verified. A deployment should refresh data
and review source parsers before using those values. The market summary is a
deterministic three-sentence explanation from stored figures; no LLM provides
numeric data.

### `GET /investment-ideas`

Purpose: return all ten learning cards with match scores, reasons and lock status. Cards sort by score; locked cards do not appear in the top picks.

Sample response shape:

```json
{
  "ideas": [
    {
      "id": "index-sip",
      "name": "Index fund SIP",
      "match_score": 80,
      "locked": false,
      "match_reason": "Fits your Balanced style. Your nearest goal is 5 years away."
    }
  ],
  "top_picks": [],
  "disclaimer": "Educational guidance only. Not licensed financial advice. Investments carry risk. Returns are not guaranteed."
}
```

### `GET /investment-ideas/{id}`

Purpose: return one idea's full learning details, including its example, pros, cons, starting steps and quiz.

Sample request:

```text
GET /investment-ideas/index-sip
```

### `POST /allocation-plan`

Purpose: return the educational seven-jar example used by the coach, or explain
which basics to fix first. The Growth projector page uses the saved-plan route
below instead.

Sample request:

```json
{"monthly_amount": "6000"}
```

Sample response shape:

```json
{
  "ready": true,
  "investor_type": "balanced",
  "monthly_amount": "6000.00",
  "total": "6000.00",
  "summary": "Your ₹6,000 each month, split into 7 jars.",
  "label": "Expected, not guaranteed"
}
```

A ready response also returns `totals.monthly`, `totals.five_year_middle`, and `totals.ten_year_middle`, each summed from its table rows by the backend with Decimal arithmetic. <!-- Explain that the backend supplies exact table totals. -->

Each jar also contains low, middle and high 5- and 10-year growth examples. Direct stocks are never part of this automatic split.

### `GET /plan/projector?years=10`

Purpose: calculate a projector view using only the signed-in user's saved plan
from `GET /plan`. Set `years` from 1 to 30. The response includes one row per
positive-share part, that part's saved share and monthly rupees, five- and
ten-year low/middle/high values, exact Decimal totals, and yearly combined
low/middle/high chart points. Growth is calculated part by part and then added;
the total row is the sum of the displayed rows. A user with no saved plan gets
`{"exists":false,"parts":[]}` so the page can offer a link to Step 4. <!-- Describe how the projector follows only the user's saved choices. -->

### `GET /health-score` and `POST /projection`

Purpose: show the saved profile's simple score or ask the backend for an estimated growth result.

Sample projection request:

```json
{"monthly_amount": "1800", "annual_rate": "12", "years": 10}
```

Sample response:

```json
{"monthly_amount": "1800", "annual_rate": "12", "years": "10", "future_value": "418210.34", "label": "Expected, not guaranteed"}
```

### `POST /chat`

Purpose: answer common money questions using the real `get_investment_ideas`,
`get_allocation_plan`, `get_market_snapshot`, and `explain_plan_choice` tools.
The coach can explain why a plan uses a given number of parts with stored market
data and source links. It will not recommend a specific stock.

Sample request:

```json
{"question": "Where should I invest?"}
```

## Five-step onboarding and investment plan

Every plan route below requires `Authorization: Bearer <token>`. The required
onboarding order is money details, risk quiz, investment choices, plan review,
then dashboard. Login resumes from the saved step. Until the plan is confirmed,
dashboard-only routes such as `/health-score`, `/readiness`, `/asset-mix`,
`/allocation-plan` and `/projection` return `409` with
`{"detail":"onboarding_incomplete"}`.

### `GET /onboarding/status`

Returns the next page and a safe monthly amount (income minus expenses and all
debt EMIs). Example before the money-details step:

```json
{
  "onboarding_step": 0,
  "step_number": 2,
  "next_page": "money-details",
  "complete": false,
  "safe_monthly_amount": null,
  "max_parts": 1
}
```

### `GET /plan/suggestion?monthly_amount=6000&tax_saving_80c=false`

After money details and the risk quiz, returns a goal-aware, data-driven plan.
The standard mixes are Conservative 20/40/10/30, Balanced 50/30/10/10 and
Aggressive 70/15/10/5 for equity/debt/gold/cash. Goals under three years cap
equity at 20%; goals under five years cap it at 50%. The response explains
accepted or skipped market tilts and reports if the selected short-goal limit
cannot fit the investor's usual risk band.

Part-count caps are 2 below ₹1,000, 3 below ₹3,000, 5 below ₹8,000 and 7 above
that. The actual plan may use fewer parts so each selected part is at least
₹500 and 10% of the total. If a smaller asset class cannot meet that minimum,
it is merged into a larger class and the reason is shown. A goal under three
years uses one safer goal jar. If emergency savings or high-interest debt needs
attention, basics jars come first and equity is paused.

The `tax_saving_80c` answer is saved with the plan. ELSS is only considered
after a "yes"; all three of Index, Equity Fund and ELSS are never combined
below ₹8,000 per month.

The response includes `monthly_amount`, `parts` (including names and exact
monthly amounts, each part's return assumptions and 5-/10-year scenarios),
`scenario_totals`, `stress_test`, `why_this_plan`, `basics`, `max_parts`,
`safe_monthly_amount`, `amount_over_safe`, `safe_amount_negative`,
`ready_for_investment`, and the assumptions disclaimer. Scenario totals add
each part's own growth rather than applying one average return.

`why_this_plan` includes a three-sentence market summary, `Data as of` date,
source links, the reason for the number of parts, each mix change, a stress
example, and the reminder to review every six months. Outcomes are assumptions,
not predictions or guarantees. Refresh data with `POST /market-snapshot/refresh`.

### `POST /plan/preview`

Previews changing slider shares, even when they do not yet add to 100%. The
response includes each part's estimated monthly amount, `shares_total`,
`valid_total` and `allocated_total`.

```json
{
  "monthly_amount": "6000",
  "parts": [{"idea_id": "fd-rd", "share": "75"}]
}
```

### `POST /plan` and `GET /plan`

Save choices once shares add to exactly 100%. The backend rejects duplicate,
unknown, locked or too-many ideas; a saved plan is marked stale until reviewed.

```json
{
  "monthly_amount": "6000",
  "tax_saving_80c": false,
  "parts": [
    {"idea_id": "index-sip", "share": "50"},
    {"idea_id": "fd-rd", "share": "50"}
  ]
}
```

Both routes return the saved plan shape:

```json
{
  "exists": true,
  "monthly_amount": "6000.00",
  "parts": [
    {"idea_id": "index-sip", "share": "50"},
    {"idea_id": "fd-rd", "share": "50"}
  ],
  "analysis": null,
  "tasks": [
    {"id": "task-index-sip", "idea_id": "index-sip", "title": "Part 1: Learn what index the fund follows.", "completed": false},
    {"id": "task-fd-rd", "idea_id": "fd-rd", "title": "Part 2: Compare rates with your bank.", "completed": false}
  ],
  "is_stale": true
}
```

### `POST /plan/analyze`

Calculates a 100-point score and grade across diversification, risk fit,
goal-time fit, affordability, and starting minimums. The response includes
`checks`, up to three actionable `top_fixes`, and per-part low/middle/high
growth examples for five and ten years. If a goal exists, it also includes
goal progress and options to invest more, take more time, or lower the goal.
Money values are JSON strings to preserve exact decimal amounts.

The response fields are `score`, `grade`, `weighted_risk`,
`weighted_average_return`, `monthly_amount`, `safe_monthly_amount`, `checks`,
`top_fixes`, `growth`, `goal`, and `label`.

### `POST /plan/apply-fix`

Applies a currently available fix from `top_fixes` and marks the analysis stale
so it can be reviewed again.

```json
{"fix_id": "affordability"}
```

If that fix is no longer available, the route returns `404`.
On success, the response contains the fix's `message` and updated `plan`.

### `GET /plan/compare`

Returns `your_plan`, fresh `your_analysis`, an idea-by-idea `suggested_plan`,
`suggested_analysis`, and a plain-language comparison `summary`. Decimal
analysis values use strings in this response too.

### `POST /plan/confirm`

Keep the user's choices with `"mine"` or replace them with ArthMitra's
suggestion using `"suggested"`. Either choice saves fresh analysis and completes
onboarding.

```json
{"choice": "mine"}
```

The response includes a completion `message`, `onboarding_step: 4`, and the
fresh `analysis`.

### `GET /plan/journey` and `PUT /plan/tasks/{task_id}`

The journey response contains where/how details for each selected idea,
growth examples, calm-investing rules, the goal and first-month checklist.
Mark one checklist task complete or incomplete with:

```json
{"completed": true}
```

The task response contains the updated `task`, `completed_tasks`, and
`task_count`. Task progress is saved per user. Editing the plan preserves
completed tasks whose idea remains in the plan.

### `POST /auth/change-password` and `POST /auth/logout`

Purpose: change a password after checking the old password, or confirm logout. The browser completes logout by deleting its JWT token.

Sample password-change request:

```json
{"old_password": "old-password", "new_password": "new-password", "confirm_password": "new-password"}
```

## Frontend

- `frontend/index.html` contains the first welcome screen.
- `frontend/styles.css` contains colors, spacing, and mobile-friendly layout styles.
- `frontend/app.js` runs sign-in, dashboard navigation, ideas, profile, goals, projector, reports and coach screens.

The first learning journey has five steps:

1. Login or register, including Demo mode.
2. Save income, expenses, savings, debt and goals.
3. Answer the 7-question risk quiz and see the investor type.
4. Choose a monthly amount, answer the 80C question, and choose plan parts;
   preview slider totals and monthly amounts. "Use ArthMitra's suggestion"
   uses the smart plan engine and sourced scenarios.
5. Review the plan analysis, compare with the suggestion, apply fixes if wanted,
   then confirm to open the dashboard.

After confirmation, the dashboard and investing journey show progress and
first-month tasks. The user can edit the plan and rerun analysis. Protected
pages check the token and onboarding status through the API. Logout asks for
confirmation and removes the browser token.

The smart plan calculations use `Decimal` in the backend. The user-selected
goal-safety priority wins if a short-goal equity cap conflicts with a risk band;
the response flags that exception instead of silently changing the goal cap.
For small amounts, the user-selected minimum-part priority wins: the planner
merges undersized classes and explains why it uses fewer parts.

## Reports and progress snapshots

`backend/report.py` builds the report from the signed-in user's saved records.
Every query for profiles, plans, snapshots, goals, debts, and investment logs
is scoped by `user_id`. Report URLs take only a period value and never expose
an account ID or email address.

The `progress_snapshots` table stores a UTC point-in-time summary: health and
plan scores, profile amounts, savings rate, debt-to-income, emergency-fund
months, debt and investment totals, current value, and each goal's chance.
Snapshots are written after profile, risk, plan, goal, debt, log, and plan-task
changes. The first report request in a UTC month makes that month's snapshot.
Legacy accounts get setup completion times from their saved profile and plan
records when the SQLite migration runs.

`GET /report/data?period=since_started` returns the full report JSON.
Supported periods are `last_month`, `last_3_months`, `last_6_months`, and
`since_started`. The earliest and latest saved snapshots in that period make
the past-versus-present comparison. All report responses set
`Cache-Control: no-store`; the JSON, PDF, and CSV routes require authentication.

The report reuses Decimal calculators for profile measures, goal progress,
debt payoff, and per-part low/middle/high growth. It never uses an average
return rate to create a plan total. Warnings are defined in the single
`WARNING_RULES` list in `backend/report.py`; each row includes its severity,
reason, and next step. Summary wording is fixed and is checked so any written
digits also exist in the report data.

`GET /report/pdf?period=...` builds an A4 PDF on the server. ReportLab lays out
the tables and sections, and Matplotlib draws the report charts as images.
The PDF includes the name and local date in its header, a page number, and the
learning disclaimer in each page footer. The endpoint is limited to five
downloads per user per minute. `GET /report/csv?period=...` downloads the
report's profile, chosen plan parts, goals, debts, and investment-log rows.
An account without a plan, goals, debts, or logs still receives an honest
report with empty-state notes.

## Safety

The footer always reminds users that ArthMitra is educational, not licensed financial advice, that investments carry risk, and that returns are not guaranteed.
