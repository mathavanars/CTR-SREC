/** Run ArthMitra's signed-in dashboard and investment learning pages. */

const APP_CREDIT = window.APP_CONFIG.APP_CREDIT; // Read the one shared developer-credit setting.
const APP_VERSION = window.APP_CONFIG.APP_VERSION; // Read the version shown on the About page.
const isLocalNetworkHost = window.location.hostname.startsWith("192.168.");
const API_URL = (window.location.hostname === "localhost"
  || window.location.hostname === "127.0.0.1"
  || isLocalNetworkHost)
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin;
const app = document.getElementById("app");
const tokenKey = "arthmitra-token";
let token = localStorage.getItem(tokenKey) || "";
let userProfile = null;
let simpleMode = localStorage.getItem("arthmitra-mode") !== "detailed";
let currentPage = "dashboard";
let currentIdea = null;
let currentIdeas = [];
let ideaFilter = "all"; // Remember the selected risk or match filter.
let ideaSort = "match"; // Keep the selected idea sort order.
let ideaSearch = ""; // Keep the user's short idea search.
let smartAmountSuggestion = null; // Keep backend results while Step 4 moves between questions.
let smartAmountSelection = "recommended"; // Start the interactive card on the recommended choice.
let smartAmountCustom = null; // Keep the user's own amount while the card redraws.
let smartAmountYears = 10; // Keep the chosen growth time in one place.
let smartAmountTimer = null; // Debounce live amount and expense previews.
let smartExpenseTimer = null; // Keep the separate expense preview debounce independent.
let smartAmountRequestId = 0; // Ignore an older response after a newer choice was made.
let smartAmountNotice = ""; // Show the saved-amount message after the dashboard refreshes.
const chartsByCanvas = new Map();
let projectorYears = 10; // Keep the selected projector time range when its page refreshes.
let projectorScenario = "mid"; // Keep the selected growth case when its page refreshes.
let setupNotice = "";
let reviewChoice = "mine";
let planDraft = {
  monthlyAmount: "0",
  selectedIds: [],
  parts: [],
  maxParts: 1,
  suggestions: [],
  basics: [],
  taxSaving80c: false,
  suggestionDetails: null,
};
let planPreviewSequence = 0;
let sectionEditorDirty = false; // Track edits before a section form closes.
let profileSaveNotice = ""; // Show the last profile save message after refresh.
let goalLogDirty = false; // Track changes in a monthly log form before it closes.
let goalLogState = new Map(); // Keep each goal's filters, page and undo window.
let goalLogWarnings = new Map(); // Show non-blocking amount warnings after a save.
let reportPeriod = "since_started"; // Keep the report's selected date range.

window.addEventListener("beforeunload", (event) => { // Warn before leaving an edited section form.
  if (!sectionEditorDirty && !goalLogDirty) return; // Let safe page closes continue.
  event.preventDefault(); // Ask the browser to confirm leaving.
  event.returnValue = ""; // Show the browser's unsaved-change warning.
}); // Finish the browser-close warning.

// This function replaces only the chart on the same canvas.
function replaceChart(canvas, options) {
  const oldChart = chartsByCanvas.get(canvas.id);
  if (oldChart) oldChart.destroy();
  const chart = new Chart(canvas, options);
  chartsByCanvas.set(canvas.id, chart);
  return chart;
}

// This function clears every chart when the signed-in user logs out.
function destroyCharts() {
  chartsByCanvas.forEach((chart) => chart.destroy());
  chartsByCanvas.clear();
}

// This function protects saved or API-provided text before placing it into HTML.
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// This function formats money with the Indian numbering style.
function money(value) {
  const raw = String(value ?? "0");
  const negative = raw.startsWith("-");
  const [whole = "0", fraction = ""] = (negative ? raw.slice(1) : raw).split(".");
  const integer = whole.replace(/\D/g, "") || "0";
  const lastThree = integer.slice(-3);
  const leading = integer.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  const grouped = leading ? `${leading},${lastThree}` : lastThree;
  return `${negative ? "-" : ""}₹${grouped}.${(fraction + "00").slice(0, 2)}`;
}

function smartAmountMarkup(suggestion, interactive = false) { // Show backend amounts and optionally enable live choices.
  const barLabels = { expenses: "Expenses", emi: "EMI", basics: "Basics", invest: "Invest", cushion: "Cushion", free: "Free" }; // Give each bar section a short label.
  const barParts = Object.entries(suggestion.stacked_bar).map(([key, item]) => `
    <span class="amount-bar-part ${escapeHtml(key)}" style="width:${escapeHtml(item.percent)}%" title="${barLabels[key]}: ${money(item.amount)}"></span>
  `).join(""); // Finish the backend-sized bar parts.
  const barLegend = Object.entries(suggestion.stacked_bar).map(([key, item]) => `
    <span><i class="amount-legend ${escapeHtml(key)}"></i>${barLabels[key]} · ${money(item.amount)}</span>
  `).join(""); // Show the exact rupees beside every bar color.
  const goalNeed = suggestion.goal_need === null ? "Add a goal" : money(suggestion.goal_need); // Avoid a fake zero when no goal exists.
  const months = suggestion.months_to_goal_at_recommended === null
    ? "Not reached within 50 years at this amount"
    : `${escapeHtml(suggestion.months_to_goal_at_recommended)} months`; // Show the backend whole-month estimate.
  const fiveYearGrowth = suggestion.step_up.growth["5"]; // Read both backend growth cases.
  const tenYearGrowth = suggestion.step_up.growth["10"]; // Read the longer backend growth cases.
  const sliderMax = Math.max(500, Number(suggestion.custom_slider_max || 0)); // Keep the custom slider within the backend surplus.
  if (interactive && smartAmountCustom === null) smartAmountCustom = Math.max(500, Number(suggestion.recommended || 0)); // Start the own amount at a usable hundred-rupee step.
  const options = [
    ["comfortable", "Comfortable", suggestion.comfortable, "Easy to keep up."],
    ["recommended", "Recommended", suggestion.recommended, suggestion.ready_to_invest ? "Keeps room for surprises." : "Use this for your basics first."],
    ["stretch", "Stretch", suggestion.stretch, "Harder to keep up."],
    ["want", "You want", suggestion.wanted, "Your saved amount."],
    ["custom", "Your own amount", smartAmountCustom ?? 500, "Try a different amount."],
  ]; // Keep every comparison option tied to the exact backend amount.
  const amountOptions = interactive
    ? options.map(([key, label, amount, note]) => `
        <button type="button" class="smart-amount-option smart-amount-choice ${smartAmountSelection === key ? "selected" : ""}"
          role="radio" aria-checked="${smartAmountSelection === key}" tabindex="${smartAmountSelection === key ? "0" : "-1"}"
          data-smart-amount-choice="${key}">
          <span>${escapeHtml(label)}${smartAmountSelection === key ? '<span class="smart-amount-check" aria-label="Selected">✓</span>' : ""}</span>
          <strong>${money(amount)}</strong><small>${escapeHtml(note)}</small>
        </button>`).join("")
    : options.slice(0, 3).map(([, label, amount, note]) => `
        <article class="smart-amount-option ${label === "Recommended" ? "recommended" : ""}">
          <span>${escapeHtml(label)}</span><strong>${money(amount)}</strong><small>${escapeHtml(note)}</small>
        </article>`).join("");
  const interactiveControls = interactive ? `
    <div class="smart-amount-controls">
      <label for="smart-amount-custom">Try your own amount</label>
      <div class="smart-amount-custom-controls">
        <input id="smart-amount-custom-slider" type="range" min="500" max="${sliderMax}" step="100"
          value="${smartAmountCustom}" aria-label="Try your own monthly amount"
          ${Number(suggestion.can) < 500 ? "disabled" : ""} />
        <input id="smart-amount-custom" type="number" min="500" max="${sliderMax}" step="100"
          value="${smartAmountCustom}" inputmode="numeric" aria-label="Type your own monthly amount" />
      </div>
      <p id="smart-amount-current-selection" aria-live="polite"></p>
      <p id="smart-amount-warning" class="status hidden" role="status"></p>
      <p id="smart-amount-save-notice" class="status" role="status">${escapeHtml(smartAmountNotice)}</p>
      <label for="smart-amount-years">See growth over
        <input id="smart-amount-years" type="number" min="1" max="30" step="1" value="${smartAmountYears}" /> years
      </label>
      <button id="use-smart-amount" type="button">Use this amount</button>
    </div>
    <div id="smart-amount-results" aria-live="polite">
      <div class="loading smart-amount-skeleton" role="status">Loading your growth examples...</div>
    </div>
    <section class="smart-expense-card" aria-labelledby="smart-expense-title">
      <h3 id="smart-expense-title">Your monthly expense limit</h3>
      <div id="smart-expense-summary" aria-live="polite">
        <div class="loading smart-amount-skeleton" role="status">Checking your monthly room...</div>
      </div>
      <label for="smart-expense-slider">What if my expenses change?</label>
      <input id="smart-expense-slider" type="range" min="0" max="${escapeHtml(suggestion.income || 0)}" step="100"
        value="${escapeHtml(suggestion.expenses || 0)}" />
      <div id="smart-expense-preview" aria-live="polite"></div>
      <button id="update-smart-expenses" class="link-button" type="button">Update my expenses</button>
    </section>
    <p class="smart-growth-note">A smaller amount is easier to keep up. A bigger amount grows more but leaves less room for surprises.</p>
    <small>Expected, not guaranteed. These are possible outcomes, not promises.</small>
  ` : "";
  return `<section class="smart-amount-card dashboard-panel" aria-labelledby="smart-amount-title">
    <h2 id="smart-amount-title">Smart monthly amount</h2>
    <p>${escapeHtml(suggestion.plain_english)}</p>
    <div class="smart-amount-options" ${interactive ? 'role="radiogroup" aria-label="Choose a monthly amount"' : ""}>${amountOptions}</div>
    <div class="smart-amount-comparison">
      <div><span>You want</span><strong>${money(suggestion.wanted)}</strong><small class="status-chip ${suggestion.verdict.startsWith("Too high") ? "watch" : "good"}">${suggestion.verdict.startsWith("Too high") ? "!" : "✓"} ${escapeHtml(suggestion.verdict)}</small></div>
      <div><span>You can</span><strong>${money(suggestion.can)}</strong></div>
      <div><span>Your goal needs</span><strong>${goalNeed}</strong></div>
    </div>
    <div class="amount-gauge" role="img" aria-label="Comparison of wanted, available and goal-needed amounts">
      <span class="gauge-marker wanted" style="left:${escapeHtml(suggestion.gauge.wanted_percent)}%"></span>
      <span class="gauge-marker can" style="left:${escapeHtml(suggestion.gauge.can_percent)}%"></span>
      <span class="gauge-marker need" style="left:${escapeHtml(suggestion.gauge.need_percent)}%"></span>
    </div>
    <div class="gauge-legend"><span>Want</span><span>Can</span><span>Need</span></div>
    <p class="eyebrow">Where your monthly income goes</p>
    <div class="amount-stacked-bar" role="img" aria-label="Monthly income breakdown">${barParts}</div>
    <div class="amount-bar-legend">${barLegend}</div>
    <p>${suggestion.basics > 0
      ? `You are not ready to invest yet. Put ${money(suggestion.basics)} toward ${escapeHtml(suggestion.basics_priority)} first. If you put it toward your emergency fund, it may take ${escapeHtml(suggestion.emergency_fund_months_at_basics)} months, ignoring interest.`
      : suggestion.goal_need !== null
        ? `At the recommended amount, your goal pace is ${escapeHtml(suggestion.goal_chance_at_recommended)}%. It may take ${months} to reach this goal.`
        : "Add a goal to see the monthly amount it may need."}</p>
    ${suggestion.tips.length ? `<ul class="amount-tips">${suggestion.tips.map((tip) => `<li>${escapeHtml(tip)}</li>`).join("")}</ul>` : ""}
    <details class="step-up-details">
      <summary>Optional: raise the amount by 10% each year</summary>
      <label class="step-up-switch"><input class="smart-step-up" type="checkbox" /> Show the step-up example</label>
      <p class="smart-growth-output"
        data-flat-five="${escapeHtml(fiveYearGrowth.flat)}" data-step-five="${escapeHtml(fiveYearGrowth.step_up)}"
        data-flat-ten="${escapeHtml(tenYearGrowth.flat)}" data-step-ten="${escapeHtml(tenYearGrowth.step_up)}">
        Without step-up: 5 years ${money(fiveYearGrowth.flat)} · 10 years ${money(tenYearGrowth.flat)}.
      </p>
    </details>
    ${interactive ? interactiveControls : ""}
    <small>Last calculated ${escapeHtml(suggestion.calculated_at_local)} · Estimates are assumptions, not guarantees.</small>
  </section>`; // Finish the simple monthly amount card.
} // Finish the smart amount display helper.

function bindSmartAmountToggles() { // Let users compare flat and step-up amounts from backend results.
  document.querySelectorAll(".smart-step-up").forEach((toggle) => { // Connect each card's optional switch.
    toggle.addEventListener("change", () => { // Change only which backend totals are shown.
      const output = toggle.closest(".step-up-details").querySelector(".smart-growth-output"); // Find this card's growth line.
      const label = toggle.checked ? "With 10% step-up" : "Without step-up"; // Keep the selected case clear.
      const five = toggle.checked ? output.dataset.stepFive : output.dataset.flatFive; // Read the matching five-year result.
      const ten = toggle.checked ? output.dataset.stepTen : output.dataset.flatTen; // Read the matching ten-year result.
      output.textContent = `${label}: 5 years ${money(five)} · 10 years ${money(ten)}.`; // Display backend amounts without recalculating.
    }); // Finish one optional switch.
  }); // Finish all amount cards.
} // Finish smart amount switch binding.

function smartAmountChoices(suggestion) { // Keep the five selectable amounts in the same order as the card.
  return [
    { key: "comfortable", label: "Comfortable", amount: String(suggestion.comfortable) },
    { key: "recommended", label: "Recommended", amount: String(suggestion.recommended) },
    { key: "stretch", label: "Stretch", amount: String(suggestion.stretch) },
    { key: "want", label: "You want", amount: String(suggestion.wanted) },
    { key: "custom", label: "Your own amount", amount: String(smartAmountCustom ?? 500) },
  ];
}

function selectedSmartAmount(suggestion) { // Read the amount from the selected backend option or own-amount box.
  return smartAmountChoices(suggestion).find((choice) => choice.key === smartAmountSelection);
}

function updateSmartAmountCard(suggestion) { // Refresh radio checks, warnings and the selected amount label.
  const choice = selectedSmartAmount(suggestion);
  document.querySelectorAll("[data-smart-amount-choice]").forEach((button) => {
    const selected = button.dataset.smartAmountChoice === smartAmountSelection;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-checked", String(selected));
    button.tabIndex = selected ? 0 : -1;
    const check = button.querySelector(".smart-amount-check");
    if (selected && !check) {
      button.querySelector("span").insertAdjacentHTML("beforeend", '<span class="smart-amount-check" aria-label="Selected">✓</span>');
    } else if (!selected && check) {
      check.remove();
    }
  });
  document.getElementById("smart-amount-current-selection").textContent =
    `Selected: ${choice.label} · ${money(choice.amount)} each month`;
  const warning = document.getElementById("smart-amount-warning");
  const overSurplus = Number(choice.amount) > Number(suggestion.can);
  warning.classList.toggle("hidden", !overSurplus);
  warning.textContent = overSurplus ? "This is more than you have left each month." : "";
}

function smartAmountLoading() { // Keep the page responsive while the backend calculates new amounts.
  return `<div class="loading smart-amount-skeleton" role="status">Recalculating your examples...</div>`;
}

function drawSmartAmountCharts(selected, rows) { // Draw every growth line from backend projection points.
  const years = selected.series.map((point) => point.year);
  replaceChart(document.getElementById("smart-amount-growth-chart"), {
    type: "line",
    data: {
      labels: years,
      datasets: [
        { label: "Low", data: selected.series.map((point) => Number(point.low)), borderColor: "#D97706", tension: 0.2 },
        { label: "Middle", data: selected.series.map((point) => Number(point.mid)), borderColor: "#2563EB", borderWidth: 3, tension: 0.2 },
        { label: "High", data: selected.series.map((point) => Number(point.high)), borderColor: "#10B981", tension: 0.2 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { callback: (value) => money(value) } } } },
  });
  const colors = ["#2563EB", "#10B981", "#D97706", "#7C3AED", "#0F766E"];
  replaceChart(document.getElementById("smart-amount-options-chart"), {
    type: "line",
    data: {
      labels: years,
      datasets: rows.map((row, index) => ({
        label: row.label,
        data: row.result.series.map((point) => Number(point.mid)),
        borderColor: colors[index],
        tension: 0.2,
      })),
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { callback: (value) => money(value) } } } },
  });
}

function renderSmartAmountResults(suggestion, results) { // Show selected growth, all comparison rows and expense limits.
  const selectedChoice = selectedSmartAmount(suggestion);
  const selected = results[selectedChoice.key];
  const container = document.getElementById("smart-amount-results");
  const options = smartAmountChoices(suggestion);
  const selectedIndex = options.findIndex((choice) => choice.key === selectedChoice.key);
  const room = selected.expense_limit.room_left;
  const roomText = Number(room) < 0
    ? `<strong class="expense-over">⚠ Over by ${money(selected.expense_limit.over_by)}</strong>`
    : money(room);
  const expenseLimit = selected.expense_limit;
  const tips = selected.tips.length
    ? `<ul class="amount-tips">${selected.tips.map((tip) => `<li>${escapeHtml(tip)}</li>`).join("")}</ul>`
    : "";
  const unavailableRows = options.map((choice, index) => {
    const result = results[choice.key];
    const rowRoom = Number(result.expense_limit.room_left) < 0
      ? `<strong class="expense-over">⚠ Over by ${money(result.expense_limit.over_by)}</strong>`
      : money(result.expense_limit.room_left);
    return `<tr class="${index === selectedIndex ? "selected" : ""}">
      <th scope="row">${escapeHtml(choice.label)}</th><td>${money(choice.amount)}</td>
      <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td>
      <td>${money(result.expense_limit.highest_expenses_allowed)}</td><td>${rowRoom}</td>
    </tr>`;
  }).join("");
  const unavailableTable = `<div class="table-scroll"><table class="allocation-table smart-amount-table">
    <thead><tr><th>Option</th><th>Monthly amount</th><th>Invested in ${selected.years} years</th><th>Low</th><th>Middle</th><th>High</th><th>Goal chance</th><th>Years to reach goal</th><th>Highest expenses allowed</th><th>Room left</th></tr></thead>
    <tbody>${unavailableRows}</tbody></table></div>`;
  const expenseText = `<p>To invest ${money(expenseLimit.monthly_amount)} each month, keep your monthly expenses under ${money(expenseLimit.highest_expenses_allowed)}. Your expenses now: ${money(expenseLimit.current_expenses)}. Room left: ${roomText}.</p>
    <p>Safer expense limit after your cushion: <strong>${money(expenseLimit.safe_expense_limit)}</strong>.</p>${tips}`;
  let growthContent = "";
  if (selected.mode === "no_surplus") {
    growthContent = `<p class="status" role="status">${escapeHtml(selected.message)}</p>${unavailableTable}`;
  } else if (selected.mode === "basics") {
    const emergency = selected.basics.emergency_fund_months === null
      ? "Add a monthly amount to estimate the timeline."
      : `${escapeHtml(selected.basics.emergency_fund_months)} months to reach 3 months of expenses.`;
    const debt = selected.basics.debt
      ? `<p>With extra debt payments, you could be debt-free in ${escapeHtml(selected.basics.debt.months_with_extra ?? "—")} months and save about ${selected.basics.debt.interest_saved === null ? "not available" : money(selected.basics.debt.interest_saved)} interest.</p>`
      : "";
    growthContent = `<p class="status" role="status">${escapeHtml(selected.message)}</p>
      <p>Emergency fund: ${emergency}</p>${debt}
      <p>Investment growth is hidden while this amount goes to money basics.</p>${unavailableTable}`;
  } else {
    const total = selected.totals;
    const tableRows = options.map((choice, index) => {
      const result = results[choice.key];
      const rowGrowth = result.mode === "growth" && result.totals;
      const goalChance = result.goal ? `${escapeHtml(result.goal.goal_chance)}%` : "—";
      const yearsToGoal = result.goal?.years_to_reach === null || !result.goal
        ? "—"
        : `${escapeHtml(result.goal.years_to_reach)} years`;
      const rowRoom = Number(result.expense_limit.room_left) < 0
        ? `<strong class="expense-over">⚠ Over by ${money(result.expense_limit.over_by)}</strong>`
        : money(result.expense_limit.room_left);
      return `<tr class="${index === selectedIndex ? "selected" : ""}">
        <th scope="row">${escapeHtml(choice.label)}</th><td>${money(choice.amount)}</td>
        <td>${rowGrowth ? money(rowGrowth.invested) : "—"}</td>
        <td>${rowGrowth ? money(rowGrowth.low) : "—"}</td>
        <td>${rowGrowth ? money(rowGrowth.mid) : "—"}</td>
        <td>${rowGrowth ? money(rowGrowth.high) : "—"}</td>
        <td>${goalChance}</td><td>${yearsToGoal}</td>
        <td>${money(result.expense_limit.highest_expenses_allowed)}</td><td>${rowRoom}</td>
      </tr>`;
    }).join("");
    growthContent = `<p class="smart-growth-headline">If you invest ${money(selected.amount)} each month for ${selected.years} years, you could have about ${money(total.mid)} (middle case). You put in ${money(total.invested)}.</p>
      <div class="smart-growth-charts">
        <div class="chart-wrap"><h3>Your possible growth</h3><canvas id="smart-amount-growth-chart" aria-label="Low, middle and high possible growth"></canvas></div>
        <div class="chart-wrap"><h3>Compare all five amounts</h3><canvas id="smart-amount-options-chart" aria-label="Middle growth for all five amount choices"></canvas></div>
      </div>
      <div class="table-scroll"><table class="allocation-table smart-amount-table">
        <thead><tr><th>Option</th><th>Monthly amount</th><th>Invested in ${selected.years} years</th><th>Low</th><th><span title="The middle case is one possible example, not a promise.">Middle ?</span></th><th>High</th><th><span title="A simple comparison with your goal target, not a real-world probability.">Goal chance ?</span></th><th>Years to reach goal</th><th><span title="The most you can spend after EMI, basics and this selected amount.">Highest expenses allowed ?</span></th><th><span title="The amount left between your current expenses and the highest limit.">Room left ?</span></th></tr></thead>
        <tbody>${tableRows}</tbody>
      </table></div>
      `;
  }
  container.innerHTML = `${growthContent}<small>Last calculated ${escapeHtml(selected.calculated_at_local)}.</small>`;
  if (selected.mode === "growth") {
    drawSmartAmountCharts(selected, options.map((choice) => ({
      label: choice.label,
      result: results[choice.key],
    })));
  } else {
    ["smart-amount-growth-chart", "smart-amount-options-chart"].forEach((id) => {
      chartsByCanvas.get(id)?.destroy();
      chartsByCanvas.delete(id);
    });
  }
  document.getElementById("smart-expense-summary").innerHTML = expenseText;
}

async function loadSmartAmountResults(suggestion) { // Fetch every option from the signed-in user's backend.
  const requestId = ++smartAmountRequestId;
  const choices = smartAmountChoices(suggestion);
  const responses = await Promise.all(choices.map(async (choice) => {
    const query = new URLSearchParams({
      amount: choice.amount,
      years: String(smartAmountYears),
    });
    const result = await apiRequest(`/smart-amount/growth?${query}`, { cache: "no-store" });
    return [choice.key, result];
  }));
  if (requestId !== smartAmountRequestId) return;
  const results = Object.fromEntries(responses);
  renderSmartAmountResults(suggestion, results);
  renderSmartExpensePreview(suggestion, results[smartAmountSelection]);
}

function renderSmartExpensePreview(suggestion, result) { // Show what changes when only the expense slider moves.
  const target = document.getElementById("smart-expense-preview");
  if (result.mode !== "growth") {
    chartsByCanvas.get("smart-expense-growth-chart")?.destroy();
    chartsByCanvas.delete("smart-expense-growth-chart");
    target.innerHTML = `<p>${escapeHtml(result.message || "This amount goes to your money basics first.")}</p>`;
    return;
  }
  const amount = result.amount;
  const middle = result.totals.mid;
  target.innerHTML = `<p>With monthly expenses of ${money(result.expense_limit.current_expenses)}, you could invest about ${money(amount)} each month. In ${smartAmountYears} years, the middle case is about ${money(middle)}.</p>
    <div class="chart-wrap smart-expense-chart"><canvas id="smart-expense-growth-chart" aria-label="Possible middle growth after changing expenses"></canvas></div>`;
  replaceChart(document.getElementById("smart-expense-growth-chart"), {
    type: "line",
    data: {
      labels: result.series.map((point) => point.year),
      datasets: [{ label: "Middle case", data: result.series.map((point) => Number(point.mid)), borderColor: "#2563EB", tension: 0.2 }],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { callback: (value) => money(value) } } } },
  });
  if (Number(amount) > Number(suggestion.can)) {
    target.insertAdjacentHTML("beforeend", '<p class="status">This is more than your usual monthly surplus.</p>');
  }
}

function scheduleSmartAmountRefresh(suggestion) { // Wait briefly so slider movement makes one backend request.
  clearTimeout(smartAmountTimer);
  document.getElementById("smart-amount-results").innerHTML = smartAmountLoading();
  smartAmountTimer = window.setTimeout(async () => {
    try {
      await loadSmartAmountResults(suggestion);
    } catch (error) {
      if (smartAmountRequestId > 0) {
        document.getElementById("smart-amount-results").innerHTML =
          `<p class="status problem" role="alert">Growth could not load: ${escapeHtml(error.message)}</p>`;
      }
    }
  }, 300);
}

function bindSmartAmountCard(suggestion) { // Connect radio choices, sliders, confirmation and live results.
  const keys = smartAmountChoices(suggestion).map((choice) => choice.key);
  const customInput = document.getElementById("smart-amount-custom");
  const customSlider = document.getElementById("smart-amount-custom-slider");
  document.querySelectorAll("[data-smart-amount-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      smartAmountSelection = button.dataset.smartAmountChoice;
      updateSmartAmountCard(suggestion);
      scheduleSmartAmountRefresh(suggestion);
    });
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      const currentIndex = keys.indexOf(button.dataset.smartAmountChoice);
      const step = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
      const next = keys[(currentIndex + step + keys.length) % keys.length];
      document.querySelector(`[data-smart-amount-choice="${next}"]`).focus();
      smartAmountSelection = next;
      updateSmartAmountCard(suggestion);
      scheduleSmartAmountRefresh(suggestion);
    });
  });
  customSlider.addEventListener("input", () => {
    smartAmountCustom = customSlider.value;
    customInput.value = smartAmountCustom;
    smartAmountSelection = "custom";
    updateSmartAmountCard(suggestion);
    scheduleSmartAmountRefresh(suggestion);
  });
  customInput.addEventListener("input", () => {
    if (customInput.value === "") return;
    smartAmountCustom = customInput.value;
    customSlider.value = String(Math.min(Number(customSlider.max), Math.max(500, Number(smartAmountCustom))));
    smartAmountSelection = "custom";
    updateSmartAmountCard(suggestion);
    scheduleSmartAmountRefresh(suggestion);
  });
  document.getElementById("smart-amount-years").addEventListener("input", (event) => {
    const years = Number(event.currentTarget.value);
    if (!Number.isInteger(years) || years < 1 || years > 30) return;
    smartAmountYears = years;
    scheduleSmartAmountRefresh(suggestion);
    const expense = document.getElementById("smart-expense-slider").value;
    scheduleSmartExpensePreview(suggestion, expense);
  });
  document.getElementById("use-smart-amount").addEventListener("click", async () => {
    const choice = selectedSmartAmount(suggestion);
    if (!window.confirm(`Use ${money(choice.amount)} as your monthly amount? Your saved plan will need a re-check.`)) return;
    const button = document.getElementById("use-smart-amount");
    const notice = document.getElementById("smart-amount-save-notice");
    button.disabled = true;
    notice.textContent = "Saving your monthly amount...";
    try {
      const saved = await apiRequest("/smart-amount", {
        method: "PUT",
        body: JSON.stringify({ amount: choice.amount, choice: choice.key }),
      });
      smartAmountNotice = saved.message;
      await showDashboard();
      smartAmountNotice = "";
    } catch (error) {
      button.disabled = false;
      notice.textContent = `Your amount was not saved: ${error.message}`;
    }
  });
  const expenseSlider = document.getElementById("smart-expense-slider");
  expenseSlider.addEventListener("input", () => scheduleSmartExpensePreview(suggestion, expenseSlider.value));
  document.getElementById("update-smart-expenses").addEventListener("click", () => navigate("edit-profile"));
  updateSmartAmountCard(suggestion);
  loadSmartAmountResults(suggestion).catch((error) => {
    document.getElementById("smart-amount-results").innerHTML =
      `<p class="status problem" role="alert">Growth could not load: ${escapeHtml(error.message)}</p>`;
  });
}

function scheduleSmartExpensePreview(suggestion, expenses) { // Debounce expense-only previews without saving the profile.
  clearTimeout(smartExpenseTimer);
  document.getElementById("smart-expense-preview").innerHTML =
    `<div class="loading smart-amount-skeleton" role="status">Checking the new expense amount...</div>`;
  smartExpenseTimer = window.setTimeout(async () => {
    try {
      const query = new URLSearchParams({
        amount: "0",
        years: String(smartAmountYears),
        expenses: String(expenses),
      });
      const result = await apiRequest(`/smart-amount/growth?${query}`, { cache: "no-store" });
      renderSmartExpensePreview(suggestion, result);
    } catch (error) {
      document.getElementById("smart-expense-preview").innerHTML =
        `<p class="status problem" role="alert">Expense preview could not load: ${escapeHtml(error.message)}</p>`;
    }
  }, 300);
}

// This function displays the current step in the five-step setup.
function onboardingProgress(step, title) {
  const message = setupNotice
    ? `<p class="status" role="status">${escapeHtml(setupNotice)}</p>`
    : "";
  setupNotice = "";
  return `<div class="onboarding-progress">
    <p><strong>Step ${step} of 5</strong> · ${escapeHtml(title)}</p>
    <div class="progress" role="progressbar" aria-valuenow="${step}" aria-valuemin="1" aria-valuemax="5">
      <div class="progress-bar" style="width:${step * 20}%"></div>
    </div>${message}
  </div>`;
}

// This function sends a request and turns API errors into clear messages.
async function apiRequest(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }
  if (!response.ok) {
    if (response.status === 401 && token && !path.startsWith("/auth/login")) {
      handleExpiredSession();
    }
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(" ")
      : data.detail;
    throw new Error(detail || "Please try again.");
  }
  return data;
}

// This function clears an expired sign-in and returns the user to login.
function handleExpiredSession() {
  token = "";
  userProfile = null;
  localStorage.removeItem(tokenKey);
  localStorage.removeItem("arthmitra-dashboard-visited");
  history.replaceState({}, "", "#login");
  renderLogin("Your session ended for safety. Please log in again.");
}

// This function switches the header and navigation between public and signed-in mode.
function setSignedInLayout(signedIn) {
  document.getElementById("demo-button").classList.toggle("hidden", signedIn);
  document.getElementById("avatar-button").classList.toggle("hidden", !signedIn);
  document.getElementById("side-nav").classList.toggle("hidden", !signedIn);
  document.getElementById("mobile-nav").classList.toggle("hidden", !signedIn);
  document.getElementById("sidebar-toggle").classList.toggle("hidden", !signedIn); // Show the desktop collapse control only after login.
  app.classList.toggle("authenticated", signedIn);
  if (signedIn && userProfile?.email) {
    document.getElementById("avatar-button").textContent =
      userProfile.email.trim().charAt(0).toUpperCase();
  }
}

// This function displays the login and registration form.
function renderLogin(message = "") {
  setSignedInLayout(false);
  document.getElementById("page-title").textContent = "Learn to invest";
  document.getElementById("profile-menu").classList.add("hidden");
  app.innerHTML = `
    <section class="card welcome-card">
      <p class="eyebrow">AI investment learning assistant</p>
      ${onboardingProgress(1, "Account")}
      <h1>Make a calm, clear money plan</h1>
      <p>Learn where to invest, how to invest, and how regular saving may grow.</p>
      <p class="app-credit">${escapeHtml(APP_CREDIT)}</p> <!-- Show the app credit on login and register. -->
      <div class="tabs" aria-label="Account choice">
        <button class="tab active" id="login-tab" type="button">Login</button>
        <button class="tab" id="register-tab" type="button">Register</button>
      </div>
      <form id="auth-form" class="form-grid">
        <label>Email
          <input id="email" type="email" autocomplete="email" required />
        </label>
        <label>Password
          <input id="password" type="password" autocomplete="current-password" minlength="8" required />
        </label>
        <button id="auth-submit" type="submit">Login</button>
      </form>
      <p id="auth-status" class="status" role="status">${escapeHtml(message)}</p>
    </section>
  `;
  document.getElementById("login-tab").addEventListener("click", () => setAuthMode("login"));
  document.getElementById("register-tab").addEventListener("click", () => setAuthMode("register"));
  document.getElementById("auth-form").addEventListener("submit", authenticate);
}

// This function changes the login form into register mode or back again.
function setAuthMode(mode) {
  document.getElementById("login-tab").classList.toggle("active", mode === "login");
  document.getElementById("register-tab").classList.toggle("active", mode === "register");
  document.getElementById("auth-submit").textContent =
    mode === "login" ? "Login" : "Create account";
  document.getElementById("password").autocomplete =
    mode === "login" ? "current-password" : "new-password";
  document.getElementById("auth-form").dataset.mode = mode;
}

// This function signs the user in and verifies the token before showing the app.
async function authenticate(event) {
  event.preventDefault();
  const mode = event.currentTarget.dataset.mode || "login";
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  try {
    const result = await apiRequest(`/auth/${mode}`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    token = result.access_token;
    localStorage.removeItem("arthmitra-dashboard-visited");
    localStorage.setItem(tokenKey, token);
    await loadProfile();
    const onboarding = await apiRequest("/onboarding/status");
    navigate(mode === "register" || !onboarding.complete ? onboarding.next_page : "dashboard", false);
  } catch (error) {
    const status = document.getElementById("auth-status");
    if (status) status.textContent = error.message;
  }
}

// This function retrieves profile details and checks that the saved token is valid.
async function loadProfile() {
  userProfile = await apiRequest("/profile");
  setSignedInLayout(true);
}

// This function changes the current app page and browser address.
async function navigate(page, push = true) {
  if ((sectionEditorDirty || goalLogDirty) && !window.confirm("You have unsaved changes. Leave without saving?")) { // Ask before leaving an edited form.
    if (routeName() !== currentPage) history.replaceState({}, "", `#${currentPage}`); // Keep the address on the open editor page.
    return; // Leave the unsaved form open.
  } // Finish the unsaved navigation check.
  sectionEditorDirty = false; // Clear the warning after the user chooses to leave.
  goalLogDirty = false; // Clear the log warning after the user chooses to leave.
  if (!token && page !== "login") {
    history.replaceState({}, "", "#login");
    renderLogin();
    return;
  }
  if (token && page !== "login") {
    try {
      await loadProfile();
    } catch (error) {
      if (!token) return;
      renderRetry("We could not check your sign-in", error.message, () => navigate(page, false));
      return;
    }
  }
  if (["money-details", "edit-profile", "goals", "debts", "investment-choices", "plan-review", "projector"].includes(page)) {
    localStorage.removeItem("arthmitra-dashboard-visited");
  }
  currentPage = page;
  if (push) history.pushState({ page }, "", `#${page}`);
  document.getElementById("page-title").textContent = pageTitles[page] || "ArthMitra";
  document.querySelectorAll("[data-page]").forEach((button) => {
    button.classList.toggle("active", button.dataset.page === page);
  });
  document.getElementById("mobile-more-menu").classList.add("hidden");
  document.getElementById("mobile-more").setAttribute("aria-expanded", "false");
  renderPage(page);
}

const pageTitles = {
  dashboard: "Home",
  "money-details": "Money details",
  "investment-choices": "Investment choices",
  "plan-review": "Review and plan",
  ideas: "Investment ideas",
  projector: "Growth projector",
  goals: "Goals",
  debts: "Debts",
  learn: "Learn",
  coach: "AI coach",
  reports: "Reports",
  journey: "Your investing journey",
  profile: "My profile",
  "edit-profile": "Edit money details",
  "retake-quiz": "Retake risk quiz",
  about: "About ArthMitra",
};

const pageDescriptions = { // Keep the short page explanations in one readable map.
  login: "Learn about money and make a calm plan.",
  dashboard: "See your money picture and next steps.",
  "money-details": "Add the details that shape your plan.",
  "investment-choices": "Choose the monthly amount and investment parts.",
  "plan-review": "Check your plan before you confirm it.",
  ideas: "Compare learning ideas by risk and fit.",
  projector: "See possible growth from your chosen plan.",
  goals: "Track how close you are to each goal.",
  debts: "Review balances, rates and monthly payments.",
  learn: "Build money skills one small lesson at a time.",
  coach: "Ask a question using your saved numbers.",
  reports: "Read a full report based on your saved details.",
  journey: "Follow your first steps into investing.",
  profile: "Check and update your personal details.",
  "edit-profile": "Update the money details behind your plan.",
  "retake-quiz": "Review how comfortable you feel with risk.",
  about: "Learn who made ArthMitra and what it can do.",
}; // Finish the one-line page descriptions.

function updatePageDescription() { // Keep the top page heading paired with its short explanation.
  const page = token ? currentPage : "login"; // Use the login description before sign-in.
  document.getElementById("page-description").textContent = pageDescriptions[page] || ""; // Show a short, plain-English line.
} // Finish the page description update.

const pageHeaderObserver = new MutationObserver(updatePageDescription); // Follow existing title updates across every page.
pageHeaderObserver.observe(document.getElementById("page-title"), { childList: true, characterData: true, subtree: true }); // Refresh the description when old page code changes the title.

// This function sends the user to the page chosen in the desktop or mobile menu.
function handlePageNavigation(event) {
  const button = event.target.closest("[data-page]");
  if (button) navigate(button.dataset.page);
}

// This function chooses the correct screen for the requested page.
async function renderPage(page) {
  try {
    const result = await window.guard(page);
    if (!result.allowed) {
      if (!result.authenticated) {
        handleExpiredSession();
        return;
      }
      setupNotice = result.message;
      currentPage = result.nextPage;
      history.replaceState({}, "", `#${result.nextPage}`);
      document.getElementById("page-title").textContent =
        pageTitles[result.nextPage] || "ArthMitra";
      await renderPage(result.nextPage);
      return;
    }
  } catch (error) {
    renderRetry("We could not check your setup", error.message, () => renderPage(page));
    return;
  }
  if (page === "ideas") return showIdeas();
  if (page === "profile") return showMyProfile();
  if (page === "edit-profile" || page === "money-details") return showMoneyDetails();
  if (page === "retake-quiz") return showRetakeQuiz();
  if (page === "investment-choices") return showInvestmentChoices();
  if (page === "plan-review") return showPlanReview();
  if (page === "journey") return showInvestmentJourney();
  if (page === "projector") return showProjector();
  if (page === "goals") return showGoals();
  if (page === "debts") return showDebts();
  if (page === "learn") return showLearn();
  if (page === "coach") {
    if (localStorage.getItem("arthmitra-dashboard-visited") !== "true") {
      currentPage = "dashboard";
      history.replaceState({}, "", "#dashboard");
      return showDashboard();
    }
    return showCoach();
  }
  if (page === "reports") return showReports();
  if (page === "about") return showAbout();
  return showDashboard();
}

// This function displays loading cards while dashboard information is collected.
function showDashboardLoading() {
  app.innerHTML = `
    <section class="card">
      <div class="loading" role="status" aria-label="Loading dashboard"></div>
      <p>Getting your money picture ready...</p>
    </section>
  `;
}

// This function loads the persisted calculator results for the dashboard.
async function showDashboard() {
  showDashboardLoading();
  try {
    await loadProfile();
    const data = await apiRequest("/dashboard", { cache: "no-store" });
    renderDashboard(data);
    localStorage.setItem("arthmitra-dashboard-visited", "true");
  } catch (error) {
    if (!token) return;
    app.innerHTML = `
      <section class="card error-card">
        <h1>We could not load your dashboard</h1>
        <p>${escapeHtml(error.message)}</p>
        <button id="retry-dashboard" type="button">Try again</button>
      </section>
    `;
    document.getElementById("retry-dashboard").addEventListener("click", showDashboard);
  }
}

// This function renders only saved profile, goal, debt and calculator results.
function renderDashboard(data) {
  const expenseLimit = data.expense_limit;
  const scenarios = data.scenarios || [];
  const stretch = scenarios.find((scenario) => scenario.label === "Stretch");
  const wanted = scenarios.find((scenario) => scenario.label === "You want");
  const goals = data.goals || [];
  const debts = data.debts || [];
  const growth = data.growth;
  const missingProfile = !data.profile_complete;
  app.innerHTML = `
    <section>
      <p class="eyebrow">Your saved money picture</p>
      <h1>Dashboard</h1>
      ${missingProfile ? `
        <section class="dashboard-panel empty-state">
          <h2>Add your income and expenses to see this</h2>
          <p>Nothing is estimated until you save your own monthly details.</p>
          <button id="dashboard-add-profile" type="button">Add income and expenses</button>
        </section>` : `
        <section class="dashboard-panel">
          <h2>Monthly expense limit</h2>
          ${expenseLimit ? `
            <div class="dashboard-grid">
              <div class="stat"><strong>Safe monthly limit</strong><p>${money(expenseLimit.safe_expense_limit)}</p></div>
              <div class="stat"><strong>Your monthly expenses</strong><p>${money(expenseLimit.current_expenses)}</p></div>
              <div class="stat"><strong>Highest allowed</strong><p>${money(expenseLimit.highest_expenses_allowed)}</p></div>
              <div class="stat"><strong>Room left</strong><p>${money(expenseLimit.room_left)}</p></div>
            </div>` : `
            <div class="empty-state">
              <p>${escapeHtml(data.investment_note || "Save your income, expenses and debt details to calculate this.")}</p>
              <button id="dashboard-add-debts" class="secondary-button" type="button">Review debts and basics</button>
            </div>`}
        </section>
        <section class="dashboard-panel">
          <h2>Investable amount</h2>
          ${data.investment_ready ? `
            <p class="dashboard-primary-value">${money(data.investable_amount)} per month</p>
            <div class="table-scroll">
              <table class="scenario-table dashboard-scenario-table">
                <thead><tr>
                  <th scope="col">Stretch</th>
                  <th scope="col">You want</th>
                  <th scope="col">Your own amount</th>
                </tr></thead>
                <tbody><tr>
                  <td>${stretch && stretch.amount !== null ? money(stretch.amount) : "Not set"}</td>
                  <td>${wanted && wanted.amount !== null ? money(wanted.amount) : "Not set"}</td>
                  <td>
                    <form id="dashboard-amount-form" class="dashboard-amount-form">
                      <label class="sr-only" for="dashboard-own-amount">Your own monthly amount</label>
                      <input id="dashboard-own-amount" name="amount" type="number" min="0" step="0.01"
                        value="${escapeHtml(data.own_amount ?? "")}" />
                      <button class="secondary-button" type="submit">Save amount</button>
                    </form>
                  </td>
                </tr></tbody>
              </table>
            </div>
            <p id="dashboard-amount-status" class="status" role="status"></p>` : `
            <div class="empty-state">
              <p>${escapeHtml(data.investment_note || "Add your income, expenses and debts to see an investable amount.")}</p>
              <button id="dashboard-investment-debts" class="secondary-button" type="button">Review debts and basics</button>
            </div>`}
        </section>
        <section class="dashboard-panel">
          <h2>Goals progress</h2>
          ${goals.length ? goals.map((progress) => {
            const goal = progress.goal || {};
            const snapshot = progress.latest_value_snapshot;
            const hasContributions = Number(progress.total_invested || 0) > 0;
            return `<div class="dashboard-goal">
              <p><strong>${escapeHtml(goal.name || "Saved goal")}</strong> · Target ${money(goal.amount)} · ${escapeHtml(goal.years)} years</p>
              ${snapshot ? `
                <p>Actual saved value: ${money(snapshot.value)} · ${escapeHtml(snapshot.taken_at)}</p>
                <progress value="${escapeHtml(progress.value_progress_percent)}" max="100"
                  aria-label="${escapeHtml(goal.name || "Goal")} actual value progress"></progress>
                <small>Actual value entered by you.</small>`
                : hasContributions ? `
                  <p>Saved contributions: ${money(progress.total_invested)} · excludes investment growth.</p>`
                  : `<div class="empty-state">
                      <p>No goal contributions or actual value have been saved yet.</p>
                      <button class="secondary-button dashboard-open-goals" type="button">Log goal progress</button>
                    </div>`}
            </div>`;
          }).join("") : `
            <div class="empty-state">
              <p>Add a goal and log contributions to see progress here.</p>
              <button id="dashboard-add-goal" class="secondary-button" type="button">Add a goal</button>
            </div>`}
        </section>
        <section class="dashboard-panel">
          <h2>Debts</h2>
          ${debts.length ? `<ul class="dashboard-debt-list">${debts.map((debt) => {
            const amount = debt.balance ?? debt.amount ?? debt.outstanding_balance;
            return `<li><strong>${escapeHtml(debt.name || debt.type || "Debt")}</strong>
              ${amount === undefined || amount === null ? "" : ` · ${money(amount)}`}</li>`;
          }).join("")}</ul>` : `
            <div class="empty-state">
              <p>No debts are saved in your profile.</p>
              <button id="dashboard-edit-debts" class="secondary-button" type="button">Review debts</button>
            </div>`}
        </section>
        <section class="dashboard-panel">
          <h2>Growth projection</h2>
          ${growth ? `
            <p><strong>Estimate</strong>: ${money(growth.amount)} per month for ${escapeHtml(growth.years)} years.</p>
            <p>Assumptions — annual return rates: ${growth.assumptions.map((item) =>
              `${escapeHtml(item.idea_id)}: ${escapeHtml(item.low)}% low, ${escapeHtml(item.middle)}% middle, ${escapeHtml(item.high)}% high`).join("; ")}. Period: ${escapeHtml(growth.years)} years.</p>
            <p>Estimated value after ${escapeHtml(growth.years)} years:
              Low ${money(growth.totals.low)} · Middle ${money(growth.totals.mid)} · High ${money(growth.totals.high)}.</p>
            <div class="chart-wrap"><canvas id="dashboard-growth" aria-label="Estimated investment growth in rupees over years"></canvas></div>`
            : `<div class="empty-state">
                <p>${escapeHtml(data.growth_missing_reason || "Save a monthly amount in Calculators to see an estimate.")}</p>
                <button id="dashboard-open-calculators" class="secondary-button" type="button">Open Calculators</button>
              </div>`}
        </section>`}
    </section>
  `;
  document.getElementById("dashboard-add-profile")?.addEventListener("click", () => navigate("money-details"));
  document.getElementById("dashboard-add-debts")?.addEventListener("click", () => navigate("debts"));
  document.getElementById("dashboard-investment-debts")?.addEventListener("click", () => navigate("debts"));
  document.getElementById("dashboard-edit-debts")?.addEventListener("click", () => navigate("debts"));
  document.getElementById("dashboard-add-goal")?.addEventListener("click", () => navigate("goals"));
  document.querySelectorAll(".dashboard-open-goals").forEach((button) =>
    button.addEventListener("click", () => navigate("goals")));
  document.getElementById("dashboard-open-calculators")?.addEventListener("click", () => navigate("investment-choices"));
  document.getElementById("dashboard-amount-form")?.addEventListener("submit", saveDashboardAmount);
  if (growth) drawDashboardGrowth(growth);
}

async function saveDashboardAmount(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const amount = form.get("amount");
  const target = document.getElementById("dashboard-amount-status");
  if (!String(amount ?? "").trim()) {
    target.textContent = "Enter a monthly amount first.";
    return;
  }
  try {
    await apiRequest("/smart-amount", {
      method: "PUT",
      body: JSON.stringify({ choice: "custom", amount }),
    });
    await showDashboard();
  } catch (error) {
    target.textContent = error.message;
  }
}

// Draw only the saved projection returned by the dashboard calculator.
function drawDashboardGrowth(growth) {
  const canvas = document.getElementById("dashboard-growth");
  if (!canvas || !window.Chart) return;
  replaceChart(canvas, {
    type: "line",
    data: {
      labels: growth.series.map((point) => point.year),
      datasets: [
        { label: "Low estimate", data: growth.series.map((point) => Number(point.low)), borderColor: "#2563EB" },
        { label: "Middle estimate", data: growth.series.map((point) => Number(point.mid)), borderColor: "#10B981" },
        { label: "High estimate", data: growth.series.map((point) => Number(point.high)), borderColor: "#F59E0B" },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        title: { display: true, text: "Estimated growth over time" },
        legend: { display: true, position: "bottom" },
      },
      scales: {
        x: { title: { display: true, text: "Years" } },
        y: {
          title: { display: true, text: "Value (₹)" },
          ticks: { callback: (value) => `₹${Number(value).toLocaleString("en-IN")}` },
        },
      },
    },
  });
}

// This function creates a card that explains an idea, its risk and its match.
function ideaCard(idea) {
  const bars = Array.from({ length: 5 }, (_, index) =>
    `<span class="${index < idea.risk_level ? "filled" : ""}"></span>`).join("");
  return `
    <article class="idea-card ${idea.locked ? "locked" : ""}">
      <p class="eyebrow">${idea.asset_class === "Equity" ? "📈" : idea.asset_class === "Gold" ? "🪙" : "🏦"}
        ${escapeHtml(idea.asset_class)}</p>
      <h3>${escapeHtml(idea.name)}</h3>
      <p><span class="risk-meter" aria-label="Risk ${idea.risk_level} of 5">${bars}</span>${escapeHtml(idea.risk_words)}</p>
      <p>${escapeHtml(idea.school_explanation)}</p>
      ${simpleMode ? "" : `<p class="detailed-note">Assumed yearly return range:
        ${idea.expected_return_low}% to ${idea.expected_return_high}%. These examples can be wrong and are not promises.</p>`}
      <div class="facts-row">
        <span>Start with ${money(idea.minimum_to_start)}</span>
        <span>Keep for ${escapeHtml(idea.time_needed)}</span>
        <span>Access: ${escapeHtml(idea.money_access)}</span>
      </div>
      <p><span class="match-badge">Match for you · ${escapeHtml(idea.match_score)}%</span></p>
      <p>${escapeHtml(idea.match_reason)}</p>
      ${idea.locked ? `<p class="error"><span aria-hidden="true">🔒</span> ${escapeHtml(idea.lock_reason)}</p>` : ""}
      <div class="actions">
        <button type="button" data-idea-detail="${escapeHtml(idea.id)}">Learn more</button>
        <button type="button" class="secondary-button" data-idea-growth="${escapeHtml(idea.id)}">See my plan growth</button><!-- Keep idea cards pointed at the user's saved plan. -->
        <button type="button" class="secondary-button" data-idea-coach="${escapeHtml(idea.id)}">Ask AI coach</button>
      </div>
    </article>
  `;
}

// This function displays all ideas and the four short lessons at the top.
async function showIdeas() {
  currentPage = "ideas";
  document.getElementById("page-title").textContent = pageTitles.ideas; // Keep the shared page header current.
  app.innerHTML = `<section class="card"><div class="loading"></div><p>Loading investment ideas...</p></section>`;
  try {
    const result = await apiRequest("/investment-ideas");
    currentIdeas = result.ideas;
    renderIdeaBrowser(); // Show filterable cards from the saved backend idea list.
  } catch (error) {
    renderRetry("Ideas did not load", error.message, showIdeas);
  }
}

function ideaMatchesFilter(idea) { // Apply the selected simple risk or match chip.
  if (ideaFilter === "safe") return idea.risk_level <= 2; // Keep the safest risk levels together.
  if (ideaFilter === "medium") return idea.risk_level === 3; // Treat risk level three as medium.
  if (ideaFilter === "high") return idea.risk_level >= 4; // Group the higher risk levels together.
  if (ideaFilter === "best") return idea.match_score >= 70 && !idea.locked; // Keep the best unlocked matches visible.
  return true; // Show every idea for the All chip.
} // Finish the risk and match filter.

function renderIdeaResults() { // Filter and sort ideas without asking the backend to invent any.
  const search = ideaSearch.trim().toLowerCase(); // Compare the search text without letter case.
  const ideas = currentIdeas.filter((idea) => { // Keep ideas that match both the chip and search.
    const searchable = `${idea.name} ${idea.asset_class} ${idea.school_explanation}`.toLowerCase(); // Search simple card details.
    return ideaMatchesFilter(idea) && (!search || searchable.includes(search)); // Keep matching ideas only.
  });
  ideas.sort((first, second) => { // Apply the user's selected sort order.
    if (ideaSort === "risk") return first.risk_level - second.risk_level || first.name.localeCompare(second.name); // Show lower risk first.
    if (ideaSort === "start") return Number(first.minimum_to_start) - Number(second.minimum_to_start) || first.name.localeCompare(second.name); // Show lower starting amount first.
    return second.match_score - first.match_score || first.name.localeCompare(second.name); // Show the strongest match first.
  });
  const results = document.getElementById("idea-results"); // Find the visible card area.
  if (!results) return; // Keep the helper safe when the page is changing.
  results.innerHTML = ideas.length
    ? ideas.map(ideaCard).join("")
    : `<p class="empty-state">No ideas match these choices. Try another filter or search.</p>`; // Give users a kind empty state.
  bindIdeaButtons(); // Keep each filtered card's existing actions working.
} // Finish the filtered idea list.

function renderIdeaBrowser() { // Draw the small filter bar above the existing idea cards.
  app.innerHTML = `<section class="ideas-page">
    <h1>Investment ideas</h1>
    <p>Learn first. These are examples, not personal instructions to buy.</p>
    <div class="basics-strip">
      <div class="stat"><strong>What is risk?</strong><p>Like crossing a road: more speed can mean more danger and reward.</p></div>
      <div class="stat"><strong>What is a SIP?</strong><p>Saving one set amount every month.</p></div>
      <div class="stat"><strong>What is compounding?</strong><p>Your earnings also start earning, like a snowball.</p></div>
      <div class="stat"><strong>What is diversification?</strong><p>Do not keep all eggs in one basket.</p></div>
    </div>
    <p class="status-chip watch">! Rates are broad assumptions. Check the latest rate on the official website or your bank.</p>
    <div class="idea-controls">
      <div class="filter-chips" role="group" aria-label="Filter investment ideas">
        ${[["all", "All"], ["safe", "Safe"], ["medium", "Medium"], ["high", "High risk"], ["best", "Best match"]].map(([value, label]) =>
          `<button type="button" class="filter-chip ${ideaFilter === value ? "active" : ""}" data-idea-filter="${value}" aria-pressed="${ideaFilter === value}">${label}</button>`).join("")}
      </div>
      <label>Search ideas <input id="idea-search" type="search" value="${escapeHtml(ideaSearch)}" placeholder="Try FD, gold or fund" /></label>
      <label>Sort by <select id="idea-sort">
        <option value="match" ${ideaSort === "match" ? "selected" : ""}>Best match</option>
        <option value="risk" ${ideaSort === "risk" ? "selected" : ""}>Lowest risk</option>
        <option value="start" ${ideaSort === "start" ? "selected" : ""}>Lowest start amount</option>
      </select></label>
    </div>
    <div id="idea-results" class="idea-grid" aria-live="polite"></div>
  </section>`; // Keep the current cards and only add simple discovery controls.
  document.querySelectorAll("[data-idea-filter]").forEach((button) => button.addEventListener("click", () => { // Keep filters keyboard accessible.
    ideaFilter = button.dataset.ideaFilter; // Remember the selected chip.
    renderIdeaBrowser(); // Refresh the chip state and results.
  })); // Finish the filter buttons.
  document.getElementById("idea-search").addEventListener("input", (event) => { // Filter as the user types.
    ideaSearch = event.currentTarget.value; // Remember the current words.
    renderIdeaResults(); // Update the cards without replacing the search field.
  }); // Finish search behavior.
  document.getElementById("idea-sort").addEventListener("change", (event) => { // Sort using the simple menu.
    ideaSort = event.currentTarget.value; // Remember the selected order.
    renderIdeaResults(); // Refresh the card order.
  }); // Finish sort behavior.
  renderIdeaResults(); // Fill the card area on the first render.
} // Finish the investment ideas page.

// This function connects idea cards to details, growth and the coach.
function bindIdeaButtons() {
  document.querySelectorAll("[data-idea-detail]").forEach((button) =>
    button.addEventListener("click", () => showIdeaDetails(button.dataset.ideaDetail)));
  document.querySelectorAll("[data-idea-growth]").forEach((button) =>
    button.addEventListener("click", () => showIdeaGrowth(button.dataset.ideaGrowth)));
  document.querySelectorAll("[data-idea-coach]").forEach((button) =>
    button.addEventListener("click", () => {
      currentIdea = currentIdeas.find((idea) => idea.id === button.dataset.ideaCoach);
      navigate("coach");
    }));
}

// This function shows an idea's examples, pros, cons, starting steps and mini quiz.
async function showIdeaDetails(ideaId) {
  try {
    const idea = await apiRequest(`/investment-ideas/${encodeURIComponent(ideaId)}`);
    currentIdea = idea;
    app.innerHTML = `
      <section class="card">
        <button class="secondary-button" id="back-ideas" type="button">Back to ideas</button>
        <h1>${escapeHtml(idea.name)}</h1>
        <p>${escapeHtml(idea.real_life_example)}</p>
        <p>${escapeHtml(idea.school_explanation)}</p>
        <p><strong>Risk:</strong> ${escapeHtml(idea.risk_words)}. Returns are not guaranteed.</p>
        <div class="result-grid">
          <div class="stat"><h2>Good things</h2><ul>${idea.pros.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
          <div class="stat"><h2>Things to watch</h2><ul>${idea.cons.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
        </div>
        <h2>How to start</h2>
        <ol>${idea.how_to_start.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
        <h2>Quick quiz</h2>
        ${idea.quiz.map((question, index) => `
          <fieldset class="question" data-quiz="${index}">
            <legend>${escapeHtml(question.question)}</legend>
            ${question.options.map((option, optionIndex) => `
              <label class="choice"><input type="radio" name="idea-q-${index}" value="${optionIndex}" />
                ${escapeHtml(option)}</label>
            `).join("")}
            <button type="button" data-check-quiz="${index}">Check answer</button>
            <p id="quiz-result-${index}" role="status"></p>
          </fieldset>
        `).join("")}
      </section>
    `;
    document.getElementById("back-ideas").addEventListener("click", showIdeas);
    document.querySelectorAll("[data-check-quiz]").forEach((button) =>
      button.addEventListener("click", () => checkIdeaQuiz(idea, Number(button.dataset.checkQuiz))));
    document.querySelectorAll(".question input[type=radio]").forEach((input) =>
      input.addEventListener("change", () => {
        const index = Number(input.name.replace("idea-q-", ""));
        checkIdeaQuiz(idea, index);
      }));
  } catch (error) {
    renderRetry("Idea details did not load", error.message, () => showIdeaDetails(ideaId));
  }
}

// This function gives kind feedback when a learner checks a quiz answer.
function checkIdeaQuiz(idea, index) {
  const selected = document.querySelector(`input[name="idea-q-${index}"]:checked`);
  const result = document.getElementById(`quiz-result-${index}`);
  if (!selected) {
    result.textContent = "Choose one answer first.";
    return;
  }
  result.textContent = Number(selected.value) === idea.quiz[index].answer
    ? "Nice! Try the next one."
    : "Good try. Read the idea again, then try once more.";
}

// This function opens the saved-plan projector from an investment idea card.
function showIdeaGrowth() { // Open the saved-plan projector from an idea card.
  navigate("projector"); // Project the chosen plan instead of an unchosen idea.
}

// This function shows a friendly next step when the user has not saved a plan.
function renderProjectorEmpty() {
  app.innerHTML = `<section class="card">
    <h1>Growth projector</h1>
    <p>You have not chosen your investments yet.</p>
    <button id="choose-projector-investments" type="button">Choose my investments</button>
  </section>`; // Keep an empty plan from looking like a loading or error state.
  document.getElementById("choose-projector-investments").addEventListener(
    "click",
    () => navigate("investment-choices"),
  ); // Open the user's Step 4 choices.
}

// This function draws the saved-part donut and the plan's three growth cases.
function drawPlanProjectorCharts(result) {
  if (!window.Chart) return; // Keep the table useful if charts are not available.
  const colors = ["#2563EB", "#10B981", "#F59E0B", "#6366F1", "#14B8A6", "#D97706", "#64748B"]; // Reuse clear colors for saved parts.
  const donut = document.getElementById("plan-projector-donut"); // Find the saved-plan allocation chart.
  if (donut) replaceChart(donut, {
    type: "doughnut",
    data: {
      labels: result.parts.map((part) => part.name),
      datasets: [{ data: result.parts.map((part) => Number(part.share)), backgroundColor: colors }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  }); // Draw only the chosen plan parts.
  const growth = document.getElementById("plan-projector-growth"); // Find the full-plan growth chart.
  if (growth) replaceChart(growth, {
    type: "line",
    data: {
      labels: result.series.map((point) => `${point.year} year${point.year === 1 ? "" : "s"}`),
      datasets: [
        { label: "Low", data: result.series.map((point) => Number(point.low)), borderColor: "#D97706", borderWidth: projectorScenario === "low" ? 4 : 2 },
        { label: "Middle", data: result.series.map((point) => Number(point.mid)), borderColor: "#2563EB", borderWidth: projectorScenario === "mid" ? 4 : 2 },
        { label: "High", data: result.series.map((point) => Number(point.high)), borderColor: "#10B981", borderWidth: projectorScenario === "high" ? 4 : 2 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
  }); // Keep each return case visible and highlight the selected one.
}

// This function paints saved parts, backend totals, controls and plan growth.
function renderPlanProjector(result) {
  const selectedPoint = result.series.find((point) => point.year === projectorYears) || result.series[result.series.length - 1]; // Read the selected year's backend result.
  const scenarioNames = { low: "low", mid: "middle", high: "high" }; // Use plain-English case names in the summary.
  const monthlyRupees = `Rs ${money(result.monthly_amount).replace(/^₹/, "")}`; // Keep the requested simple rupee wording.
  const futureRupees = `Rs ${money(selectedPoint[projectorScenario]).replace(/^₹/, "")}`; // Format the selected scenario result.
  const investedRupees = `Rs ${money(selectedPoint.invested).replace(/^₹/, "")}`; // Show the backend total invested.
  app.innerHTML = `<section class="card">
    <h1>Growth projector</h1>
    <p>Expected, not guaranteed.</p>
    <p>Your plan: ${result.parts_count} parts, ${monthlyRupees} per month. In ${selectedPoint.year} years your money could be about ${futureRupees} (${scenarioNames[projectorScenario]} case). You put in ${investedRupees}.</p>
    <div class="projector-controls">
      <label>Years
        <input id="projector-years" type="number" min="1" max="30" step="1" value="${result.years}" />
      </label>
      <label>Scenario
        <select id="projector-scenario">
          <option value="low" ${projectorScenario === "low" ? "selected" : ""}>Low</option>
          <option value="mid" ${projectorScenario === "mid" ? "selected" : ""}>Middle</option>
          <option value="high" ${projectorScenario === "high" ? "selected" : ""}>High</option>
        </select>
      </label>
    </div>
    <div class="projector-charts">
      <div class="chart-wrap"><h2>Your chosen parts</h2><canvas id="plan-projector-donut" aria-label="Only your chosen investment parts"></canvas></div>
      <div class="chart-wrap projector-growth-chart"><h2>Possible growth for your whole plan</h2><canvas id="plan-projector-growth" aria-label="Low, middle and high growth cases for your saved plan"></canvas></div>
    </div>
    <p>${escapeHtml(result.label)}</p>
    <div class="table-scroll"><table class="allocation-table">
      <thead><tr><th>Idea</th><th>Each month</th><th>5-year middle</th><th>10-year middle</th></tr></thead>
      <tbody>${result.parts.map((part) => `<tr>
        <td>${escapeHtml(part.name)}<br /><small>Share: ${escapeHtml(part.share)}%</small></td>
        <td>${money(part.monthly_amount)}</td>
        <td>${money(part.growth["5"].mid)}</td>
        <td>${money(part.growth["10"].mid)}</td>
      </tr>`).join("")}</tbody>
      <tfoot><tr>
        <th scope="row">Total</th>
        <td>${money(result.totals.monthly)}</td>
        <td>${money(result.totals.five_year_middle)}</td>
        <td>${money(result.totals.ten_year_middle)}</td>
      </tr></tfoot>
    </table></div><!-- Let the saved-plan table scroll without widening the page. -->
    <p>Each growth number is an assumption, not a promise.</p>
  </section>`; // Show only saved choices and backend-calculated results.
  document.getElementById("projector-years").addEventListener("change", (event) => {
    const years = Number(event.currentTarget.value); // Read the requested whole-year range.
    if (!Number.isInteger(years) || years < 1 || years > 30) return; // Leave out-of-range values for the browser to flag.
    projectorYears = years; // Remember the selected range.
    showProjector(); // Ask the backend for the selected range of growth.
  }); // Finish connecting the year selector.
  document.getElementById("projector-scenario").addEventListener("change", (event) => {
    projectorScenario = event.currentTarget.value; // Remember the selected growth case.
    renderPlanProjector(result); // Update the summary and highlight without changing calculations.
  }); // Finish connecting the scenario selector.
  drawPlanProjectorCharts(result); // Draw the two charts from the saved plan response.
}

// This function loads the saved plan and its per-part Decimal projection.
async function showProjector() {
  app.innerHTML = `<section class="card"><div class="loading"></div><p>Loading your saved plan...</p></section>`; // Show a short loading state.
  try {
    const savedPlan = await apiRequest("/plan", { cache: "no-store" }); // Always read the latest saved choices.
    if (!savedPlan.exists) return renderProjectorEmpty(); // Give users a clear next step when no plan is saved.
    const result = await apiRequest(`/plan/projector?years=${projectorYears}`, { cache: "no-store" }); // Load growth only for saved plan parts.
    if (!result.exists) return renderProjectorEmpty(); // Handle a plan removed between the two requests.
    renderPlanProjector(result); // Show exact amounts and per-part growth outcomes.
  } catch (error) {
    renderRetry("Growth projector could not load", error.message, showProjector); // Show a clear retry for real API failures.
  }
}

// This function opens the three-question investment-choice wizard.
async function showInvestmentChoices() {
  app.innerHTML = `<section class="card"><div class="loading"></div><p>Loading your choices...</p></section>`;
  try {
    const [onboarding, ideas, savedPlan, smartAmount] = await Promise.all([
      apiRequest("/onboarding/status"),
      apiRequest("/investment-ideas"),
      apiRequest("/plan"),
      apiRequest("/smart-monthly-amount"),
    ]);
    currentIdeas = ideas.ideas;
    const defaultAmount = savedPlan.exists
      ? savedPlan.monthly_amount
      : userProfile.wanted_monthly_amount || String(smartAmount.recommended);
    smartAmountSuggestion = smartAmount; // Keep the fresh recommendation for the Step 4 back button.
    planDraft = {
      monthlyAmount: defaultAmount,
      selectedIds: savedPlan.exists ? savedPlan.parts.map((part) => part.idea_id) : [],
      parts: savedPlan.exists ? savedPlan.parts : [],
      maxParts: onboarding.max_parts || 1,
      suggestions: [],
      basics: [],
      taxSaving80c: Boolean(savedPlan.tax_saving_80c),
      suggestionDetails: null,
    };
    const suggestion = await loadChoiceSuggestion(defaultAmount);
    renderChoiceAmount(onboarding, suggestion, !onboarding.complete, smartAmount);
  } catch (error) {
    renderRetry("Investment choices could not load", error.message, showInvestmentChoices);
  }
}

// This function asks the backend for safe amounts, part limits and suggestion choices.
async function loadChoiceSuggestion(amount) {
  const result = await apiRequest(
    `/plan/suggestion?monthly_amount=${encodeURIComponent(amount)}&tax_saving_80c=${planDraft.taxSaving80c}`,
  );
  planDraft.maxParts = result.max_parts;
  planDraft.suggestions = result.parts;
  planDraft.basics = result.basics;
  planDraft.suggestionDetails = result;
  return result;
}

// This function displays the sourced reasons and per-part outcome scenarios.
function renderWhyPlanCard(suggestion) {
  if (!suggestion?.why_this_plan) return "";
  const why = suggestion.why_this_plan;
  const parts = suggestion.parts || [];
  const scenarios = suggestion.scenario_totals || {};
  const partRows = parts.map((part) => {
    const five = part.growth["5"];
    const ten = part.growth["10"];
    return `<tr>
      <th scope="row">${escapeHtml(part.name)}</th>
      <td>${money(part.monthly_amount)}</td>
      <td>${money(five.invested)}</td>
      <td>Low ${money(five.low)} (earned ${money(five.earned_low)})<br>
        Expected ${money(five.mid)} (earned ${money(five.earned_mid)})<br>
        High ${money(five.high)} (earned ${money(five.earned_high)})</td>
      <td>${money(ten.invested)}</td>
      <td>Low ${money(ten.low)} (earned ${money(ten.earned_low)})<br>
        Expected ${money(ten.mid)} (earned ${money(ten.earned_mid)})<br>
        High ${money(ten.high)} (earned ${money(ten.earned_high)})</td>
    </tr>`;
  }).join("");
  const totalRows = ["5", "10"].map((years) => {
    const total = scenarios[years];
    return `<tr>
      <th scope="row">${years}-year total</th>
      <td>${money(total.invested)} invested</td>
      <td>Low earned ${money(total.earned_low)}</td>
      <td>Expected earned ${money(total.earned_mid)}</td>
      <td>High earned ${money(total.earned_high)}</td>
    </tr>`;
  }).join("");
  const stress = suggestion.stress_test || {};
  return `<section class="dashboard-panel why-plan" aria-labelledby="why-plan-title">
    <h2 id="why-plan-title">Why this plan</h2>
    <p><strong>Data as of ${escapeHtml(why.data_as_of)}.</strong> ${escapeHtml(why.market_notice || "")}</p>
    <p>${escapeHtml(why.market_summary)}</p>
    <ul>${(why.sources || []).map((source) => `
      <li><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">
        ${escapeHtml(source.name)} source</a></li>`).join("")}</ul>
    <p>${escapeHtml(why.means_for_you)}</p>
    <p>${escapeHtml(why.part_count_reason)}</p>
    <h3>Changes from the standard mix</h3>
    ${why.changes_from_standard_mix?.length
      ? `<ul>${why.changes_from_standard_mix.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : "<p>No market tilt was applied.</p>"}
    <h3>Possible outcomes by part</h3>
    <p>Low, expected and high are assumptions, not guarantees. Each part is calculated separately.</p>
    <div class="table-scroll"><table class="allocation-table scenario-table">
      <thead><tr><th>Part</th><th>Monthly</th><th>5-year invested</th><th>5-year possible value and earned</th>
        <th>10-year invested</th><th>10-year possible value and earned</th></tr></thead>
      <tbody>${partRows}</tbody>
      <tfoot>${totalRows}</tfoot>
    </table></div>
    <p>Your plan could temporarily fall by about ${escapeHtml(stress.fall_percent || "0")}%,
      or ${money(stress.loss_amount || "0")}, in one bad-year example.</p>
    <p><strong>${escapeHtml(why.disclaimer)}</strong> ${escapeHtml(why.review_reminder)}</p>
    <button id="refresh-market-data" class="secondary-button" type="button">Refresh data</button>
    <p id="market-refresh-status" role="status">${escapeHtml(why.market_notice || "")}</p>
  </section>`;
}

// This function refreshes sourced figures and keeps the user's current part edits.
function bindMarketRefresh(onboarding, isSetup, showParts) {
  document.getElementById("refresh-market-data")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    const status = document.getElementById("market-refresh-status");
    if (status) status.textContent = "Refreshing public data...";
    try {
      await apiRequest("/market-snapshot/refresh", { method: "POST" });
      await loadChoiceSuggestion(planDraft.monthlyAmount);
      if (showParts) {
        renderChoiceParts(onboarding, isSetup);
      } else {
        renderChoiceIdeas(
          onboarding,
          { basics: planDraft.basics, parts: planDraft.suggestions },
          isSetup,
        );
      }
    } catch (error) {
      if (status) status.textContent = error.message;
      button.disabled = false;
    }
  });
}

// This function shows the user's monthly amount and safe-budget warning.
function renderChoiceAmount(onboarding, suggestion, isSetup, smartAmount) {
  app.innerHTML = `<section class="card">
    ${isSetup ? onboardingProgress(4, "Your investment choices") : ""}
    <h1>${isSetup ? "Your investment choices" : "Edit my plan"}</h1>
    ${isSetup ? "<p>We will choose where your money goes, one question at a time.</p>"
      : "<p>Changing your plan will refresh its score and dashboard summary.</p>"}
    <p class="eyebrow">Question 1 of 3</p>
    <form id="choice-amount-form" class="form-grid">
      <label>How much do you want to invest each month?
        <input id="choice-monthly-amount" name="monthly_amount" type="number" min="0"
          step="0.01" value="${escapeHtml(planDraft.monthlyAmount)}" required />
      </label>
      <label>Is your income steady?
        <select id="income-stability" name="income_stability">
          <option value="steady" ${smartAmount.income_stability === "steady" ? "selected" : ""}>Yes, it is steady</option>
          <option value="sometimes_changes" ${smartAmount.income_stability === "sometimes_changes" ? "selected" : ""}>It sometimes changes</option>
          <option value="irregular" ${smartAmount.income_stability === "irregular" ? "selected" : ""}>It is irregular</option>
        </select>
      </label>
      <div id="smart-amount-preview">${smartAmountMarkup(smartAmount)}</div>
      <small>Each saved plan part must be at least ₹500 and at least 10% of the total.</small>
      <label>Do you want to save tax under 80C?
        <select id="tax-saving-80c" name="tax_saving_80c">
          <option value="false" ${planDraft.taxSaving80c ? "" : "selected"}>No</option>
          <option value="true" ${planDraft.taxSaving80c ? "selected" : ""}>Yes</option>
        </select>
      </label>
      <small>Choose Yes only if you want ELSS to be considered. Check the current tax rules.</small>
      <p>Your safe amount left each month is
        <strong>${suggestion.safe_monthly_amount === null ? "not available yet" : money(suggestion.safe_monthly_amount)}</strong>.
        This uses income minus expenses and all monthly debt payments.</p>
      <p id="amount-warning" class="${suggestion.amount_over_safe ? "error" : "status"}" role="status">
        ${suggestion.amount_over_safe
          ? "That is more than you have left each month. You may need to cut expenses or choose a smaller amount."
          : suggestion.safe_amount_negative
            ? "Money out is more than money in. Try to lower expenses or debt payments before choosing an investment amount."
            : "This amount is a starting point. You can change it."}
      </p>
      ${suggestion.safe_amount_negative ? `<div class="dashboard-panel"><strong>Ways to free up money</strong>
        <ul><li>List needs and wants, then look for one small cost to reduce.</li>
        <li>Ask your lender about payment options before missing an EMI.</li>
        <li>Do not borrow money just to invest.</li></ul></div>` : ""}
      <button type="submit">Continue to where</button>
      <button id="back-to-quiz" class="secondary-button" type="button">Back to risk quiz</button>
    </form>
  </section>`;
  bindSmartAmountToggles();
  let amountTouched = Boolean(userProfile.wanted_monthly_amount || planDraft.selectedIds.length); // Do not replace a saved amount the user chose.
  document.getElementById("choice-amount-form").addEventListener("change", async (event) => {
    if (event.target.name === "tax_saving_80c") {
      planDraft.taxSaving80c = event.target.value === "true";
      try {
        await loadChoiceSuggestion(planDraft.monthlyAmount);
      } catch (error) {
        document.getElementById("amount-warning").textContent = error.message;
      }
      return;
    }
    if (!["monthly_amount", "income_stability"].includes(event.target.name)) return;
    try {
      if (event.target.name === "monthly_amount") {
        planDraft.monthlyAmount = event.target.value;
        amountTouched = true;
      }
      const currentStability = document.getElementById("income-stability").value;
      let preview = await apiRequest("/smart-monthly-amount/preview", {
        method: "POST",
        body: JSON.stringify({
          income_stability: currentStability,
          wanted_monthly_amount: document.getElementById("choice-monthly-amount").value,
        }),
      });
      if (event.target.name === "income_stability" && !amountTouched) {
        document.getElementById("choice-monthly-amount").value = String(preview.recommended);
        planDraft.monthlyAmount = String(preview.recommended);
        preview = await apiRequest("/smart-monthly-amount/preview", {
          method: "POST",
          body: JSON.stringify({
            income_stability: currentStability,
            wanted_monthly_amount: String(preview.recommended),
          }),
        });
      }
      smartAmountSuggestion = preview; // Keep the newest backend preview for the next screen.
      document.getElementById("smart-amount-preview").innerHTML = smartAmountMarkup(preview);
      bindSmartAmountToggles();
      const updated = await loadChoiceSuggestion(planDraft.monthlyAmount);
      const warning = document.getElementById("amount-warning");
      warning.className = updated.amount_over_safe ? "error" : "status";
      warning.textContent = updated.amount_over_safe
        ? "That is more than you have left each month. You may need to cut expenses or choose a smaller amount."
        : updated.safe_amount_negative
          ? "Money out is more than money in. Try to lower expenses or debt payments before choosing an investment amount."
          : "This amount is a starting point. You can change it.";
    } catch (error) {
      document.getElementById("amount-warning").textContent = error.message;
    }
  });
  document.getElementById("choice-amount-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const amount = formData.get("monthly_amount");
    planDraft.monthlyAmount = String(amount);
    planDraft.taxSaving80c = formData.get("tax_saving_80c") === "true";
    try {
      const savedCapacity = await apiRequest("/profile/investment-capacity", {
        method: "PATCH",
        body: JSON.stringify({
          income_stability: formData.get("income_stability"),
          wanted_monthly_amount: amount,
        }),
      });
      smartAmountSuggestion = savedCapacity.suggestion; // Keep the saved backend recommendation after Step 4.
      const updated = await loadChoiceSuggestion(planDraft.monthlyAmount);
      renderChoiceIdeas(onboarding, updated, isSetup);
    } catch (error) {
      document.getElementById("amount-warning").textContent = error.message;
    }
  });
  document.getElementById("back-to-quiz").addEventListener("click", () =>
    navigate(onboarding.complete ? "dashboard" : "retake-quiz"));
}

// This function shows all ideas, their lock status, and safe basics jars when needed.
function renderChoiceIdeas(onboarding, suggestion, isSetup) {
  const ideaMarkup = currentIdeas.map((idea) => `
    <label class="choice-card ${idea.locked ? "locked" : ""}">
      <input type="checkbox" data-choice-id="${escapeHtml(idea.id)}"
        ${idea.locked ? "disabled" : ""}
        ${planDraft.selectedIds.includes(idea.id) ? "checked" : ""} />
      <strong>${escapeHtml(idea.name)}</strong>
      <span>${escapeHtml(idea.school_explanation)}</span>
      ${idea.locked
        ? `<span class="error">Fix basics first: ${escapeHtml(idea.lock_reason)}</span>` : ""}
      <small>Risk ${idea.risk_level} of 5 · Start from ${money(idea.minimum_to_start)}</small>
    </label>`).join("");
  const basicsMarkup = (suggestion.basics || []).map((idea) => `
    <label class="choice-card basics-choice">
      <input type="checkbox" data-choice-id="${escapeHtml(idea.id)}"
        ${planDraft.selectedIds.includes(idea.id) ? "checked" : ""} />
      <strong>${escapeHtml(idea.name)}</strong>
      <span>${escapeHtml(idea.reason)}</span>
      <small>Basics first · Not an investment</small>
    </label>`).join("");
  app.innerHTML = `<section class="card">
    ${isSetup ? onboardingProgress(4, "Your investment choices") : ""}
    <h1>${isSetup ? "Where would you like to put your money?" : "Choose your plan parts"}</h1>
    <p class="eyebrow">Question 2 of 3</p>
    <p>Pick one or more ideas. Locked ideas cannot be chosen until the basics are ready.</p>
    <div class="choice-grid">${ideaMarkup}${basicsMarkup}</div>
    ${renderWhyPlanCard(planDraft.suggestionDetails)}
    <p id="idea-selection-error" class="error" role="alert"></p>
    <div class="actions">
      <button id="continue-to-parts" type="button">Choose my parts</button>
      <button id="use-suggestion" class="secondary-button" type="button">
        Not sure? Use ArthMitra's suggestion
      </button>
      <button id="back-to-amount" class="secondary-button" type="button">Back</button>
    </div>
  </section>`;
  document.getElementById("continue-to-parts").addEventListener("click", () => {
    planDraft.selectedIds = [...document.querySelectorAll("[data-choice-id]:checked")]
      .map((input) => input.dataset.choiceId);
    if (!planDraft.selectedIds.length) {
      document.getElementById("idea-selection-error").textContent = "Choose at least one idea or safe basics jar.";
      return;
    }
    planDraft.parts = [];
    renderChoiceParts(onboarding, isSetup);
  });
  document.getElementById("use-suggestion").addEventListener("click", () => {
    planDraft.parts = suggestion.parts.map((part) => ({
      idea_id: part.idea_id,
      share: part.share,
    }));
    planDraft.selectedIds = planDraft.parts.map((part) => part.idea_id);
    renderChoiceParts(onboarding, isSetup);
  });
  bindMarketRefresh(onboarding, isSetup, false);
  document.getElementById("back-to-amount").addEventListener("click", () =>
    renderChoiceAmount(onboarding, suggestion, isSetup, smartAmountSuggestion));
}

// This function assigns each part one idea and shows its slider-based percentage.
function renderChoiceParts(onboarding, isSetup) {
  const maximum = Math.max(1, Math.min(7, planDraft.maxParts, planDraft.selectedIds.length));
  const initialCount = Math.min(
    maximum,
    planDraft.parts.length || maximum,
  );
  if (planDraft.parts.length !== initialCount) {
    const ids = planDraft.selectedIds.slice(0, initialCount);
    const shares = evenShares(initialCount);
    planDraft.parts = ids.map((idea_id, index) => ({ idea_id, share: shares[index] }));
  }
  app.innerHTML = `<section class="card">
    ${isSetup ? onboardingProgress(4, "Your investment choices") : ""}
    <h1>How many parts do you want?</h1>
    <p class="eyebrow">Question 3 of 3</p>
    <p>Think of each part as a separate piggy bank (jar). Different jars do different jobs.
      Do not keep all eggs in one basket.</p>
    <label>Number of parts
      <select id="part-count">${Array.from({ length: maximum }, (_, index) =>
        `<option value="${index + 1}" ${index + 1 === initialCount ? "selected" : ""}>
          ${index + 1} ${index === 0 ? "part" : "parts"}
        </option>`).join("")}</select>
    </label>
    <div id="part-sliders">${planDraft.parts.map((part, index) => partSlider(part, index)).join("")}</div>
    ${renderWhyPlanCard(planDraft.suggestionDetails)}
    <p id="share-total" class="status" aria-live="polite"></p>
    <p id="share-error" class="error" role="alert"></p>
    <div class="actions">
      <button id="split-evenly" class="secondary-button" type="button">Split evenly</button>
      <button id="parts-suggestion" class="secondary-button" type="button">Use ArthMitra's suggestion</button>
      <button id="reset-parts" class="secondary-button" type="button">Reset</button>
    </div>
    <div id="parts-preview"></div>
    <div class="actions">
      <button id="save-plan" type="button">Continue to review</button>
      <button id="back-to-ideas" class="secondary-button" type="button">Back to ideas</button>
      ${isSetup ? `<button id="save-plan-later" class="secondary-button" type="button">Save and continue later</button>` : ""}
    </div>
  </section>`;
  document.getElementById("part-count").addEventListener("change", (event) => {
    const count = Number(event.target.value);
    const ids = planDraft.parts.map((part) => part.idea_id);
    const nextIds = ids.slice(0, count);
    for (const id of planDraft.selectedIds) {
      if (nextIds.length >= count) break;
      if (!nextIds.includes(id)) nextIds.push(id);
    }
    const shares = evenShares(count);
    planDraft.parts = nextIds.map((idea_id, index) => ({ idea_id, share: shares[index] }));
    renderChoiceParts(onboarding, isSetup);
  });
  document.querySelectorAll("[data-part-idea]").forEach((select) =>
    select.addEventListener("change", (event) => {
      const index = Number(event.currentTarget.dataset.partIdea);
      const ideaId = event.currentTarget.value;
      if (planDraft.parts.some((part, partIndex) => partIndex !== index && part.idea_id === ideaId)) {
        document.getElementById("share-error").textContent = "Choose a different idea for each part.";
        return;
      }
      planDraft.parts[index].idea_id = ideaId;
      updateShareTotal();
      refreshPlanPreview();
    }));
  document.querySelectorAll("[data-part-share]").forEach((slider) =>
    slider.addEventListener("input", (event) => {
      const index = Number(event.currentTarget.dataset.partShare);
      planDraft.parts[index].share = event.currentTarget.value;
      event.currentTarget.parentElement.querySelector("output").textContent =
        `${event.currentTarget.value}%`;
      updateShareTotal();
      refreshPlanPreview();
    }));
  document.getElementById("split-evenly").addEventListener("click", () => {
    const shares = evenShares(planDraft.parts.length);
    planDraft.parts.forEach((part, index) => { part.share = shares[index]; });
    renderChoiceParts(onboarding, isSetup);
  });
  document.getElementById("parts-suggestion").addEventListener("click", async () => {
    try {
      const suggestion = await loadChoiceSuggestion(planDraft.monthlyAmount);
      planDraft.parts = suggestion.parts.map((part) => ({
        idea_id: part.idea_id,
        share: part.share,
      }));
      planDraft.selectedIds = planDraft.parts.map((part) => part.idea_id);
      renderChoiceParts(onboarding, isSetup);
    } catch (error) {
      document.getElementById("share-error").textContent = error.message;
    }
  });
  bindMarketRefresh(onboarding, isSetup, true);
  document.getElementById("reset-parts").addEventListener("click", () => {
    planDraft.parts.forEach((part, index) => {
      part.share = index === 0 ? "100" : "0";
    });
    renderChoiceParts(onboarding, isSetup);
  });
  document.getElementById("save-plan").addEventListener("click", () => saveChoicePlan(false));
  document.getElementById("save-plan-later")?.addEventListener("click", () => saveChoicePlan(true));
  document.getElementById("back-to-ideas").addEventListener("click", () =>
    renderChoiceIdeas(onboarding, { basics: planDraft.basics, parts: planDraft.suggestions }, isSetup));
  updateShareTotal();
  refreshPlanPreview();
}

// This function makes percentage shares add up to exactly 100 with hundredth-percent steps.
function evenShares(count) {
  const base = Math.floor(10000 / count);
  const remainder = 10000 - base * count;
  return Array.from({ length: count }, (_, index) =>
    ((base + (index < remainder ? 1 : 0)) / 100).toFixed(2));
}

// This function builds one idea selector and one 0-to-100 percent slider.
function partSlider(part, index) {
  const choices = planDraft.selectedIds.map((ideaId) => {
    const idea = currentIdeas.find((item) => item.id === ideaId) ||
      planDraft.basics.find((item) => item.id === ideaId) ||
      planDraft.suggestions.find((item) => item.idea_id === ideaId);
    return `<option value="${escapeHtml(ideaId)}" ${ideaId === part.idea_id ? "selected" : ""}>
      ${escapeHtml(idea?.name || ideaId)}</option>`;
  }).join("");
  return `<fieldset class="question part-row">
    <legend>Part ${index + 1}</legend>
    <label>Idea
      <select data-part-idea="${index}">${choices}</select>
    </label>
    <label>Share
      <input type="range" min="0" max="100" step="0.01" value="${escapeHtml(part.share)}"
        data-part-share="${index}" />
      <output>${escapeHtml(part.share)}%</output>
    </label>
  </fieldset>`;
}

// This function reports whether the slider percentages total exactly 100%.
function updateShareTotal() {
  const totalHundredths = planDraft.parts.reduce(
    (total, part) => total + Math.round(Number(part.share) * 100),
    0,
  );
  const total = (totalHundredths / 100).toFixed(2);
  const totalElement = document.getElementById("share-total");
  if (totalElement) {
    totalElement.textContent = totalHundredths === 10000
      ? "Your parts add up to 100%. You can continue."
      : `Your parts add up to ${total}%. ${totalHundredths < 10000
        ? `Add ${(10000 - totalHundredths) / 100}% more.`
        : `Remove ${(totalHundredths - 10000) / 100}%.`}`;
  }
  const saveButton = document.getElementById("save-plan");
  if (saveButton) saveButton.disabled = totalHundredths !== 10000;
}

// This function asks the backend for live amounts and updates the plan donut.
async function refreshPlanPreview() {
  const target = document.getElementById("parts-preview");
  if (!target) return;
  const sequence = ++planPreviewSequence;
  target.innerHTML = "<p>Updating your part amounts...</p>";
  try {
    const result = await apiRequest("/plan/preview", {
      method: "POST",
      body: JSON.stringify({
        monthly_amount: planDraft.monthlyAmount,
        parts: planDraft.parts,
        tax_saving_80c: planDraft.taxSaving80c,
      }),
    });
    if (sequence !== planPreviewSequence) return;
    target.innerHTML = `
      <div class="chart-wrap"><canvas id="parts-preview-chart" aria-label="Live monthly plan split"></canvas></div>
      <ul>${result.parts.map((part, index) => `<li>
        Part ${index + 1}: ${escapeHtml(part.name)} · ${escapeHtml(part.share)}% =
        ${money(part.monthly_amount)}
        ${part.below_minimum ? `<span class="status">Needs at least ${money(part.minimum_to_start)} and 10% of the plan to save.</span>` : ""}
      </li>`).join("")}</ul>
      <p>Total selected: ${money(result.allocated_total)} of ${money(result.total)}.</p>`;
    drawPlanPreview(result.parts);
  } catch (error) {
    if (sequence !== planPreviewSequence) return;
    target.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
  }
}

// This function draws a donut from the exact amounts returned by the backend.
function drawPlanPreview(parts) {
  const canvas = document.getElementById("parts-preview-chart");
  if (!canvas || !window.Chart) return;
  replaceChart(canvas, {
    type: "doughnut",
    data: {
      labels: parts.map((part) => part.name),
      datasets: [{
        data: parts.map((part) => Number(part.monthly_amount)),
        backgroundColor: ["#2563EB", "#10B981", "#F59E0B", "#6366F1", "#14B8A6", "#D97706", "#64748B"],
      }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}

// This function saves the validated sliders and opens plan analysis.
async function saveChoicePlan(saveLater) {
  const total = planDraft.parts.reduce(
    (sum, part) => sum + Math.round(Number(part.share) * 100),
    0,
  );
  if (total !== 10000) {
    document.getElementById("share-error").textContent =
      `Your parts add up to ${(total / 100).toFixed(2)}%. Make the total exactly 100%.`;
    return;
  }
  try {
    await apiRequest("/plan", {
      method: "POST",
      body: JSON.stringify({
        monthly_amount: planDraft.monthlyAmount,
        parts: planDraft.parts,
      }),
    });
    if (saveLater) {
      await apiRequest("/auth/logout", { method: "POST" });
      token = "";
      localStorage.removeItem(tokenKey);
      history.replaceState({}, "", "#login");
      renderLogin("Your choices are saved. Log in when you are ready to review them.");
      return;
    }
    navigate("plan-review");
  } catch (error) {
    document.getElementById("share-error").textContent = error.message;
  }
}

// This function shows both plans, all analysis checks, goal options and score fixes.
async function showPlanReview() {
  app.innerHTML = `<section class="card"><div class="loading"></div><p>Reviewing each part of your plan...</p></section>`;
  try {
    const analysis = await apiRequest("/plan/analyze", { method: "POST" });
    const comparison = await apiRequest("/plan/compare");
    const plan = await apiRequest("/plan");
    const [minePreview, suggestedPreview] = await Promise.all([
      apiRequest("/plan/preview", {
        method: "POST",
        body: JSON.stringify({ monthly_amount: plan.monthly_amount, parts: plan.parts }),
      }),
      apiRequest("/plan/preview", {
        method: "POST",
        body: JSON.stringify({
          monthly_amount: plan.monthly_amount,
          parts: comparison.suggested_plan.parts,
        }),
      }),
    ]);
    renderPlanReview(analysis, comparison, minePreview, suggestedPreview);
  } catch (error) {
    renderRetry("Plan review could not load", error.message, showPlanReview);
  }
}

// This function puts analysis results into school-level words and review actions.
function renderPlanReview(analysis, comparison, minePreview, suggestedPreview) {
  const goal = analysis.goal;
  app.innerHTML = `<section class="card">
    ${onboardingProgress(5, "Review and plan")}
    <h1>Review your plan</h1>
    <p>These are estimates based on assumptions, not promises. A high score cannot remove investment risk.</p>
    <div class="dashboard-grid">
      <div class="stat"><strong>Your plan score</strong><p>${analysis.score} / 100 · ${escapeHtml(analysis.grade)}</p></div>
      <div class="stat"><strong>Weighted risk</strong><p>${escapeHtml(analysis.weighted_risk)} / 5</p></div>
      <div class="stat"><strong>Average return</strong><p>${escapeHtml(analysis.weighted_average_return)}% ·
        ${escapeHtml(analysis.weighted_average_return_label)}</p></div>
      <div class="stat"><strong>Monthly amount</strong><p>${money(analysis.monthly_amount)}</p></div>
    </div>
    <h2>Six checks</h2>
    <div class="result-grid">${analysis.checks.map((check) => `
      <div class="check ${check.status === "good" ? "passed" : "failed"}">
        <strong>${escapeHtml(check.name)} · ${check.score}/${check.max_points}</strong>
        <p>${escapeHtml(check.message)}</p>
      </div>`).join("")}</div>
    ${goal ? `<section class="dashboard-panel">
      <h2>Goal chance: ${escapeHtml(goal.chance_percent)}%</h2>
      <p>For ${escapeHtml(goal.name)}: middle estimate ${money(goal.future_value_mid)} in
        ${escapeHtml(goal.years)} years. This is only an example, not a promise.</p>
      ${goal.reachable ? "<p>The middle estimate reaches the goal amount.</p>" : `
        <p>The middle estimate is below the goal. Here are three things you could change:</p>
        <ul><li>Invest more: about ${money(goal.options.invest_more_monthly)} each month.</li>
        <li>Take more time: ${goal.options.take_more_time_years === null
          ? "This goal was not reached within 50 years at the current amount."
          : `${escapeHtml(goal.options.take_more_time_years)} years.`}</li>
        <li>Lower the goal: about ${money(goal.options.lower_goal_to)} in the chosen time.</li></ul>`}
    </section>` : `<p>Add a goal in money details to see a goal chance.</p>`}
    <h2>Your plan vs ArthMitra's suggestion</h2>
    <p>${escapeHtml(comparison.summary)}</p>
    <div class="comparison-grid">
      <article class="dashboard-panel">
        <h3>Your plan · ${analysis.score}/100 · ${escapeHtml(analysis.grade)}</h3>
        <p>Weighted risk ${escapeHtml(analysis.weighted_risk)} · Goal chance
          ${goal ? `${escapeHtml(goal.chance_percent)}%` : "not set"}</p>
        <div class="chart-wrap"><canvas id="review-your-chart" aria-label="Your plan donut chart"></canvas></div>
        ${growthSummary(analysis.growth)}
      </article>
      <article class="dashboard-panel">
        <h3>ArthMitra's suggestion · ${comparison.suggested_analysis.score}/100 ·
          ${escapeHtml(comparison.suggested_analysis.grade)}</h3>
        <p>Weighted risk ${escapeHtml(comparison.suggested_analysis.weighted_risk)} · Goal chance
          ${comparison.suggested_analysis.goal
            ? `${escapeHtml(comparison.suggested_analysis.goal.chance_percent)}%` : "not set"}</p>
        <div class="chart-wrap"><canvas id="review-suggested-chart" aria-label="Suggested plan donut chart"></canvas></div>
        ${growthSummary(comparison.suggested_analysis.growth)}
      </article>
    </div>
    ${renderWhyPlanCard(comparison.suggestion_details)}
    <h2>Top fixes</h2>
    ${analysis.top_fixes.length ? `<ol class="fix-list">${analysis.top_fixes.map((fix) => `
      <li><span>${escapeHtml(fix.label)} (${fix.points_lost} points to win back)</span>
        <button type="button" data-apply-fix="${escapeHtml(fix.id)}">Apply this fix</button></li>`).join("")}</ol>`
      : "<p>Your plan has no scored checks to fix right now.</p>"}
    <div class="actions">
      <button id="keep-plan" class="${reviewChoice === "mine" ? "" : "secondary-button"}" type="button">Keep my plan</button>
      <button id="use-plan-suggestion" class="${reviewChoice === "suggested" ? "" : "secondary-button"}" type="button">
        Use ArthMitra's plan</button>
    </div>
    <p id="review-choice" role="status">Selected: ${reviewChoice === "mine" ? "your plan" : "ArthMitra's plan"}.</p>
    <div class="actions">
      <button id="finish-plan" type="button">Go to my dashboard</button>
      <button id="edit-choices" class="secondary-button" type="button">Back to choices</button>
    </div>
    <p>Expected, not guaranteed. Past examples do not predict future results.</p>
  </section>`;
  drawReviewChart("review-your-chart", minePreview.parts);
  drawReviewChart("review-suggested-chart", suggestedPreview.parts);
  document.getElementById("keep-plan").addEventListener("click", () => {
    reviewChoice = "mine";
    document.getElementById("review-choice").textContent = "Selected: your plan.";
  });
  document.getElementById("use-plan-suggestion").addEventListener("click", () => {
    reviewChoice = "suggested";
    document.getElementById("review-choice").textContent = "Selected: ArthMitra's plan.";
  });
  document.querySelectorAll("[data-apply-fix]").forEach((button) =>
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const result = await apiRequest("/plan/apply-fix", {
          method: "POST",
          body: JSON.stringify({ fix_id: button.dataset.applyFix }),
        });
        reviewChoice = "mine";
        setupNotice = result.message;
        await showPlanReview();
      } catch (error) {
        button.disabled = false;
        document.getElementById("review-choice").textContent = error.message;
      }
    }));
  document.getElementById("finish-plan").addEventListener("click", confirmPlanChoice);
  document.getElementById("edit-choices").addEventListener("click", () => navigate("investment-choices"));
  document.getElementById("refresh-market-data")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    const status = document.getElementById("market-refresh-status");
    if (status) status.textContent = "Refreshing public data...";
    try {
      await apiRequest("/market-snapshot/refresh", { method: "POST" });
      await showPlanReview();
    } catch (error) {
      if (status) status.textContent = error.message;
      button.disabled = false;
    }
  });
}

// This function lists five- and ten-year ranges without blending the part returns.
function growthSummary(growth) {
  return `<div><h4>Growth examples · Expected, not guaranteed</h4>
    ${["5", "10"].map((years) => `<p>${years} years:
      Low ${money(growth[years].low)} · Middle ${money(growth[years].mid)} ·
      High ${money(growth[years].high)}.</p>`).join("")}</div>`;
}

// This function draws one side of the plan comparison with exact backend amounts.
function drawReviewChart(canvasId, parts) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !window.Chart) return;
  replaceChart(canvas, {
    type: "doughnut",
    data: {
      labels: parts.map((part) => part.name),
      datasets: [{
        data: parts.map((part) => Number(part.monthly_amount)),
        backgroundColor: ["#2563EB", "#10B981", "#F59E0B", "#6366F1", "#14B8A6", "#D97706", "#64748B"],
      }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}

// This function records the chosen plan and marks setup complete on the server.
async function confirmPlanChoice() {
  const button = document.getElementById("finish-plan");
  button.disabled = true;
  try {
    await apiRequest("/plan/confirm", {
      method: "POST",
      body: JSON.stringify({ choice: reviewChoice }),
    });
    navigate("dashboard");
  } catch (error) {
    button.disabled = false;
    document.getElementById("review-choice").textContent = error.message;
  }
}

// This function presents the where, how, grow and calm-profit learning panels.
async function showInvestmentJourney() {
  app.innerHTML = `<section class="card"><div class="loading"></div><p>Loading your investing journey...</p></section>`;
  try {
    const journey = await apiRequest("/plan/journey");
    app.innerHTML = `<section class="card">
      <h1>Your investing journey</h1>
      <div class="dashboard-panel"><h2>Where</h2>
        ${journey.where.map((part) => `<p><strong>${escapeHtml(part.name)}</strong> ·
          ${escapeHtml(part.share)}% — ${escapeHtml(part.reason)}</p>`).join("")}</div>
      <div class="dashboard-panel"><h2>How</h2>
        ${journey.how.map((part) => `<h3>${escapeHtml(part.name)}</h3>
          <ol>${part.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>`).join("")}</div>
      <div class="dashboard-panel"><h2>Grow</h2>
        <p>Money invested and possible earnings are shown separately. Expected, not guaranteed.</p>
        <div class="chart-wrap"><canvas id="journey-growth-chart" aria-label="Low, middle and high growth examples"></canvas></div>
        ${growthSummary(journey.growth)}
        ${["5", "10"].map((years) => `<p>${years} years · Money invested:
          ${money(journey.growth[years].invested)} · Middle earnings example:
          ${money(journey.growth[years].earned_mid)}.</p>`).join("")}
      </div>
      <div class="dashboard-panel"><h2>Profit, the realistic way</h2>
        <ul>${journey.rules.map((rule) => `<li>${escapeHtml(rule)}</li>`).join("")}</ul>
        <h3>Do</h3><ul>${journey.do.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        <h3>Don't</h3><ul>${journey.dont.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div class="dashboard-panel"><h2>First 30 days plan</h2>
        <p>${journey.completed_tasks} of ${journey.task_count} tasks done.</p>
        ${journey.tasks.map((task) => `<label class="choice">
          <input type="checkbox" data-plan-task="${escapeHtml(task.id)}" ${task.completed ? "checked" : ""} />
          ${escapeHtml(task.title)}</label>`).join("")}
      </div>
      <div class="actions">
        <button id="journey-edit-plan" type="button">Edit my plan</button>
        <button id="journey-dashboard" class="secondary-button" type="button">Back to dashboard</button>
      </div>
    </section>`;
    drawJourneyGrowth(journey.growth);
    document.getElementById("journey-edit-plan").addEventListener("click", () => navigate("investment-choices"));
    document.getElementById("journey-dashboard").addEventListener("click", () => navigate("dashboard"));
    document.querySelectorAll("[data-plan-task]").forEach((input) =>
      input.addEventListener("change", async (event) => {
        try {
          await apiRequest(`/plan/tasks/${encodeURIComponent(event.currentTarget.dataset.planTask)}`, {
            method: "PUT",
            body: JSON.stringify({ completed: event.currentTarget.checked }),
          });
          showInvestmentJourney();
        } catch (error) {
          event.currentTarget.checked = !event.currentTarget.checked;
          renderRetry("Task was not saved", error.message, showInvestmentJourney);
        }
      }));
  } catch (error) {
    renderRetry("Your journey could not load", error.message, showInvestmentJourney);
  }
}

// This function draws the low, middle and high growth bands from backend results.
function drawJourneyGrowth(growth) {
  const canvas = document.getElementById("journey-growth-chart");
  if (!canvas || !window.Chart) return;
  replaceChart(canvas, {
    type: "line",
    data: {
      labels: ["5 years", "10 years"],
      datasets: [
        { label: "Low example", data: [Number(growth["5"].low), Number(growth["10"].low)], borderColor: "#F59E0B" },
        { label: "Middle example", data: [Number(growth["5"].mid), Number(growth["10"].mid)], borderColor: "#2563EB" },
        { label: "High example", data: [Number(growth["5"].high), Number(growth["10"].high)], borderColor: "#10B981" },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}

// This function shows profile details, health, readiness, and account actions.
async function showMyProfile() {
  currentPage = "profile";
  document.getElementById("page-title").textContent = pageTitles.profile;
  try {
    await loadProfile();
    const [health, readiness, smartAmount] = await Promise.all([
      apiRequest("/health-score"),
      apiRequest("/readiness"),
      apiRequest("/smart-monthly-amount"),
    ]);
    const saveMessage = profileSaveNotice ? `<p class="status-chip good" role="status">✓ ${escapeHtml(profileSaveNotice)}</p>` : ""; // Announce a saved preference after refresh.
    profileSaveNotice = ""; // Show the save confirmation only once.
    app.innerHTML = `
      <section class="card">
        <h1>My profile</h1>
        ${saveMessage}
        <div class="result-grid">
          <div class="stat"><strong>Name</strong><p>${escapeHtml((userProfile.email || "").split("@")[0])}</p></div>
          <div class="stat"><strong>Email</strong><p>${escapeHtml(userProfile.email)}</p></div>
          <div class="stat"><strong>Investor type</strong><p>${escapeHtml(userProfile.investor_type || "Not set")}</p>
            <small>Based on your answers about comfort with ups and downs.</small></div>
          <div class="stat"><strong>Health score</strong><p>${health.score} / 100</p>
            <small>${health.top_hurts.map(escapeHtml).join(" ")}</small></div>
          <div class="stat"><strong>Readiness</strong><p>${readiness.ready ? "Basics look ready" : "Fix basics first"}</p></div>
          <div class="stat"><strong>Details last updated</strong><p>${escapeHtml(userProfile.updated_at || "Not yet updated")}</p></div>
        </div>
        ${smartAmountMarkup(smartAmount)}
        <form id="profile-capacity-form" class="profile-grid capacity-editor">
          <h2>Update your monthly amount</h2>
          <label>Is your income steady?
            <select name="income_stability">
              <option value="steady" ${smartAmount.income_stability === "steady" ? "selected" : ""}>Yes, it is steady</option>
              <option value="sometimes_changes" ${smartAmount.income_stability === "sometimes_changes" ? "selected" : ""}>It sometimes changes</option>
              <option value="irregular" ${smartAmount.income_stability === "irregular" ? "selected" : ""}>It is irregular</option>
            </select>
          </label>
          <label>How much do you want to invest each month?
            <input name="wanted_monthly_amount" type="number" min="0" step="0.01"
              value="${escapeHtml(smartAmount.wanted)}" required />
          </label>
          <button type="submit">Save monthly amount</button>
          <p id="capacity-save-status" role="status"></p>
        </form>
        <div class="actions">
          <button id="profile-edit" type="button">Edit money details</button>
          <button id="profile-quiz" class="secondary-button" type="button">Retake risk quiz</button>
          <button id="profile-password" class="secondary-button" type="button">Change password</button>
          <button id="profile-logout" class="secondary-button" type="button">Logout</button>
        </div>
        <div id="profile-action"></div>
      </section>
    `;
    document.getElementById("profile-edit").addEventListener("click", showMoneyDetails);
    bindSmartAmountToggles(); // Bind the profile's step-up comparison.
    document.getElementById("profile-capacity-form").addEventListener("submit", saveProfileCapacity); // Save editable monthly preferences.
    document.getElementById("profile-quiz").addEventListener("click", showRetakeQuiz);
    document.getElementById("profile-password").addEventListener("click", showChangePassword);
    document.getElementById("profile-logout").addEventListener("click", confirmLogout);
  } catch (error) {
    renderRetry("Profile could not load", error.message, showMyProfile);
  }
}

function showAbout() { // Show the app credit, version and learning disclaimer.
  currentPage = "about"; // Keep the navigation marker on the About page.
  document.getElementById("page-title").textContent = pageTitles.about; // Set the short page title.
  app.innerHTML = `<section class="card about-card">
    <h1>About ArthMitra</h1>
    <p class="app-credit">${escapeHtml(APP_CREDIT)}</p>
    <p>Version ${escapeHtml(APP_VERSION)}</p>
    <p>ArthMitra helps you learn about money and compare possible investment choices.</p>
    <p class="report-disclaimer">Educational guidance only. Not licensed financial advice. Investments carry risk. Returns are not guaranteed.</p>
  </section>`; // Keep the About page short and clear.
} // Finish the About page.

async function saveProfileCapacity(event) { // Save only income stability and the monthly amount the user wants.
  event.preventDefault(); // Keep the profile open while the values are saved.
  const form = new FormData(event.currentTarget); // Read the two profile controls.
  const status = document.getElementById("capacity-save-status"); // Find the message shown after saving.
  try { // Show a friendly message for the save or any validation error.
    const result = await apiRequest("/profile/investment-capacity", {
      method: "PATCH",
      body: JSON.stringify({
        income_stability: form.get("income_stability"),
        wanted_monthly_amount: form.get("wanted_monthly_amount"),
      }),
    });
    userProfile = result.profile; // Keep the refreshed profile values.
    profileSaveNotice = result.message; // Show the saved result after the page refreshes.
    await showMyProfile(); // Recalculate all amount cards using the new profile.
  } catch (error) {
    status.textContent = error.message; // Keep the form open and explain what failed.
  }
} // Finish the profile amount save action.

// This function shows a form to edit income, expenses, savings, debts and goals.
async function showMoneyDetails() {
  try {
    await loadProfile();
    const onboarding = await apiRequest("/onboarding/status");
    const isSetup = !onboarding.complete;
    currentPage = isSetup ? "money-details" : "edit-profile";
    document.getElementById("page-title").textContent =
      isSetup ? pageTitles["money-details"] : pageTitles["edit-profile"];
    app.innerHTML = `
      <section class="card">
        ${isSetup ? onboardingProgress(2, "Money details")
          : `<button class="secondary-button" id="cancel-edit" type="button">Back to profile</button>`}
        <h1>${isSetup ? "Your money details" : "Edit money details"}</h1>
        ${isSetup ? "<p>Use monthly amounts. You can save and return to setup later.</p>" : ""}
        ${moneyForm(userProfile)}
      </section>
    `;
    if (!isSetup) document.getElementById("cancel-edit").addEventListener("click", showMyProfile);
    document.getElementById("money-form").addEventListener("submit", saveMoneyDetails);
    document.getElementById("money-form").addEventListener("click", (event) => {
      if (event.target.closest(".remove-row")) {
        event.target.closest("fieldset").remove();
      }
    });
    document.getElementById("add-debt").addEventListener("click", () => addMoneyRow("debt"));
    document.getElementById("add-goal").addEventListener("click", () => addMoneyRow("goal"));
  } catch (error) {
    renderRetry("Profile could not load", error.message, showMoneyDetails);
  }
}

// This function creates the profile form with all saved debts and goals.
function moneyForm(profile = {}) {
  const debts = profile.debts?.length ? profile.debts : [{}];
  const goals = profile.goals?.length ? profile.goals : [{}];
  return `
    <form id="money-form" class="profile-grid">
      <label>Monthly income <input name="income" type="number" min="1" value="${escapeHtml(profile.income)}" required /></label>
      <label>Monthly expenses <input name="expenses" type="number" min="0" value="${escapeHtml(profile.expenses)}" required /></label>
      <label>Savings <input name="savings" type="number" min="0" value="${escapeHtml(profile.savings)}" required /></label>
      <div id="debt-rows"><h2>Debts (optional)</h2>
        ${debts.map(debtRow).join("")}</div>
      <button id="add-debt" type="button" class="secondary-button">Add another debt</button>
      <div id="goal-rows"><h2>Goals (optional)</h2>
        ${goals.map(goalRow).join("")}</div>
      <button id="add-goal" type="button" class="secondary-button">Add another goal</button>
      <button type="submit">Save and continue</button>
      <button id="save-later" class="secondary-button" type="submit">Save and continue later</button>
      <p id="money-error" class="error" role="alert"></p>
    </form>
  `;
}

// This function creates one debt row with the saved name, amount, rate and payment.
function debtRow(debt = {}) {
  return `<fieldset class="question debt-row">
    <legend>Debt</legend>
    <label>Name <input data-field="name" value="${escapeHtml(debt.name)}" /></label>
    <label>Amount <input data-field="amount" type="number" min="0" value="${escapeHtml(debt.amount)}" /></label>
    <label>Interest rate <input data-field="interest_rate" type="number" min="0" max="60" value="${escapeHtml(debt.interest_rate)}" /></label> <!-- Match the supported annual debt-rate range. -->
    <label>Monthly EMI <input data-field="emi" type="number" min="0" value="${escapeHtml(debt.emi)}" /></label>
    <button type="button" class="secondary-button remove-row">Remove debt</button>
  </fieldset>`;
}

// This function creates one goal row with its name, amount and number of years.
function goalRow(goal = {}) {
  return `<fieldset class="question goal-row">
    <legend>Goal</legend>
    <input data-field="id" type="hidden" value="${escapeHtml(goal.id)}" />
    <input data-field="start_date" type="hidden" value="${escapeHtml(goal.start_date)}" />
    <label>Name <input data-field="name" value="${escapeHtml(goal.name)}" /></label>
    <label>Amount <input data-field="amount" type="number" min="1" value="${escapeHtml(goal.amount)}" /></label>
    <label>Years to goal <input data-field="years" type="number" min="1" max="50" value="${escapeHtml(goal.years)}" /></label>
    <button type="button" class="secondary-button remove-row">Remove goal</button>
  </fieldset>`;
}

// This function adds a blank debt or goal row and wires its remove button.
function addMoneyRow(kind) {
  const container = document.getElementById(kind === "debt" ? "debt-rows" : "goal-rows");
  container.insertAdjacentHTML("beforeend", kind === "debt" ? debtRow() : goalRow());
  container.lastElementChild.querySelector(".remove-row").addEventListener("click", (event) =>
    event.currentTarget.closest("fieldset").remove());
}

// This function checks form fields, saves money details, and returns to the profile.
async function saveMoneyDetails(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const debts = [...event.currentTarget.querySelectorAll(".debt-row")].flatMap((row) => {
      const name = row.querySelector('[data-field="name"]').value.trim();
      const amount = row.querySelector('[data-field="amount"]').value;
      if (!name && !amount) return [];
      if (!name || !amount) throw new Error("Please enter both the debt name and amount.");
      return [{
        name,
        amount,
        interest_rate: row.querySelector('[data-field="interest_rate"]').value || "0",
        emi: row.querySelector('[data-field="emi"]').value || "0",
      }];
    });
    const goals = [...event.currentTarget.querySelectorAll(".goal-row")].flatMap((row) => {
      const name = row.querySelector('[data-field="name"]').value.trim();
      const amount = row.querySelector('[data-field="amount"]').value;
      const years = row.querySelector('[data-field="years"]').value;
      if (!name && !amount && !years) return [];
      if (!name || !amount || !years) throw new Error("Please enter a goal name, amount and years.");
      return [{
        id: row.querySelector('[data-field="id"]').value || null,
        start_date: row.querySelector('[data-field="start_date"]').value || null,
        name,
        amount,
        years: Number(years),
      }];
    });
    await apiRequest("/profile", {
      method: "PUT",
      body: JSON.stringify({
        income: form.get("income"),
        expenses: form.get("expenses"),
        savings: form.get("savings"),
        debts,
        goals,
      }),
    });
    await loadProfile();
    if (event.submitter?.id === "save-later") {
      try {
        await apiRequest("/auth/logout", { method: "POST" });
      } catch (logoutError) {
        document.getElementById("money-error").textContent = logoutError.message;
        return;
      }
      token = "";
      localStorage.removeItem(tokenKey);
      history.replaceState({}, "", "#login");
      renderLogin("Your progress is saved. Log in when you are ready to continue.");
      return;
    }
    const onboarding = await apiRequest("/onboarding/status");
    navigate(onboarding.complete ? "plan-review" : onboarding.next_page);
  } catch (error) {
    document.getElementById("money-error").textContent = error.message;
  }
}

// This function checks the saved login and shows the seven risk questions again.
async function showRetakeQuiz() {
  let onboarding;
  try {
    await loadProfile();
    onboarding = await apiRequest("/onboarding/status");
    currentPage = "retake-quiz";
    document.getElementById("page-title").textContent = pageTitles["retake-quiz"];
  } catch (error) {
    renderRetry("We could not check your sign-in", error.message, showRetakeQuiz);
    return;
  }
  const prompts = [
    "If investments fall by 20%, what would you do?",
    "How long can you leave money invested?",
    "How stable is your main income?",
    "How much price movement feels acceptable?",
    "How do you react to uncertain results?",
    "How much investing experience do you have?",
    "Why are you investing?",
  ];
  app.innerHTML = `<section class="card">
    ${onboarding.complete ? "" : onboardingProgress(3, "Risk quiz")}
    <button class="secondary-button" id="back-risk" type="button">
      ${onboarding.complete ? "Back to profile" : "Back to money details"}
    </button>
    <h1>${onboarding.complete ? "Retake your risk quiz" : "How do you feel about risk?"}</h1>
    ${onboarding.complete ? "" : "<p>There are no right or wrong answers. Choose what feels true for you.</p>"}
    <form id="retake-quiz">${prompts.map((prompt, index) => `
      <fieldset class="question"><legend>${index + 1}. ${prompt}</legend>
        ${[1, 2, 3, 4, 5].map((value) => `<label class="choice">
          <input type="radio" name="q${index}" value="${value}" ${value === 3 ? "checked" : ""} required />
          ${["Very low", "Low", "Medium", "High", "Very high"][value - 1]}</label>`).join("")}
      </fieldset>`).join("")}
      <button type="submit">Save and continue</button>
      <button id="quiz-save-later" class="secondary-button" type="submit">Save and continue later</button>
    </form></section>`;
  document.getElementById("back-risk").addEventListener("click", () =>
    navigate(onboarding.complete ? "profile" : "money-details"));
  document.getElementById("retake-quiz").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const answers = Array.from({ length: 7 }, (_, index) => Number(form.get(`q${index}`)));
    try {
      await apiRequest("/risk-quiz", { method: "POST", body: JSON.stringify({ answers }) });
      await loadProfile();
      if (event.submitter?.id === "quiz-save-later") {
        try {
          await apiRequest("/auth/logout", { method: "POST" });
        } catch (logoutError) {
          renderRetry("Progress was saved, but logout failed", logoutError.message, showRetakeQuiz);
          return;
        }
        token = "";
        localStorage.removeItem(tokenKey);
        history.replaceState({}, "", "#login");
        renderLogin("Your progress is saved. Log in when you are ready to continue.");
        return;
      }
      const currentOnboarding = await apiRequest("/onboarding/status");
      navigate(currentOnboarding.complete ? "plan-review" : currentOnboarding.next_page);
    } catch (error) {
      renderRetry("Your answers were not saved", error.message, showRetakeQuiz);
    }
  });
}

// This function displays a safe password form with two matching new-password fields.
function showChangePassword() {
  document.getElementById("profile-action").innerHTML = `
    <form id="password-form" class="profile-grid">
      <h2>Change password</h2>
      <label>Current password <input name="old_password" type="password" autocomplete="current-password" required /></label>
      <label>New password <input name="new_password" type="password" minlength="8" autocomplete="new-password" required /></label>
      <label>Type the new password again <input name="confirm_password" type="password" minlength="8" autocomplete="new-password" required /></label>
      <button type="submit">Change password</button>
      <p id="password-error" class="error" role="alert"></p>
    </form>`;
  document.getElementById("password-form").addEventListener("submit", submitChangePassword);
}

// This function sends the old password and both new entries to the backend.
async function submitChangePassword(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const body = Object.fromEntries(form.entries());
  if (body.new_password !== body.confirm_password) {
    document.getElementById("password-error").textContent = "The new passwords do not match.";
    return;
  }
  try {
    const result = await apiRequest("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(body),
    });
    document.getElementById("password-error").textContent = result.message;
    event.currentTarget.reset();
  } catch (error) {
    document.getElementById("password-error").textContent = error.message;
  }
}

// This function asks before logout and clears the token and personal data if confirmed.
function confirmLogout() {
  app.insertAdjacentHTML("beforeend", `
    <div class="modal-backdrop" id="logout-dialog">
      <section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="logout-title">
        <h2 id="logout-title">Do you want to log out?</h2>
        <div class="actions">
          <button id="confirm-logout" type="button">Yes, log out</button>
          <button id="cancel-logout" class="secondary-button" type="button">Stay</button>
        </div>
      </section>
    </div>`);
  document.getElementById("confirm-logout").focus();
  document.getElementById("cancel-logout").addEventListener("click", () =>
    document.getElementById("logout-dialog").remove());
  document.getElementById("confirm-logout").addEventListener("click", logout);
}

// This function tells the backend, deletes browser sign-in data and returns to login.
async function logout() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch (error) { /* Local sign-out must still work when the server is unreachable. */ }
  token = "";
  userProfile = null;
  currentIdea = null;
  currentIdeas = [];
  destroyCharts();
  localStorage.removeItem(tokenKey);
  localStorage.removeItem("arthmitra-dashboard-visited");
  history.pushState({}, "", "#login");
  renderLogin("You are logged out.");
}

// This function opens the profile dropdown and supports click-outside and Escape closing.
function toggleProfileMenu() {
  const menu = document.getElementById("profile-menu");
  const opening = menu.classList.contains("hidden");
  menu.classList.toggle("hidden", !opening);
  document.getElementById("avatar-button").setAttribute("aria-expanded", String(opening));
}

// This function sends a profile-menu choice to its screen or action.
function handleProfileMenu(event) {
  const choice = event.target.closest("[data-menu]")?.dataset.menu;
  if (!choice) return;
  document.getElementById("profile-menu").classList.add("hidden");
  document.getElementById("avatar-button").setAttribute("aria-expanded", "false");
  if (choice === "profile") navigate("profile");
  if (choice === "edit-profile") navigate("edit-profile");
  if (choice === "retake-quiz") navigate("retake-quiz");
  if (choice === "report") downloadReport();
  if (choice === "about") navigate("about");
  if (choice === "logout") confirmLogout();
}

// This function switches and remembers dark mode.
function toggleTheme() {
  const dark = document.body.classList.toggle("dark");
  localStorage.setItem("arthmitra-theme", dark ? "dark" : "light");
  document.getElementById("theme-button").textContent = dark ? "Light mode" : "Dark mode";
  document.getElementById("profile-menu").classList.add("hidden");
  document.getElementById("avatar-button").setAttribute("aria-expanded", "false");
}

// This function switches between short explanations and detailed finance terms.
function toggleMode() {
  simpleMode = !simpleMode;
  localStorage.setItem("arthmitra-mode", simpleMode ? "simple" : "detailed");
  document.getElementById("mode-button").textContent =
    simpleMode ? "Use detailed mode" : "Use simple mode";
  document.getElementById("profile-menu").classList.add("hidden");
  document.getElementById("avatar-button").setAttribute("aria-expanded", "false");
  const hashPage = routeName();
  navigate(["edit-profile", "retake-quiz"].includes(currentPage) ? currentPage : hashPage, false);
}

// This function opens the report and keeps the existing browser print option.
async function downloadReport() {
  await showReports();
  await new Promise((resolve) => window.setTimeout(resolve, 150));
  window.print();
}

function reportStatusBadge(status) { // Show a status word and icon, not color alone.
  const label = status?.label || status?.severity || "Watch"; // Keep a readable status label.
  const icon = status?.icon || (label === "Good" ? "✓" : "!"); // Add an icon for color-blind readers.
  const kind = status?.kind || label.toLowerCase(); // Pick a color style from the status type.
  return `<span class="report-badge ${escapeHtml(kind)}">${escapeHtml(icon)} ${escapeHtml(label)}</span>`; // Show the accessible badge.
} // Finish the status badge helper.

function reportNote(meaning, status = "Watch") { // Start each report section with two clear lines.
  const label = status === "Good" ? "Good" : status === "Problem" ? "Problem" : "Watch"; // Choose a simple status word.
  const icon = label === "Good" ? "✓" : label === "Problem" ? "!" : "?"; // Pair the word with a clear icon.
  const message = label === "Good" ? "Your saved information has a positive sign." : label === "Problem" ? "Check the problem items and next steps below." : "Check the values and notes below."; // Use short, steady wording.
  return `<div class="report-meaning"><p><strong>What this means:</strong> ${escapeHtml(meaning)}</p><p><strong>Good news / Watch out:</strong> ${icon} ${label}. ${message}</p></div>`; // Return the two-line meaning box.
} // Finish the section meaning helper.

function reportTable(headers, rows, emptyMessage = "") { // Build a mobile-safe report table.
  const body = rows.length
    ? rows.map((row) => `<tr>${row.map((cell) => `<td>${cell || "—"}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${headers.length}">${escapeHtml(emptyMessage || "No saved information yet.")}</td></tr>`; // Show an honest empty row.
  return `<div class="report-table-wrap"><table class="report-table"><thead><tr>${headers.map((header) => `<th scope="col">${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`; // Return a scrollable accessible table.
} // Finish the report table helper.

function reportNumber(value, suffix = "") { // Format saved values without making new financial calculations.
  return value === null || value === undefined ? "—" : `${escapeHtml(value)}${suffix}`; // Keep missing values clear.
} // Finish the report number helper.

function reportMoney(value) { // Show a backend money value in Indian rupee format.
  return value === null || value === undefined ? "—" : escapeHtml(money(value)); // Format only for display.
} // Finish the report money helper.

function renderReportCharts(report) { // Draw charts from the backend's report data.
  destroyCharts(); // Remove old charts before reusing page canvas names.
  const lineOptions = { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: "index" } }; // Keep charts readable on phones.
  const draw = (id, type, labels, datasets, options = {}) => { // Create one chart only when its canvas exists.
    const canvas = document.getElementById(id); // Find this report chart.
    if (!canvas) return; // Skip charts in empty report sections.
    replaceChart(canvas, { type, data: { labels, datasets }, options: { ...lineOptions, ...options } }); // Render the saved values.
  }; // Finish the small chart builder.
  const chartMoney = { ticks: { callback: (value) => money(value) } }; // Format chart axes as Indian rupees.
  const profile = report.profile.chart; // Read the backend profile chart values.
  if (!report.profile.empty) draw("report-profile-chart", "bar", profile.labels, [{ label: "Monthly amount", data: profile.values.map(Number), backgroundColor: "#3977d5" }], { scales: { y: chartMoney } }); // Compare income, spending and remaining money.
  const history = report.past_present.history; // Read saved point-in-time report snapshots.
  const healthHistory = history.filter((row) => row.health_score !== null); // Ignore snapshots from before profile details existed.
  if (healthHistory.length) {
    draw("report-health-chart", "line", healthHistory.map((row) => row.date), [{ label: "Health score", data: healthHistory.map((row) => Number(row.health_score)), borderColor: "#16845b", tension: 0.2 }], { scales: { y: { min: 0, max: 100 } } }); // Show health score changes over time.
  }
  if (history.length && !report.past_present.empty) {
    draw("report-value-chart", "line", history.map((row) => row.date), [
      { label: "Total invested", data: history.map((row) => Number(row.total_invested)), borderColor: "#3977d5", tension: 0.2 },
      { label: "Value today", data: history.map((row) => Number(row.value_today)), borderColor: "#ef8c31", tension: 0.2 },
    ], { scales: { y: chartMoney } }); // Compare saved investments and their current value.
  }
  const logs = report.investment_logs.chart; // Read planned and real monthly amounts.
  if (!report.investment_logs.empty) draw("report-logs-chart", "bar", logs.labels, [
    { label: "Planned", data: logs.planned.map(Number), backgroundColor: "#9ab7eb" },
    { label: "Actual", data: logs.actual.map(Number), backgroundColor: "#3977d5" },
  ], { scales: { y: chartMoney } }); // Compare the plan with logged amounts.
  const donut = report.plan.donut; // Read only the saved plan parts.
  draw("report-plan-chart", "doughnut", donut.labels, [{ label: "Share", data: donut.values.map(Number), backgroundColor: ["#3977d5", "#16845b", "#ef8c31", "#8b5cf6", "#d34c65", "#14a3a3", "#94a3b8"] }]); // Show the chosen plan shares.
  report.goals.forEach((goal, index) => { // Draw planned and real contribution history for every goal.
    draw(`report-goal-chart-${index}`, "line", goal.chart.labels, [
      { label: "Planned contributions", data: goal.chart.planned.map(Number), borderColor: "#9ab7eb", borderDash: [5, 4], tension: 0.2 },
      { label: "Real contributions", data: goal.chart.actual.map(Number), borderColor: "#3977d5", tension: 0.2 },
    ], { scales: { y: chartMoney } }); // Keep each goal chart separate and easy to read.
  }); // Finish the goal chart loop.
  const debt = report.debts.chart; // Read the debt payoff line.
  draw("report-debt-chart", "line", debt.labels, [{ label: "Debt balance", data: debt.balance.map(Number), borderColor: "#c34a4a", tension: 0.2 }], { scales: { y: chartMoney } }); // Show the expected balance path.
  const curve = report.outlook.curve; // Read the three future paths.
  const futureDatasets = [
    { label: "If you follow your plan", data: curve.follow_plan.map(Number), borderColor: "#3977d5", tension: 0.15 },
    { label: "If you invest only what you invested so far", data: curve.invested_so_far.map(Number), borderColor: "#16845b", tension: 0.15 },
    { label: "If you stop investing", data: curve.stop_investing.map(Number), borderColor: "#ef8c31", tension: 0.15 },
  ]; // Keep the three future paths together.
  if (curve.goal_target !== null) futureDatasets.push({ label: `${curve.goal_name} goal`, data: curve.years.map(() => Number(curve.goal_target)), borderColor: "#64748b", borderDash: [4, 5], pointRadius: 0 }); // Add the goal target as a dotted guide.
  draw("report-future-chart", "line", curve.years, futureDatasets, { scales: { x: { title: { display: true, text: "Years from today" } }, y: chartMoney } }); // Never label a scenario as guaranteed.
} // Finish report chart drawing.

function reportSection(id, title, note, content, status = "Watch") { // Wrap one report section in an accessible collapsible panel.
  return `<details class="report-section" id="${escapeHtml(id)}" open><summary>${escapeHtml(title)} ${reportStatusBadge({ label: status, icon: status === "Good" ? "✓" : status === "Problem" ? "!" : "?", kind: status.toLowerCase() })}</summary>${reportNote(note, status)}${content}</details>`; // Keep the section easy to find and open.
} // Finish the report section helper.

function renderReport(report) { // Build all thirteen requested report sections.
  const cards = report.key_cards; // Use the backend's four headline values.
  const profileRows = report.profile.rows.map((row) => [
    escapeHtml(row.item),
    row.item === "Savings rate" || row.item === "Debt-to-income" || row.item === "Emergency fund months"
      ? escapeHtml(row.value)
      : reportMoney(row.value),
    escapeHtml(row.healthy_range),
    reportStatusBadge(row.status),
  ]); // Add profile values and color-independent status labels.
  const journeyRows = report.journey.slice(0, 5).map((step) => [
    escapeHtml(step.step), step.completed_at ? escapeHtml(step.completed_at) : "Not completed yet",
  ]); // Show each setup step with India time.
  const journey = reportTable(["Setup step", "Completed at (Asia/Kolkata)"], journeyRows, "Your setup timeline will appear here."); // Draw the setup timeline table.
  const journeyTotals = report.journey[4] || {}; // Read the attached log summary values.
  const comparisonRows = report.past_present.rows.map((row) => {
    const nonMoney = ["Health score", "Plan score", "Emergency fund months"].includes(row.item) || row.item.startsWith("Goal chance:"); // Keep scores and chances as plain numbers.
    const formatValue = (value) => value === null ? "—" : nonMoney ? reportNumber(value) : reportMoney(value); // Format each past or present value by its unit.
    return [
    escapeHtml(row.item), formatValue(row.past), formatValue(row.present), formatValue(row.change),
    row.change_percent === "New" ? "New" : reportNumber(row.change_percent, "%"), reportStatusBadge({ label: row.arrow, icon: row.arrow === "better" ? "↑" : row.arrow === "worse" ? "↓" : "=", kind: row.arrow }),
  ]; }); // Show changes with arrows and words.
  const planRows = report.plan.parts.map((part) => [
    escapeHtml(part.name), reportNumber(part.share, "%"), reportMoney(part.monthly_amount), escapeHtml(part.risk_words),
    `${reportNumber(part.expected_return_low, "%")} to ${reportNumber(part.expected_return_high, "%")}`,
  ]); // List only parts selected in the saved plan.
  planRows.push(["<strong>Total</strong>", `<strong>${reportNumber(report.plan.total_share, "%")}</strong>`, `<strong>${reportMoney(report.plan.total_monthly)}</strong>`, "", ""]); // Add backend plan totals.
  const checkRows = report.plan.checks.map((check) => [
    escapeHtml(check.name), reportStatusBadge({ label: check.status, icon: check.status === "Good" ? "✓" : "!", kind: check.status.toLowerCase() }),
    `${reportNumber(check.score)} / ${reportNumber(check.max_points)}`, escapeHtml(check.message),
  ]); // Show the plan's five checks.
  const goalsContent = report.goals.map((goal, index) => `
    <article class="report-goal">
      <h3>${escapeHtml(goal.name)}</h3>
      <div class="report-progress" role="progressbar" aria-label="${escapeHtml(goal.name)} goal chance" aria-valuenow="${escapeHtml(goal.chance_now)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${Math.max(0, Math.min(100, Number(goal.chance_now || 0)))}%"></span></div>
      ${reportTable(["Goal", "Target", "Years left", "Invested so far", "Value today", "Planned by now", "Ahead or behind", "Goal chance now", "Catch-up per month"], [[
        escapeHtml(goal.name), reportMoney(goal.target), reportNumber(goal.years_left), reportMoney(goal.invested),
        `${reportMoney(goal.value_today)} (${escapeHtml(goal.value_label)})`, reportMoney(goal.planned_by_now),
        reportMoney(goal.ahead_behind), reportNumber(goal.chance_now, "%"), reportMoney(goal.catch_up_monthly),
      ]])}
      <p>Chance with your plan: ${reportNumber(goal.chance_with_plan, "%")} · Chance with your real investments: ${reportNumber(goal.chance_now, "%")}</p>
      <p>Streak: ${reportNumber(goal.streak_months)} months · Consistency: ${reportNumber(goal.consistency_percent, "%")} · Last updated: ${escapeHtml(goal.last_updated || "Not yet")}</p>
      <p>${escapeHtml(goal.next_step)}</p>
      <div class="report-chart-box"><canvas id="report-goal-chart-${index}" aria-label="Planned and real contributions for ${escapeHtml(goal.name)}"></canvas></div>
      <p class="report-caption">The table above shows the same goal's planned and real contribution amounts.</p>
    </article>`).join(""); // Show goal values, progress and chart.
  const debtRows = report.debts.items.map((debt) => [
    escapeHtml(debt.name), reportMoney(debt.balance), reportNumber(debt.interest_rate, "%"), reportMoney(debt.emi),
    reportNumber(debt.months_left), reportMoney(debt.interest_left),
  ]); // Show every saved debt and its payoff facts.
  const logRows = report.investment_logs.items.map((row) => [
    escapeHtml(row.date_time || "—"), escapeHtml(row.month), reportMoney(row.amount), escapeHtml(row.part || "—"),
    escapeHtml(row.note || "—"), reportStatusBadge({ label: row.status, icon: row.status === "Added" ? "✓" : row.status === "Edited" ? "↻" : "×", kind: row.status.toLowerCase() }),
  ]); // Show saved log history with status words and icons.
  const outlookRows = report.outlook.rows.map((row) => [
    `${reportNumber(row.years)} years`,
    `${reportMoney(row.low.value)} / earned ${reportMoney(row.low.earned)}`,
    `${reportMoney(row.mid.value)} / earned ${reportMoney(row.mid.earned)}`,
    `${reportMoney(row.high.value)} / earned ${reportMoney(row.high.earned)}`,
    reportMoney(row.mid.invested),
  ]); // Show low, middle and high values as backend results.
  const smartGrowth = report.smart_amount_growth; // Read the backend's saved smart-amount future example.
  const smartGrowthContent = smartGrowth.mode === "growth"
    ? `<h3>Smart monthly amount · ${reportMoney(smartGrowth.amount)} each month</h3>
      <p>If you keep investing this amount for 10 years, the middle case is about ${reportMoney(smartGrowth.totals.mid)}. You put in ${reportMoney(smartGrowth.totals.invested)}.</p>
      ${reportTable(["Monthly amount", "Invested", "Low", "Middle", "High", "Goal chance", "Highest expenses allowed", "Room left"], [[
        reportMoney(smartGrowth.amount), reportMoney(smartGrowth.totals.invested),
        reportMoney(smartGrowth.totals.low), reportMoney(smartGrowth.totals.mid),
        reportMoney(smartGrowth.totals.high),
        smartGrowth.goal ? reportNumber(smartGrowth.goal.goal_chance, "%") : "—",
        reportMoney(smartGrowth.expense_limit.highest_expenses_allowed),
        Number(smartGrowth.expense_limit.room_left) < 0
          ? `Over by ${reportMoney(smartGrowth.expense_limit.over_by)}`
          : reportMoney(smartGrowth.expense_limit.room_left),
      ]])}`
    : `<h3>Smart monthly amount</h3><p>${escapeHtml(smartGrowth.message)}</p>`;
  const forecastRows = report.outlook.goal_forecasts.map((goal) => [
    escapeHtml(goal.goal),
    `${reportNumber(goal.low.chance_percent, "%")} / ${reportNumber(goal.low.year_reached, " years")}`,
    `${reportNumber(goal.mid.chance_percent, "%")} / ${reportNumber(goal.mid.year_reached, " years")}`,
    `${reportNumber(goal.high.chance_percent, "%")} / ${reportNumber(goal.high.year_reached, " years")}`,
  ]); // Show possible goal chance and reach year for each case.
  const warningRows = report.warnings.items.map((warning) => [
    reportStatusBadge({ label: warning.severity, icon: warning.icon, kind: warning.severity.toLowerCase() }),
    escapeHtml(warning.what), escapeHtml(warning.why), escapeHtml(warning.action),
  ]); // Show priority warnings in backend order.
  const actionRows = report.actions.items.map((action) => [
    escapeHtml(action.action), escapeHtml(action.why), reportMoney(action.how_much), escapeHtml(action.by_when),
  ]); // Show the next actions and their reasons.
  const checklistKey = "arthmitra-report-checklist"; // Keep checklist ticks on this device.
  let checkedTasks = []; // Start with an empty saved checklist.
  try { checkedTasks = JSON.parse(localStorage.getItem(checklistKey) || "[]"); } // Restore the user's recent checklist ticks.
  catch (error) { localStorage.removeItem(checklistKey); } // Clear unreadable local state instead of breaking the report.
  const checklistRows = report.actions.checklist.map((task, index) => [
    `<input type="checkbox" class="report-checklist-box" data-check-index="${index}" aria-label="Mark ${escapeHtml(task.task)} done" ${checkedTasks.includes(task.task) ? "checked" : ""}>`,
    escapeHtml(task.task),
  ]); // Make the next-month list keyboard friendly.
  const marketRows = (report.market?.items || []).map((item) => [
    escapeHtml(item.name), reportNumber(item.value, "%"),
    item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">Source</a>` : "—",
  ]); // Keep each public market source visible.
  const assumptionRows = report.assumptions.rates.map((item) => [
    escapeHtml(item.idea), reportNumber(item.low, "%"), reportNumber(item.middle, "%"), reportNumber(item.high, "%"),
  ]); // Explain the per-part return ranges.
  const glossaryRows = report.assumptions.glossary.map((item) => [
    escapeHtml(item.term), escapeHtml(item.meaning),
  ]); // Explain money words in simple English.
  const profileContent = report.profile.empty
    ? `<p class="report-empty">Add your money details to see income, spending, savings, and a personal monthly suggestion.</p>`
    : `<p>Healthy ranges are simple guides, not rules for every family.</p>${reportTable(["Item", "Value", "Healthy range", "Status"], profileRows)}<div class="report-chart-box"><canvas id="report-profile-chart" aria-label="Income, expenses, EMI and money left"></canvas></div><p class="report-caption">The table above gives the same amounts as the chart.</p>${smartAmountMarkup(report.monthly_amount_suggestion)}`; // Keep missing profile information from looking like zero values.
  const comparisonContent = report.past_present.empty
    ? `<p class="report-empty">Past and present comparisons will appear after your first saved profile or plan update.</p>`
    : `${reportTable(["Item", `Past (${escapeHtml(report.past_present.past_date || "—")})`, `Present (${escapeHtml(report.past_present.present_date || "—")})`, "Change", "Change %", "Arrow"], comparisonRows)}<div class="report-chart-grid"><div><div class="report-chart-box"><canvas id="report-health-chart" aria-label="Health score over time"></canvas></div><p class="report-caption">Saved health scores over time.</p></div><div><div class="report-chart-box"><canvas id="report-value-chart" aria-label="Total invested compared with value today"></canvas></div><p class="report-caption">Saved total invested and value today.</p></div>${report.investment_logs.empty ? "" : `<div><div class="report-chart-box"><canvas id="report-logs-chart" aria-label="Monthly planned and actual investment amounts"></canvas></div><p class="report-caption">The investment log table below has the amounts behind this chart.</p></div>`}</div>`; // Keep an empty account from showing invented chart points.
  app.innerHTML = `<div class="report-page">
    <header class="report-toolbar">
      <div><h1>My money report</h1><p>${escapeHtml(report.name)} · Generated ${escapeHtml(report.generated_at_local)}</p></div>
      <label>Report period <select id="report-period" aria-label="Choose report period">
        <option value="since_started" ${report.period === "since_started" ? "selected" : ""}>Since I started</option>
        <option value="last_month" ${report.period === "last_month" ? "selected" : ""}>Last month</option>
        <option value="last_3_months" ${report.period === "last_3_months" ? "selected" : ""}>Last 3 months</option>
        <option value="last_6_months" ${report.period === "last_6_months" ? "selected" : ""}>Last 6 months</option>
      </select></label>
      <div class="report-actions"><button id="report-print" type="button">Print</button><button id="report-pdf" type="button">Download PDF</button><button id="report-csv" type="button">Download data (CSV)</button></div>
    </header>
    <nav class="report-toc" aria-label="Report contents"><strong>Jump to</strong>${[
      ["cover", "Summary"], ["profile", "Profile"], ["journey", "Journey"], ["past-present", "Past vs present"],
      ["plan", "Plan"], ["goals", "Goals"], ["debts", "Debts"], ["investment-log", "Investment log"],
      ["future", "Future outlook"], ["warnings", "Warnings"], ["actions", "Action plan"], ["market", "Market data"], ["calculation", "How we calculated"],
    ].map(([id, label]) => `<a href="#report-${id}">${label}</a>`).join("")}</nav>
    ${reportSection("report-cover", "1. COVER AND SUMMARY", "This is a simple view of your saved money details and progress.", `<div class="report-key-cards">
      <div><span>Health score</span><strong>${reportNumber(cards.health_score)} / 100</strong></div>
      <div><span>Plan score</span><strong>${reportNumber(cards.plan_score)} / 100</strong></div>
      <div><span>Goal chance</span><strong>${reportNumber(cards.goal_chance, "%")}</strong></div>
      <div><span>Investor type</span><strong>${escapeHtml(cards.investor_type)}</strong></div>
    </div><p class="report-period-label">${escapeHtml(report.period_label)} · ${escapeHtml(report.period_start || "No past date")} to ${escapeHtml(report.period_end || "Today")}</p><ol class="report-summary">${report.summary.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ol>`, report.report_ready.has_profile ? "Good" : "Watch")}
    ${reportSection("report-profile", "2. YOUR PROFILE TODAY", "This shows income, spending, savings, and monthly debt payments.", profileContent, report.profile.empty ? "Watch" : "Good")}
    ${reportSection("report-journey", "3. YOUR JOURNEY SO FAR", "This timeline shows when each setup step was first completed.", `${journey}<p>Investment log streak: ${reportNumber(journeyTotals.investment_log_streak_months)} months · Consistency: ${reportNumber(journeyTotals.investment_log_consistency_percent, "%")}</p>`, "Good")}
    ${reportSection("report-past-present", "4. PAST VS PRESENT", "This compares the first and latest saved snapshots in your selected period.", comparisonContent, report.past_present.empty ? "Watch" : "Good")}
    ${reportSection("report-plan", "5. YOUR INVESTMENT PLAN", "Only the parts saved in your plan are shown here.", `${report.plan.empty ? `<p class="report-empty">You have not chosen investments yet. <button type="button" data-report-plan-link>Choose my investments</button></p>` : reportTable(["Idea", "Share %", "Each month", "Risk level", "Expected return range"], planRows)}${report.plan.empty ? "" : `<p><strong>Total:</strong> ${reportNumber(report.plan.total_share, "%")} · ${reportMoney(report.plan.total_monthly)} each month</p><div class="report-chart-box report-donut"><canvas id="report-plan-chart" aria-label="Chosen investment parts"></canvas></div><p class="report-caption">The table above shows each selected part and its share.</p><p>Plan score: ${reportNumber(report.plan.plan_score)} / 100 · Risk score: ${reportNumber(report.plan.risk.weighted)} · ${report.plan.risk.within_range ? "Inside" : "Outside"} your ${escapeHtml(report.plan.risk.investor_type || "not set")} range.</p><div class="report-risk-meter" role="img" aria-label="Weighted plan risk ${escapeHtml(report.plan.risk.weighted)} out of 5"><span style="width:${Math.max(0, Math.min(100, Number(report.plan.risk.weighted || 0) * 20))}%"></span></div>${reportTable(["Plan check", "Status", "Score", "What it says"], checkRows, "Save a plan to see its five checks.")}`}<p>Expected, not guaranteed.</p>`, report.plan.empty ? "Watch" : (report.plan.risk.within_range ? "Good" : "Problem"))}
    ${reportSection("report-goals", "6. GOALS", "Goal progress uses real logged amounts and clearly labels estimated values.", goalsContent || `<p class="report-empty">Add a goal to see progress here.</p>`, report.goals.length ? "Good" : "Watch")}
    ${reportSection("report-debts", "7. DEBTS", "This section compares two ways to pay down your saved debts.", `${reportTable(["Debt", "Balance", "Interest rate", "EMI", "Months left", "Total interest left"], debtRows, "You have no debts saved.")}<p>Avalanche: ${reportMoney(report.debts.avalanche.interest)} interest · debt-free ${escapeHtml(report.debts.avalanche.debt_free_date || "date not available")}. Snowball: ${reportMoney(report.debts.snowball.interest)} interest · debt-free ${escapeHtml(report.debts.snowball.debt_free_date || "date not available")}.</p><div class="report-chart-box"><canvas id="report-debt-chart" aria-label="Debt balance over time"></canvas></div><p class="report-caption">The debt table above shows the starting balances and payoff estimates.</p>`, report.debts.empty ? "Good" : "Watch")}
    ${reportSection("report-investment-log", "8. INVESTMENT LOG", "These are your saved monthly updates, including edited and deleted rows.", `${reportTable(["Date and time (Asia/Kolkata)", "Month", "Amount", "Part", "Note", "Status"], logRows, "Log your first investment to see your progress here.")}<p>Planned in the last 12 months: ${reportMoney(report.investment_logs.planned_last_12_months)} · Actual: ${reportMoney(report.investment_logs.actual_last_12_months)}</p>`, report.investment_logs.empty ? "Watch" : "Good")}
    ${reportSection("report-future", "9. FUTURE OUTLOOK", "These are possible outcomes using each saved plan part's own return assumption.", `${report.outlook.empty ? `<p class="report-empty">Save a plan to see possible future outcomes.</p>` : `${reportTable(["Years", "Low case (value / earned)", "Middle case (value / earned)", "High case (value / earned)", "Total invested"], outlookRows)}<div class="report-chart-box"><canvas id="report-future-chart" aria-label="Three possible future paths"></canvas></div><p class="report-caption">The table above shows each case's value, money earned, and total invested.</p><p><strong>In one bad year your plan could temporarily fall by about ${reportNumber(report.outlook.stress_test.fall_percent, "%")} (about ${reportMoney(report.outlook.stress_test.loss)}).</strong></p>${reportTable(["Goal", "Low chance / year reached", "Middle chance / year reached", "High chance / year reached"], forecastRows, "Add a goal to see possible goal outcomes.")}`}${smartGrowthContent}<p><strong>Expected, not guaranteed. These are possible outcomes, not promises.</strong></p>`, report.outlook.empty ? "Watch" : "Good")}
    ${reportSection("report-warnings", "10. WARNINGS AND ALERTS", "These checks point out things you may want to review.", `${reportTable(["Severity", "What we noticed", "Why it matters", "What to do"], warningRows, "No warning matched the saved information.")}<h3>Good news</h3><ul>${report.warnings.good_news.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`, report.warnings.items.some((item) => item.severity === "Problem") ? "Problem" : report.warnings.items.length ? "Watch" : "Good")}
    ${reportSection("report-actions", "11. ACTION PLAN", "Start with the most important next step and tick items as you do them.", `${reportTable(["Action", "Why", "How much", "By when"], actionRows, "Your action list will appear here.")}<h3>Next 30 days</h3>${reportTable(["Done", "Checklist"], checklistRows)}`, "Good")}
    ${reportSection("report-market", "12. MARKET SNAPSHOT", "Public market figures are shown with their source and date.", report.market ? `<p>Data as of ${escapeHtml(report.market.data_as_of)}. ${escapeHtml(report.market.message)}</p>${reportTable(["Market number", "Value", "Source"], marketRows, "No market figures are available.")}` : `<p class="report-empty">No market snapshot is available right now.</p>`, "Watch")}
    ${reportSection("report-calculation", "13. HOW WE CALCULATED", "These numbers use saved information and clear assumptions.", `<h3>Return assumptions for your chosen parts</h3>${reportTable(["Idea", "Low", "Middle", "High"], assumptionRows, "No saved plan return assumptions yet.")}<ul>${report.assumptions.formula_notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ul><h3>Glossary</h3>${reportTable(["Word", "Meaning"], glossaryRows)}<p class="report-disclaimer">${escapeHtml(report.disclaimer)}</p>`, "Good")}
    <footer class="report-footer"><strong>${escapeHtml(report.app_credit || APP_CREDIT)}</strong><br />${escapeHtml(report.disclaimer)}</footer>
  </div>`; // Put every section in the report page.
  document.getElementById("report-period").addEventListener("change", (event) => { // Load data again when the selected period changes.
    reportPeriod = event.target.value; // Remember the chosen report period.
    showReports(); // Refresh all numbers from the report API.
  }); // Finish the period selector.
  document.getElementById("report-print").addEventListener("click", () => window.print()); // Keep the print action.
  document.getElementById("report-pdf").addEventListener("click", downloadReportPdf); // Download the backend-created PDF.
  document.getElementById("report-csv").addEventListener("click", downloadReportCsv); // Download report data as CSV.
  document.querySelector("[data-report-plan-link]")?.addEventListener("click", () => navigate("investment-choices")); // Take new users to Step 4.
  document.querySelectorAll(".report-checklist-box").forEach((checkbox) => { // Save checklist ticks on this device.
    checkbox.addEventListener("change", () => {
      const current = JSON.parse(localStorage.getItem(checklistKey) || "[]"); // Read the current saved tick list.
      const task = report.actions.checklist[Number(checkbox.dataset.checkIndex)]?.task; // Find the checklist wording.
      const next = new Set(current); // Avoid duplicate checklist entries.
      if (checkbox.checked && task) next.add(task); // Save a checked item.
      if (!checkbox.checked && task) next.delete(task); // Remove an unchecked item.
      localStorage.setItem(checklistKey, JSON.stringify([...next])); // Keep the change for the next visit.
    }); // Finish saving one checkbox.
  }); // Finish checklist setup.
  renderReportCharts(report); // Draw the charts after their canvases exist.
  bindSmartAmountToggles(); // Bind the monthly amount example inside the profile section.
} // Finish report rendering.

async function downloadReportFile(path, fallbackName) { // Download an authenticated file from the report API.
  const response = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` } }); // Send the signed-in token.
  if (!response.ok) {
    let detail = "The download could not be created."; // Keep a helpful default message.
    try { detail = (await response.json()).detail || detail; } catch (error) { /* Keep the friendly default for file errors. */ }
    throw new Error(detail); // Show the backend's clear error.
  }
  const blob = await response.blob(); // Read the actual PDF or CSV file.
  const objectUrl = URL.createObjectURL(blob); // Make a temporary browser download link.
  const anchor = document.createElement("a"); // Create a link the browser can download.
  anchor.href = objectUrl; // Point the link to the received file.
  anchor.download = response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] || fallbackName; // Use the backend filename.
  anchor.click(); // Start the download.
  URL.revokeObjectURL(objectUrl); // Release the temporary browser URL.
} // Finish authenticated file download.

async function downloadReportPdf() { // Download a real PDF made by the backend.
  try { await downloadReportFile(`/report/pdf?period=${encodeURIComponent(reportPeriod)}`, "ArthMitra_Report.pdf"); } // Ask the server for the selected period.
  catch (error) { renderRetry("PDF could not download", error.message, showReports); } // Show a useful retry option.
} // Finish the PDF download action.

async function downloadReportCsv() { // Download the report's data as a CSV file.
  try { await downloadReportFile(`/report/csv?period=${encodeURIComponent(reportPeriod)}`, "ArthMitra_Report_data.csv"); } // Ask the server for report rows.
  catch (error) { renderRetry("CSV could not download", error.message, showReports); } // Show a useful retry option.
} // Finish the CSV download action.

// This function displays the full report from the backend's single report-data endpoint.
async function showReports() {
  currentPage = "reports";
  document.getElementById("page-title").textContent = pageTitles.reports;
  app.innerHTML = `<section class="card report-loading" aria-live="polite"><h1>Making your report…</h1><div class="report-skeleton"></div><div class="report-skeleton"></div><div class="report-skeleton"></div></section>`; // Show a friendly loading shape.
  try {
    const report = await apiRequest(`/report/data?period=${encodeURIComponent(reportPeriod)}`); // Load the complete report in one request.
    reportPeriod = report.period; // Keep the period returned by the backend.
    renderReport(report); // Display every report section with its data.
  } catch (error) {
    renderRetry("Report could not load", error.message, showReports);
  }
}

function helpTip(text) { // Add a small keyboard-friendly explanation beside a field.
  const safeText = escapeHtml(text); // Protect the tooltip text before showing it.
  return `<span class="help-tip" tabindex="0" role="img" title="${safeText}" aria-label="${safeText}">?</span>`; // Show the accessible question mark.
} // Finish the help-tip helper.

function goalEditorRow(goal = {}) { // Build one editable goal using only goal fields.
  return `<fieldset class="question section-edit-row goal-row"><!-- Group the fields for one goal. -->
    <legend>Goal</legend><!-- Name this goal group. -->
    <input data-field="id" type="hidden" value="${escapeHtml(goal.id)}" /><!-- Keep this goal's stable ID. -->
    <input data-field="start_date" type="hidden" value="${escapeHtml(goal.start_date)}" /><!-- Keep the goal's original start date. -->
    <label>Goal name ${helpTip("Give this goal a short name.")}<!-- Explain the goal name. -->
      <input data-field="name" maxlength="100" value="${escapeHtml(goal.name)}" required /></label><!-- Pre-fill the goal name. -->
    <label>Goal amount ${helpTip("Enter the amount you want to save.")}<!-- Explain the goal amount. -->
      <input data-field="amount" type="number" min="0.01" step="0.01" value="${escapeHtml(goal.amount)}" required /></label><!-- Pre-fill the goal amount. -->
    <label>Years to reach goal ${helpTip("Choose between 1 and 50 years.")}<!-- Explain the goal timeline. -->
      <input data-field="years" type="number" min="1" max="50" step="1" value="${escapeHtml(goal.years)}" required /></label><!-- Pre-fill the goal timeline. -->
    <button type="button" class="secondary-button" data-section-remove>Remove goal</button><!-- Offer a confirmed goal removal. -->
  </fieldset>`; // Return one accessible goal row.
} // Finish the goal row helper.

function debtEditorRow(debt = {}) { // Build one editable debt using only debt fields.
  return `<fieldset class="question section-edit-row debt-row"><!-- Group the fields for one debt. -->
    <legend>Debt</legend><!-- Name this debt group. -->
    <label>Debt name ${helpTip("Give this debt a short name.")}<!-- Explain the debt name. -->
      <input data-field="name" maxlength="100" value="${escapeHtml(debt.name)}" required /></label><!-- Pre-fill the debt name. -->
    <label>Debt amount ${helpTip("Enter the amount you still owe.")}<!-- Explain the debt amount. -->
      <input data-field="amount" type="number" min="0" step="0.01" value="${escapeHtml(debt.amount)}" required /></label><!-- Pre-fill the debt amount. -->
    <label>Annual interest rate ${helpTip("Enter the yearly rate from 0 to 60 percent.")}<!-- Explain the annual rate. -->
      <input data-field="interest_rate" type="number" min="0" max="60" step="0.01" value="${escapeHtml(debt.interest_rate ?? "0")}" required /></label><!-- Pre-fill the annual rate. -->
    <label>Monthly EMI ${helpTip("Enter the monthly payment amount.")}<!-- Explain the monthly payment. -->
      <input data-field="emi" type="number" min="0" step="0.01" value="${escapeHtml(debt.emi ?? "0")}" required /></label><!-- Pre-fill the monthly payment. -->
    <button type="button" class="secondary-button" data-section-remove>Remove debt</button><!-- Offer a confirmed debt removal. -->
  </fieldset>`; // Return one accessible debt row.
} // Finish the debt row helper.

function closeSectionEditor(kind) { // Close one editor only after checking unsaved changes.
  if (sectionEditorDirty && !window.confirm("You have unsaved changes. Discard them?")) return; // Keep edits when the user cancels.
  sectionEditorDirty = false; // Clear the unsaved-change warning after closing.
  if (kind === "goals") showGoals(); // Return to the goals page.
  else showDebts(); // Return to the debts page.
} // Finish the section editor close action.

function bindSectionEditor(kind) { // Connect add, remove and save controls for one section.
  const form = document.getElementById("section-editor-form"); // Find the section-only form.
  const rows = document.getElementById("section-editor-rows"); // Find the editable row list.
  form.addEventListener("input", () => { sectionEditorDirty = true; }); // Track every typed change.
  form.addEventListener("click", (event) => { // Handle the section buttons from one place.
    if (event.target.closest("#section-editor-add")) { // Add one blank row when requested.
      rows.insertAdjacentHTML("beforeend", kind === "goals" ? goalEditorRow() : debtEditorRow()); // Add only this section's fields.
      sectionEditorDirty = true; // Warn if the new row is discarded.
      rows.lastElementChild.querySelector("input").focus(); // Move keyboard focus to the new row.
      return; // Do not process the new-row button as a remove button.
    } // Finish the add-row action.
    const removeButton = event.target.closest("[data-section-remove]"); // Find a clicked remove button.
    if (!removeButton) return; // Ignore clicks on other form controls.
    const question = kind === "goals" ? "Remove this goal?" : "Remove this debt?"; // Ask the required removal question.
    if (!window.confirm(question)) return; // Keep the row when the user says no.
    removeButton.closest("fieldset").remove(); // Remove only the confirmed row.
    sectionEditorDirty = true; // Warn if the removal is not saved.
  }); // Finish the section button handler.
  document.getElementById("section-editor-cancel").addEventListener("click", () => closeSectionEditor(kind)); // Confirm before closing the editor.
  form.addEventListener("submit", (event) => saveSectionEditor(kind, event)); // Save only the section being edited.
} // Finish the section editor setup.

function showSectionEditor(kind) { // Render a form containing only one profile section.
  if (kind === "goals" && !confirmGoalLogDiscard()) return; // Keep a changed goal log until the user confirms discarding it.
  const isGoals = kind === "goals"; // Choose the matching field list.
  const label = isGoals ? "goals" : "debts"; // Choose the section's simple label.
  const entries = isGoals ? userProfile.goals || [] : userProfile.debts || []; // Load the saved section values.
  const rows = entries.map(isGoals ? goalEditorRow : debtEditorRow).join(""); // Pre-fill each saved row and allow an empty section.
  sectionEditorDirty = false; // Start the newly opened form as unchanged.
  document.getElementById("page-title").textContent = `Edit ${label}`; // Name the page being edited.
  app.innerHTML = `<section class="card section-editor"><!-- Keep the focused editor inside its own card. -->
    <button id="section-editor-cancel" class="secondary-button" type="button">Cancel</button><!-- Provide a keyboard-accessible close action. -->
    <h1>Edit ${label}</h1><!-- Tell the user which details can change. -->
    <p>Change only your ${label}. Your other money details will stay the same.</p><!-- Confirm the partial-update behavior. -->
    <form id="section-editor-form" class="profile-grid section-editor-form"><!-- Keep only this section in the form. -->
      <div id="section-editor-rows">${rows}</div><!-- Show the user's current rows. -->
      <button id="section-editor-add" class="secondary-button" type="button">Add another ${isGoals ? "goal" : "debt"}</button><!-- Let the user add a row. -->
      <p id="section-editor-error" class="error" role="alert"></p><!-- Show friendly save errors. -->
      <button type="submit">Save ${label}</button><!-- Save only the current section. -->
    </form><!-- Finish the section-only form. -->
  </section><!-- Finish the focused editor card. -->`; // Render the editor without the full profile form.
  bindSectionEditor(kind); // Connect the row and form actions.
} // Finish the section editor renderer.

async function saveSectionEditor(kind, event) { // Validate and save just goals or debts.
  event.preventDefault(); // Keep the browser on this page while saving.
  const form = event.currentTarget; // Keep the section form for row reading.
  const errorMessage = document.getElementById("section-editor-error"); // Find the inline error message.
  try { // Catch validation and API errors for the user.
    const entries = [...form.querySelectorAll("fieldset")].flatMap((row) => { // Read each visible row.
      const item = Object.fromEntries([...row.querySelectorAll("[data-field]")].map((input) => [input.dataset.field, input.value.trim()])); // Read each named input.
      const blank = kind === "goals" ? !item.name && !item.amount && !item.years : !item.name && !item.amount; // Ignore an untouched blank row.
      if (blank) return []; // Do not send an empty optional row.
      if (kind === "goals" && (!item.name || !item.amount || !item.years)) throw new Error("Please enter a goal name, amount and years."); // Explain incomplete goal rows.
      if (kind === "debts" && (!item.name || !item.amount || !item.interest_rate || !item.emi)) throw new Error("Please enter a debt name, amount, interest rate and monthly EMI."); // Explain incomplete debt rows.
      if (kind === "goals") return [{ id: item.id || null, start_date: item.start_date || null, name: item.name, amount: item.amount, years: Number(item.years) }]; // Send only the completed goal fields and their stable metadata.
      return [{ name: item.name, amount: item.amount, interest_rate: item.interest_rate, emi: item.emi }]; // Send only the completed debt fields.
    }); // Finish reading the form rows.
    const result = await apiRequest(`/profile/${kind}`, { method: "PATCH", body: JSON.stringify({ [kind]: entries }) }); // Update only the selected profile section.
    sectionEditorDirty = false; // Stop the unsaved-change warning after a successful save.
    profileSaveNotice = result.message; // Show the backend's save confirmation.
    userProfile = result.profile; // Keep the freshly saved profile in memory.
    if (kind === "goals") await showGoals(); // Refresh goals and the recalculated chance.
    else await showDebts(); // Refresh debts, readiness and money left.
  } catch (error) { // Keep the editor open when saving fails.
    errorMessage.textContent = error.message; // Show the friendly validation or API message.
  } // Finish handling the save result.
} // Finish the section-only save action.

function goalDomId(goalId) { // Make a safe HTML ID from the saved goal UUID.
  return String(goalId).replaceAll(/[^a-zA-Z0-9_-]/g, "-"); // Keep only simple ID characters.
} // Finish converting goal IDs.

function goalTimeZone() { // Use the user's saved or browser timezone for displayed dates.
  return localStorage.getItem("arthmitra-timezone") || Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata"; // Default safely to India time.
} // Finish selecting the display timezone.

function formatGoalDateTime(value) { // Show a UTC timestamp in the user's local timezone.
  if (!value) return "Not yet updated"; // Explain when there is no saved timestamp.
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: goalTimeZone(),
  }).format(new Date(value)).replace(/\b(am|pm)\b/gi, (suffix) => suffix.toUpperCase()); // Format display time with the requested AM/PM style.
} // Finish formatting log timestamps.

function formatGoalMonth(value) { // Turn a saved year-month into a short readable label.
  if (!value) return "This month"; // Use a simple label when no month is saved.
  return new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${value}-01T12:00:00Z`)); // Keep the selected calendar month stable across timezones.
} // Finish formatting logged months.

function goalCurrentMonth() { // Read the current year and month in the user's selected timezone.
  const parts = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", timeZone: goalTimeZone() }).formatToParts(new Date()); // Get locale-independent date pieces.
  return `${parts.find((part) => part.type === "year")?.value}-${parts.find((part) => part.type === "month")?.value}`; // Return the stable HTML month value.
} // Finish reading the current month.

function stateForGoal(goalId) { // Keep one page, filter and undo state for each goal.
  if (!goalLogState.has(goalId)) goalLogState.set(goalId, { page: 1, month: "", year: "", undoId: null, undoUntil: null, logs: [] }); // Start with an unfiltered first page.
  return goalLogState.get(goalId); // Return the goal's saved UI state.
} // Finish reading goal UI state.

function confirmGoalLogDiscard() { // Ask before another action closes an unsaved goal form.
  if (!goalLogDirty) return true; // Let unchanged forms close without an extra question.
  if (!window.confirm("You have unsaved changes. Discard them?")) return false; // Keep the form open when the user says no.
  goalLogDirty = false; // Clear the warning after the user confirms.
  return true; // Allow the requested form change.
} // Finish the goal form close check.

function renderGoalHistoryTable(progress, result) { // Build the newest-first monthly update table.
  const goalId = progress.goal.id; // Keep the history tied to its owner-checked goal.
  const state = stateForGoal(goalId); // Restore the last selected page and filters.
  const ideaNames = Object.fromEntries((progress.plan_parts || []).map((part) => [part.idea_id, part.name])); // Match part IDs to simple names.
  const rows = result.logs.map((log) => {
    const canUndo = log.status === "Deleted" && state.undoId === log.id && Date.now() < Date.parse(state.undoUntil || "");
    const actions = log.status === "Deleted"
      ? (canUndo ? `<button type="button" class="secondary-button" data-log-action="undo" data-log-id="${log.id}">Undo</button>` : "—")
      : `<button type="button" class="secondary-button" data-log-action="edit" data-log-id="${log.id}">Edit</button>
         <button type="button" class="secondary-button" data-log-action="delete" data-log-id="${log.id}">Delete</button>`;
    return `<tr class="${log.status === "Deleted" ? "goal-log-deleted" : ""}">
      <td>${escapeHtml(formatGoalDateTime(log.updated_at))}</td>
      <td>${escapeHtml(formatGoalMonth(log.month))}</td>
      <td>${money(log.amount)}</td>
      <td>${escapeHtml(ideaNames[log.part_id] || "—")}</td>
      <td>${escapeHtml(log.note || "—")}</td>
      <td>${escapeHtml(log.status)}</td>
      <td class="goal-log-actions">${actions}</td>
    </tr>`;
  }).join("");
  const firstItem = result.total ? (result.page - 1) * result.page_size + 1 : 0;
  const lastItem = Math.min(result.page * result.page_size, result.total);
  return `<div class="goal-history-table-wrap">
    <table class="goal-history-table">
      <thead><tr><th>Date and time</th><th>Month</th><th>Amount</th><th>Part</th><th>Note</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="7">No updates match these filters.</td></tr>`}</tbody>
    </table>
  </div>
  <div class="goal-history-pages">
    <span>Showing ${firstItem}–${lastItem} of ${result.total}</span>
    <button type="button" class="secondary-button" data-log-action="previous" ${result.page <= 1 ? "disabled" : ""}>Previous</button>
    <span>Page ${result.page} of ${Math.max(1, result.pages)}</span>
    <button type="button" class="secondary-button" data-log-action="next" ${result.page >= result.pages ? "disabled" : ""}>Next</button>
  </div>`;
} // Finish rendering a page of history.

function renderGoalLogForm(progress, log = null) { // Show one new or edited monthly investment form.
  const goal = progress.goal; // Use the goal's saved name and backfill start date.
  const domId = goalDomId(goal.id); // Keep form IDs safe and unique.
  const currentMonth = goalCurrentMonth(); // Use the user's current calendar month.
  const parts = (progress.plan_parts || []).map((part) =>
    `<option value="${escapeHtml(part.idea_id)}" ${log?.part_id === part.idea_id ? "selected" : ""}>${escapeHtml(part.name)}</option>`
  ).join("");
  return `<form class="goal-log-form" id="goal-log-form-${domId}" data-goal-id="${escapeHtml(goal.id)}" data-log-id="${log?.id || ""}">
    <h3>${log ? "Edit this month's investment" : "Update this month's investment"}</h3>
    <label>Goal ${helpTip("This entry belongs to the goal shown above.")}
      <input value="${escapeHtml(goal.name)}" readonly /></label>
    <label>Month ${helpTip("Choose this month or an earlier month after the goal started.")}
      <input name="month" type="month" min="${escapeHtml(goal.start_date.slice(0, 7))}" max="${escapeHtml(currentMonth)}" value="${escapeHtml(log?.month || currentMonth)}" required /></label>
    <label>Amount invested (Rs) ${helpTip("Enter zero to record a skipped month.")}
      <input name="amount" type="number" min="0" step="0.01" value="${escapeHtml(log?.amount ?? "0")}" required /></label>
    <label>Idea or part (optional) ${helpTip("Pick a part from your saved plan, or leave it blank.")}
      <select name="part_id"><option value="">Not chosen</option>${parts}</select></label>
    <label>Note (optional) ${helpTip("Keep this note under 200 characters.")}
      <textarea name="note" maxlength="200">${escapeHtml(log?.note || "")}</textarea></label>
    <div class="actions">
      <button type="submit">${log ? "Save edit" : "Save update"}</button>
      <button type="button" class="secondary-button" data-goal-skip>Skipped this month</button>
      <button type="button" class="secondary-button" data-goal-form-cancel>Cancel</button>
    </div>
    <p class="error" data-goal-form-error role="alert"></p>
    <div class="goal-duplicate-choice" data-goal-duplicate></div>
  </form>`;
} // Finish building the monthly investment form.

function showGoalLogForm(progress, log = null) { // Open and connect one goal's monthly log form.
  if (!confirmGoalLogDiscard()) return; // Do not replace an unsaved value or log form without asking.
  const goalId = progress.goal.id; // Keep the form attached to its goal.
  const domId = goalDomId(goalId); // Find the matching form slot.
  const slot = document.getElementById(`goal-log-form-slot-${domId}`); // Place the form inside this goal card.
  slot.innerHTML = renderGoalLogForm(progress, log); // Render the saved values or an empty form.
  const form = document.getElementById(`goal-log-form-${domId}`); // Find the new form.
  let pendingPayload = null; // Keep the user's entry while they choose how to handle a duplicate.
  form.addEventListener("input", () => { goalLogDirty = true; }); // Track unsaved edits.
  form.querySelector("[data-goal-form-cancel]").addEventListener("click", () => {
    if (goalLogDirty && !window.confirm("You have unsaved changes. Discard them?")) return; // Keep the form open when the user cancels.
    goalLogDirty = false; // Clear the close warning after canceling.
    slot.innerHTML = ""; // Close only this form.
  }); // Finish the cancel action.
  form.querySelector("[data-goal-skip]").addEventListener("click", () => {
    form.elements.amount.value = "0"; // Save a skipped month as an honest zero.
    form.requestSubmit(); // Use the same validation and save path as a normal entry.
  }); // Finish the skipped-month action.

  const savePayload = async (addToMonth = false) => {
    const payload = { ...pendingPayload, add_to_month: addToMonth }; // Add an explicit duplicate-month choice.
    const editId = form.dataset.logId; // Keep edits attached to their existing audit row.
    try {
      const result = await apiRequest(
        editId ? `/logs/${editId}` : `/goals/${goalId}/logs`,
        { method: editId ? "PUT" : "POST", body: JSON.stringify(payload) },
      ); // Save through the owner-checked API.
      if (result.needs_choice) {
        const duplicate = form.querySelector("[data-goal-duplicate]"); // Find the duplicate decision area.
        duplicate.innerHTML = `<p role="status">${escapeHtml(result.message)}</p>
          <div class="actions">
            <button type="button" data-duplicate-add>Add to it</button>
            ${result.existing_logs.map((item) =>
              `<button type="button" class="secondary-button" data-duplicate-edit="${item.id}">
                Edit ${escapeHtml(formatGoalMonth(item.month))} · ${money(item.amount)}
              </button>`
            ).join("")}
          </div>`; // Offer add-to-month or edit-existing choices.
        duplicate.querySelector("[data-duplicate-add]").addEventListener("click", () => savePayload(true)); // Save a second entry only after the user confirms.
        duplicate.querySelectorAll("[data-duplicate-edit]").forEach((button) =>
          button.addEventListener("click", () => {
            const existing = result.existing_logs.find((item) => item.id === Number(button.dataset.duplicateEdit)); // Find the selected existing row.
            if (existing) showGoalLogForm(progress, existing); // Open that row in the edit form.
          })); // Finish connecting each edit choice.
        return; // Wait for the user's explicit duplicate choice.
      }
      goalLogDirty = false; // Stop warning after the save succeeds.
      goalLogWarnings.set(goalId, result.warnings || []); // Keep non-blocking amount warnings visible.
      profileSaveNotice = result.message; // Announce the completed save.
      await showGoals(); // Refresh real progress, history and charts from the backend.
    } catch (error) {
      form.querySelector("[data-goal-form-error]").textContent = error.message; // Show validation and save errors clearly.
    }
  }; // Finish the shared save action.

  form.addEventListener("submit", (event) => {
    event.preventDefault(); // Keep the user on the goal page.
    const month = form.elements.month.value; // Read the selected calendar month.
    pendingPayload = {
      month: `${month}-01`,
      amount: form.elements.amount.value,
      part_id: form.elements.part_id.value || null,
      note: form.elements.note.value,
    }; // Send only the log values the user entered.
    savePayload(false); // Let the API check whether this month already has a log.
  }); // Finish submitting a new or edited log.
} // Finish opening the monthly form.

function showGoalValueForm(progress) { // Open the optional real-value snapshot form.
  if (!confirmGoalLogDiscard()) return; // Keep an unsaved log form open unless the user agrees to discard it.
  const goal = progress.goal; // Keep the snapshot linked to this goal.
  const domId = goalDomId(goal.id); // Find the matching value form slot.
  const slot = document.getElementById(`goal-value-form-slot-${domId}`); // Place the form inside the goal card.
  const value = progress.latest_value_snapshot?.value || ""; // Prefill the latest actual value if one exists.
  slot.innerHTML = `<form class="goal-log-form" id="goal-value-form-${domId}">
    <h3>Today's value of my investments for this goal</h3>
    <label>Value today (Rs) ${helpTip("Copy the current value from your app or statement.")}
      <input name="value" type="number" min="0" step="0.01" value="${escapeHtml(value)}" required /></label>
    <div class="actions"><button type="submit">Save today's value</button>
      <button type="button" class="secondary-button" data-value-cancel>Cancel</button></div>
    <p class="error" data-value-error role="alert"></p>
  </form>`; // Show one dated value input.
  const form = document.getElementById(`goal-value-form-${domId}`); // Find the snapshot form.
  form.addEventListener("input", () => { goalLogDirty = true; }); // Track unsaved value changes.
  form.querySelector("[data-value-cancel]").addEventListener("click", () => {
    if (goalLogDirty && !window.confirm("You have unsaved changes. Discard them?")) return; // Keep a changed snapshot form open.
    goalLogDirty = false; // Clear the close warning.
    slot.innerHTML = ""; // Close only this snapshot form.
  }); // Finish the cancel action.
  form.addEventListener("submit", async (event) => {
    event.preventDefault(); // Keep the user on the goal page.
    try {
      const result = await apiRequest(`/goals/${goal.id}/value`, {
        method: "POST",
        body: JSON.stringify({ value: form.elements.value.value }),
      }); // Save a dated actual-value snapshot.
      goalLogDirty = false; // Stop warning after the snapshot is saved.
      profileSaveNotice = result.message; // Announce the snapshot update.
      await showGoals(); // Refresh the actual-value label and progress.
    } catch (error) {
      form.querySelector("[data-value-error]").textContent = error.message; // Keep validation errors beside the field.
    }
  }); // Finish saving the snapshot.
} // Finish opening the real-value form.

async function loadGoalHistory(progress) { // Load one goal's history page and connect its controls.
  const goalId = progress.goal.id; // Use the stable goal ID for every query.
  const domId = goalDomId(goalId); // Find the matching history panel.
  const root = document.getElementById(`goal-history-${domId}`); // Keep history inside this card.
  if (!root) return; // Stop if the user left the page.
  const state = stateForGoal(goalId); // Restore the current filters and page.
  const query = new URLSearchParams({ page: String(state.page) }); // Keep pagination in the API query.
  if (state.month) query.set("month", state.month); // Filter by calendar month when selected.
  if (state.year) query.set("year", state.year); // Filter by year when selected.
  root.querySelector("[data-history-results]").innerHTML = "<p>Loading updates...</p>"; // Show a clear loading state.
  try {
    const result = await apiRequest(`/goals/${goalId}/logs?${query}`); // Load the owner-filtered history.
    state.logs = result.logs; // Keep this page's rows for edit actions.
    root.querySelector("[data-history-results]").innerHTML = renderGoalHistoryTable(progress, result); // Show newest rows first.
  } catch (error) {
    root.querySelector("[data-history-results]").innerHTML = `<p class="error">${escapeHtml(error.message)}</p>
      <button type="button" class="secondary-button" data-history-retry>Try again</button>`; // Make failures visible and retryable.
    root.querySelector("[data-history-retry]").addEventListener("click", () => loadGoalHistory(progress)); // Retry only this history panel.
  }
} // Finish loading one goal's history.

async function deleteGoalLog(progress, logId) { // Soft-delete one history row after asking first.
  if (!window.confirm("Delete this update? You can undo it for 10 seconds.")) return; // Confirm before removing a row.
  try {
    const result = await apiRequest(`/logs/${logId}`, { method: "DELETE" }); // Keep the record as a soft-deleted history row.
    const state = stateForGoal(progress.goal.id); // Store the short undo window for this goal.
    state.undoId = Number(logId); // Show Undo beside the deleted row.
    state.undoUntil = result.undo_until; // Stop offering Undo after the backend deadline.
    profileSaveNotice = result.message; // Confirm the delete and explain the undo period.
    setTimeout(() => {
      state.undoId = null; // Expire the one-time undo control.
      if (currentPage === "goals") loadGoalHistory(progress); // Refresh the status after ten seconds.
    }, 10100); // Match the server's ten-second undo limit.
    await showGoals(); // Recalculate totals without the deleted row.
  } catch (error) {
    profileSaveNotice = error.message; // Show an API error without hiding the history.
    await showGoals(); // Refresh the page to show the current server state.
  }
} // Finish soft-deleting a goal log.

async function undoGoalLog(progress, logId) { // Restore a deleted row during the undo window.
  try {
    const result = await apiRequest(`/logs/${logId}/undo`, { method: "POST" }); // Ask the backend to restore this owned row.
    const state = stateForGoal(progress.goal.id); // Find this goal's undo state.
    state.undoId = null; // Remove the undo button after it is used.
    state.undoUntil = null; // Clear the expired undo timestamp.
    profileSaveNotice = result.message; // Confirm that the row is back.
    await showGoals(); // Refresh the total and charts.
  } catch (error) {
    profileSaveNotice = error.message; // Explain when the undo window has passed.
    await showGoals(); // Show the current saved state.
  }
} // Finish restoring a goal log.

async function downloadGoalLogs(goalId) { // Download this goal's history using the signed-in token.
  try {
    const response = await fetch(`${API_URL}/goals/${goalId}/logs/export`, {
      headers: { Authorization: `Bearer ${token}` },
    }); // Keep the CSV request authenticated.
    if (!response.ok) throw new Error("The CSV could not download. Please try again."); // Report download failures directly.
    const blob = await response.blob(); // Read the server-created CSV file.
    const url = URL.createObjectURL(blob); // Make a temporary browser download link.
    const link = document.createElement("a"); // Create a short-lived download control.
    link.href = url; // Point it at the downloaded file.
    link.download = `goal-${goalId}-logs.csv`; // Give the file a clear name.
    link.click(); // Start the user's download.
    URL.revokeObjectURL(url); // Release the temporary browser URL.
  } catch (error) {
    const message = document.getElementById(`goal-log-message-${goalDomId(goalId)}`); // Find this goal's status area.
    if (message) message.textContent = error.message; // Show a friendly download error.
  }
} // Finish downloading goal history.

function bindGoalCard(progress) { // Connect forms, filters and history actions for one goal.
  const goal = progress.goal; // Keep all actions attached to this goal.
  const domId = goalDomId(goal.id); // Find the card created for this UUID.
  const card = document.getElementById(`goal-card-${domId}`); // Find the card's action area.
  card.querySelector("[data-goal-log-open]").addEventListener("click", () => showGoalLogForm(progress)); // Open the monthly contribution form.
  card.querySelector("[data-goal-value-open]").addEventListener("click", () => showGoalValueForm(progress)); // Open the actual-value form.
  card.querySelector("[data-goal-edit]").addEventListener("click", () => showSectionEditor("goals")); // Reuse the goals-only editor.
  card.querySelector("[data-history-month]").addEventListener("change", (event) => {
    const state = stateForGoal(goal.id); // Keep each filter with its goal.
    state.month = event.target.value; // Save the selected month.
    state.page = 1; // Return to the first result page.
    loadGoalHistory(progress); // Apply the month filter.
  }); // Finish the month filter.
  card.querySelector("[data-history-year]").addEventListener("change", (event) => {
    const state = stateForGoal(goal.id); // Keep each filter with its goal.
    state.year = event.target.value; // Save the selected year.
    state.page = 1; // Return to the first result page.
    loadGoalHistory(progress); // Apply the year filter.
  }); // Finish the year filter.
  card.querySelector("[data-history-export]").addEventListener("click", () => downloadGoalLogs(goal.id)); // Download this goal's history.
  card.addEventListener("click", (event) => {
    const button = event.target.closest("[data-log-action]"); // Find a clicked history or pagination control.
    if (!button) return; // Ignore clicks elsewhere in the card.
    const logId = Number(button.dataset.logId); // Read the selected saved log ID.
    if (button.dataset.logAction === "edit") {
      const existing = stateForGoal(goal.id).logs.find((log) => log.id === logId); // Find the selected history row.
      if (existing) showGoalLogForm(progress, existing); // Pre-fill only that update for editing.
    } else if (button.dataset.logAction === "delete") {
      deleteGoalLog(progress, logId); // Confirm then soft-delete this update.
    } else if (button.dataset.logAction === "undo") {
      undoGoalLog(progress, logId); // Restore this update during its undo window.
    } else if (button.dataset.logAction === "previous" || button.dataset.logAction === "next") {
      const state = stateForGoal(goal.id); // Keep page movement per goal.
      state.page += button.dataset.logAction === "next" ? 1 : -1; // Move by one server page.
      loadGoalHistory(progress); // Load the requested page.
    }
  }); // Finish the card action handler.
  loadGoalHistory(progress); // Load the first ten rows for this goal.
} // Finish connecting one goal card.

function renderGoalCard(progress) { // Build the plan and real-investment summary for one goal.
  const goal = progress.goal; // Read the backend goal and its saved progress.
  const domId = goalDomId(goal.id); // Build stable IDs for this goal's controls.
  const nowParts = new Intl.DateTimeFormat("en-US", { year: "numeric", timeZone: goalTimeZone() }).formatToParts(new Date()); // Read the user's current year.
  const currentYear = Number(nowParts.find((part) => part.type === "year")?.value || new Date().getFullYear()); // Set the year filter's upper bound.
  const startYear = Number(goal.start_date.slice(0, 4)); // Set the year filter's lower bound.
  const years = Array.from({ length: Math.max(1, currentYear - startYear + 1) }, (_, index) => startYear + index); // Offer each possible backfill year.
  const state = stateForGoal(goal.id); // Keep the user's current filters.
  const warnings = goalLogWarnings.get(goal.id) || []; // Read non-blocking warnings from the latest save.
  const aheadLabel = progress.ahead_behind_direction === "ahead" ? "Ahead" : "Behind"; // Use the backend's checked comparison.
  const aheadColor = progress.ahead_behind_direction === "ahead" ? "goal-ahead" : "goal-behind"; // Color only the status label.
  const months = Array.from({ length: 12 }, (_, index) => `<option value="${index + 1}" ${state.month === String(index + 1) ? "selected" : ""}>${new Intl.DateTimeFormat("en-IN", { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(2020, index, 1)))}</option>`).join(""); // Show every month in the filter.
  return `<article class="dashboard-panel goal-card" id="goal-card-${domId}">
    <div class="goal-card-heading"><div><h2>${escapeHtml(goal.name)}</h2>
      <p>${money(goal.amount)} goal · ${escapeHtml(goal.years)} years</p></div>
      <button type="button" class="secondary-button" data-goal-edit>Edit goal</button></div>
    <progress value="${escapeHtml(progress.value_progress_percent)}" max="100" aria-label="${escapeHtml(goal.name)} actual value progress"></progress>
    <p>Chance with your plan: <strong>${escapeHtml(progress.chance_with_plan)}%</strong></p>
    <p>Chance with your real investments: <strong>${escapeHtml(progress.chance_with_real_investments)}%</strong></p>
    <div class="dashboard-grid goal-stats">
      <div class="stat"><strong>Total invested</strong><p>${money(progress.total_invested)}</p></div>
      <div class="stat"><strong>Value today</strong><p>${money(progress.value_today)}</p><span class="tag">${escapeHtml(progress.value_label)}</span></div>
      <div class="stat"><strong>${aheadLabel} your plan</strong><p class="${aheadColor}">${money(progress.ahead_behind_amount)}</p>
        <small>${escapeHtml(progress.ahead_behind_percent)}% ${aheadLabel.toLowerCase()}</small></div>
      <div class="stat"><strong>Next step</strong><p>${escapeHtml(progress.next_step)}</p></div>
    </div>
    <p class="goal-friendly-message ${aheadColor}" role="status">${escapeHtml(progress.friendly_message)}</p>
    <p>Streak: ${escapeHtml(progress.streak_months)} months · Consistency: ${escapeHtml(progress.consistency_percent)}%</p>
    <p>Last updated: ${escapeHtml(formatGoalDateTime(progress.last_updated))}</p>
    ${warnings.length ? `<div class="status goal-warnings" role="status">${warnings.map(escapeHtml).join(" ")}</div>` : ""}
    <div class="actions">
      <button type="button" data-goal-log-open>Update this month's investment</button>
      <button type="button" class="secondary-button" data-goal-value-open>Today's value of my investments</button>
    </div>
    <p id="goal-log-message-${domId}" class="status" role="status"></p>
    <div id="goal-log-form-slot-${domId}"></div>
    <div id="goal-value-form-slot-${domId}"></div>
    <section class="goal-history" id="goal-history-${domId}">
      <div class="goal-history-heading"><h3>Previous updates</h3>
        <button type="button" class="secondary-button" data-history-export>Download CSV</button></div>
      <div class="goal-history-filters">
        <label>Month <select data-history-month><option value="">All months</option>${months}</select></label>
        <label>Year <select data-history-year>
          <option value="">All years</option>
          ${years.map((year) => `<option value="${year}" ${state.year === String(year) ? "selected" : ""}>${year}</option>`).join("")}
        </select></label>
      </div>
      <div data-history-results><p>Loading updates...</p></div>
    </section>
  </article>`;
} // Finish one goal progress card.

// This function lists goals, progress and the latest plan-based chance.
async function showGoals() { // Render progress from real logs rather than profile savings.
  currentPage = "goals"; // Remember which section is open.
  document.getElementById("page-title").textContent = pageTitles.goals; // Keep the page heading correct after an edit.
  try { // Load fresh saved values before showing the page.
    await loadProfile(); // Refresh the profile values.
    const [health, savedPlan, goalList] = await Promise.all([
      apiRequest("/health-score"),
      apiRequest("/plan"),
      apiRequest("/goals"),
    ]); // Refresh the health score, saved plan and stable goal IDs.
    const goals = goalList.goals || []; // Read goals from the owner-only endpoint.
    userProfile.goals = goals; // Keep goal IDs and dates available to the goals editor.
    const progressRows = await Promise.all(
      goals.map((goal) => apiRequest(`/goals/${goal.id}/progress`)),
    ); // Calculate each goal on the backend.
    const saveMessage = profileSaveNotice ? `<p class="status" role="status">${escapeHtml(profileSaveNotice)}</p>` : ""; // Announce a successful save.
    profileSaveNotice = ""; // Show the save message only once.
    const planNotice = savedPlan.exists && savedPlan.is_stale ? `<div class="dashboard-panel" role="status">Your goals/debts changed. Re-check your plan.</div>` : ""; // Keep the plan reminder visible until review.
    app.innerHTML = `<section class="card"><h1>Your goals</h1>
      ${saveMessage}
      ${planNotice}
      <p>Health score: ${health.score} / 100</p>
      ${progressRows.length ? progressRows.map(renderGoalCard).join("") : "<p>You have not added any goals.</p>"}
      <button id="edit-goals" type="button">Edit goals</button></section>`;
    document.getElementById("edit-goals").addEventListener("click", () => showSectionEditor("goals")); // Open only the goals editor.
    progressRows.forEach(bindGoalCard); // Connect each goal's log form, history and charts.
  } catch (error) { // Keep failures visible and retryable.
    renderRetry("Goals could not load", error.message, showGoals); // Show a friendly retry action.
  } // Finish loading the goals page.
} // Finish rendering the goals page.

// This function lists debts and the refreshed readiness and budget numbers.
async function showDebts() { // Render only debt details and their updated calculations.
  currentPage = "debts"; // Remember which section is open.
  document.getElementById("page-title").textContent = pageTitles.debts; // Keep the page heading correct after an edit.
  try { // Load fresh saved values before showing the page.
    await loadProfile(); // Refresh the profile values.
    const [health, readiness, savedPlan] = await Promise.all([apiRequest("/health-score"), apiRequest("/readiness"), apiRequest("/plan")]); // Refresh debt calculations and plan status.
    const debts = userProfile.debts || []; // Read the saved debt rows.
    const saveMessage = profileSaveNotice ? `<p class="status" role="status">${escapeHtml(profileSaveNotice)}</p>` : ""; // Announce a successful save.
    profileSaveNotice = ""; // Show the save message only once.
    const planNotice = savedPlan.exists && savedPlan.is_stale ? `<div class="dashboard-panel" role="status">Your goals/debts changed. Re-check your plan.</div>` : ""; // Keep the plan reminder visible until review.
    app.innerHTML = `<section class="card"><h1>Your debts</h1><!-- Keep this page focused on debts. -->
      ${saveMessage}<!-- Show the latest save confirmation. -->
      ${planNotice}<!-- Remind the user to review a saved plan. -->
      <p>Readiness: ${readiness.ready ? "Basics look ready" : "Fix basics first"}</p><!-- Show refreshed readiness. -->
      <p>Debt-to-income: ${escapeHtml(health.debt_to_income_ratio)}%</p><!-- Show the refreshed debt ratio. -->
      <p>Monthly money left: ${money(health.monthly_left)}</p><!-- Show the refreshed monthly balance. -->
      <p>Health score: ${health.score} / 100</p><!-- Show the refreshed health score. -->
      ${debts.length ? `<div class="result-grid">${debts.map((debt) => `<div class="stat"><!-- Show one saved debt. -->
        <h2>${escapeHtml(debt.name)}</h2><p>Left to pay: ${money(debt.amount)}</p><!-- Show the current debt balance. -->
        <p>Interest: ${escapeHtml(debt.interest_rate)}% · Monthly payment: ${money(debt.emi)}</p><!-- Show the current payment facts. -->
        ${Number(debt.interest_rate) > 15 ? "<p>High interest: focus on this before taking extra investment risk.</p>" : ""}<!-- Explain costly debt. -->
      </div><!-- Finish this saved debt. -->`).join("")}</div>` : "<p>You have not added any debts.</p>"}<!-- Explain when no debts are saved. -->
      <button id="edit-debts" type="button">Edit debts</button></section><!-- Open the debts-only editor. -->`; // Render the updated debts.
    document.getElementById("edit-debts").addEventListener("click", () => showSectionEditor("debts")); // Open only the debts editor.
  } catch (error) { // Keep failures visible and retryable.
    renderRetry("Debts could not load", error.message, showDebts); // Show a friendly retry action.
  } // Finish loading the debts page.
} // Finish rendering the debts page.

// This function shows a few short lessons about regular investing and risk.
function showLearn() {
  currentPage = "learn";
  const tooltips = [
    ["SIP", "A SIP is a set amount you invest again each month."],
    ["Diversification", "Diversification means spreading money across different places."],
    ["Inflation", "Inflation means the same money buys less as prices rise."],
    ["Compounding", "Compounding means your earnings can earn too."],
    ["Liquidity", "Liquidity means how quickly you can get your money back."],
    ["Returns", "Returns are how much your money grows or falls."],
    ["Risk", "Risk means your money's value can change or fall."],
    ["Equity", "Equity means owning a small part of a company."],
    ["Debt fund", "A debt fund lends money to borrowers through a shared fund."],
    ["Demat account", "A demat account keeps shares in an electronic account."],
  ];
  app.innerHTML = `<section class="card"><h1>Learn the basics</h1>
    <div class="result-grid">
      <div class="stat"><h2>What is risk?</h2><p>Like crossing a road: more speed can mean more danger and reward.</p></div>
      <div class="stat"><h2>What is a SIP?</h2><p>Saving one fixed amount each month, like pocket money in a jar.</p></div>
      <div class="stat"><h2>What is compounding?</h2><p>Your earnings may earn too, like a growing snowball.</p></div>
      <div class="stat"><h2>What is diversification?</h2><p>Do not keep all eggs in one basket.</p></div>
    </div>
    <h2>Money words</h2>
    <div class="result-grid">${tooltips.map(([term, meaning]) => `
      <p class="stat"><abbr class="term" title="${escapeHtml(meaning)}">${escapeHtml(term)} <span aria-hidden="true">?</span></abbr>
      — ${escapeHtml(meaning)}</p>`).join("")}</div>
    ${simpleMode ? "" : `<div class="dashboard-panel"><h2>Detailed mode</h2>
      <p>SIP future value uses monthly rate r and number of months n:
        FV = P × (((1 + r)^n − 1) / r) × (1 + r).</p>
      <p>Every result is an estimate based on an assumption.</p></div>`}
    <button id="learn-ideas" type="button">Browse investment ideas</button></section>`;
  document.getElementById("learn-ideas").addEventListener("click", () => navigate("ideas"));
}

// This function collects a question for the AI coach.
async function showCoach() {
  currentPage = "coach";
  app.innerHTML = `<section class="card"><h1>AI coach</h1>
    <p>This learning helper uses your saved profile and real calculator results.</p>
    <form id="coach-form" class="form-grid">
      <label>Your question <input name="question" required /></label>
      <button type="submit">Ask</button>
    </form><div id="coach-answer" role="status" aria-live="polite"></div>
  </section>`;
  document.getElementById("coach-form").addEventListener("submit", answerCoachQuestion);
}

// This function sends the full question to the backend coach.
async function answerCoachQuestion(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const target = document.getElementById("coach-answer");
  target.className = "coach-answer";
  target.setAttribute("role", "status");
  target.textContent = "The coach is thinking...";
  try {
    const result = await apiRequest("/chat", {
      method: "POST",
      body: JSON.stringify({ question: form.get("question") }),
    });
    target.innerHTML = `<p>${escapeHtml(result.answer)}</p>`;
  } catch (error) {
    target.className = "coach-answer error-card";
    target.setAttribute("role", "alert");
    target.innerHTML = `<strong>We couldn't get an answer to that question.</strong>
      <p>${escapeHtml(error.message)}</p>
      <button id="retry-coach" type="button">Try again</button>`;
    document.getElementById("retry-coach").addEventListener("click", () => {
      document.getElementById("coach-form").requestSubmit();
    });
  }
}

// This function shows a friendly retry card for a page that could not load.
function renderRetry(title, message, retry) {
  app.innerHTML = `<section class="card"><h1>${escapeHtml(title)}</h1>
    <p>${escapeHtml(message)}</p><button id="retry-view" type="button">Try again</button></section>`;
  document.getElementById("retry-view").addEventListener("click", retry);
}

// This function starts the requested page only after checking the saved login token.
async function initializeApp() {
  document.getElementById("side-nav").addEventListener("click", handlePageNavigation);
  document.getElementById("mobile-nav").addEventListener("click", handlePageNavigation);
  document.getElementById("avatar-button").addEventListener("click", toggleProfileMenu);
  document.getElementById("profile-menu").addEventListener("click", handleProfileMenu);
  document.getElementById("theme-button").addEventListener("click", toggleTheme);
  document.getElementById("mode-button").addEventListener("click", toggleMode);
  document.getElementById("demo-button").addEventListener("click", enterDemoMode);
  document.getElementById("brand-button").addEventListener("click", () => navigate("dashboard"));
  const sidebarToggle = document.getElementById("sidebar-toggle"); // Find the desktop menu control.
  const sidebarCollapsed = localStorage.getItem("arthmitra-sidebar-collapsed") === "true"; // Restore the user's menu width.
  document.body.classList.toggle("sidebar-collapsed", sidebarCollapsed); // Apply the saved desktop layout.
  sidebarToggle.setAttribute("aria-expanded", String(!sidebarCollapsed)); // Describe whether the menu is open.
  sidebarToggle.textContent = sidebarCollapsed ? "Expand menu" : "Collapse menu"; // Show the next action.
  sidebarToggle.addEventListener("click", () => { // Let the user fold or reopen the desktop navigation.
    const collapsed = document.body.classList.toggle("sidebar-collapsed"); // Change the menu width and page spacing.
    localStorage.setItem("arthmitra-sidebar-collapsed", String(collapsed)); // Remember the user's choice.
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed)); // Keep screen readers up to date.
    sidebarToggle.textContent = collapsed ? "Expand menu" : "Collapse menu"; // Keep the button action clear.
  }); // Finish the desktop collapse control.
  document.getElementById("mobile-more").addEventListener("click", toggleMobileMore);
  document.addEventListener("click", closeProfileMenuOutside);
  document.addEventListener("keydown", handleGlobalKey);
  window.addEventListener("popstate", () => routeFromHash());
  if (localStorage.getItem("arthmitra-theme") === "dark") document.body.classList.add("dark");
  document.getElementById("theme-button").textContent =
    document.body.classList.contains("dark") ? "Light mode" : "Dark mode";
  document.getElementById("mode-button").textContent =
    simpleMode ? "Use detailed mode" : "Use simple mode";
  if (token) {
    try {
      await loadProfile();
      navigate(routeName(), false);
    } catch (error) {
      if (token) renderRetry("We could not check your sign-in", error.message, initializeApp);
    }
  } else {
    if (window.location.hash && window.location.hash !== "#login") {
      history.replaceState({}, "", "#login");
    }
    renderLogin();
    checkBackend();
  }
}

// This function toggles the extra links in the phone navigation.
function toggleMobileMore() {
  const menu = document.getElementById("mobile-more-menu");
  const opening = menu.classList.contains("hidden");
  menu.classList.toggle("hidden", !opening);
  document.getElementById("mobile-more").setAttribute("aria-expanded", String(opening));
}

// This function closes the profile menu when a click happens somewhere else.
function closeProfileMenuOutside(event) {
  if (!event.target.closest(".header-actions")) {
    document.getElementById("profile-menu").classList.add("hidden");
    document.getElementById("avatar-button").setAttribute("aria-expanded", "false");
  }
}

// This function closes menus with Escape and keeps menu keyboard use straightforward.
function handleGlobalKey(event) {
  if (event.key === "Escape") {
    document.getElementById("profile-menu").classList.add("hidden");
    document.getElementById("avatar-button").setAttribute("aria-expanded", "false");
    document.getElementById("mobile-more-menu").classList.add("hidden");
    document.getElementById("mobile-more").setAttribute("aria-expanded", "false");
  }
}

// This function reads the requested page name from the browser address.
function routeName() {
  const page = window.location.hash.slice(1);
  return pageTitles[page] ? page : "dashboard";
}

// This function handles direct page links and sends unsigned visitors to login.
function routeFromHash() {
  if (!token) {
    renderLogin();
    return;
  }
  navigate(routeName(), false);
}

// This function creates or signs into the shared sample account and fills its example details.
async function enterDemoMode() {
  const demoId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const email = `demo-${demoId}@arthmitra.local`;
  const password = `demo-${demoId}-temporary-password`;
  try {
    const result = await apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    token = result.access_token;
    localStorage.setItem(tokenKey, token);
    await apiRequest("/profile", {
      method: "PUT",
      body: JSON.stringify({
        income: "30000",
        expenses: "20000",
        savings: "60000",
        debts: [{ name: "Personal loan", amount: "200000", interest_rate: "12", emi: "5000" }],
        goals: [{ name: "Wealth goal", amount: "1000000", years: 5 }],
      }),
    });
    await apiRequest("/risk-quiz", {
      method: "POST",
      body: JSON.stringify({ answers: [3, 3, 3, 3, 3, 3, 3] }),
    });
    await loadProfile();
    const onboarding = await apiRequest("/onboarding/status");
    navigate(onboarding.next_page, false);
  } catch (error) {
    renderLogin(error.message);
  }
}

// This function checks whether the backend can receive health requests.
async function checkBackend() {
  const status = document.getElementById("auth-status");
  try {
    const result = await apiRequest("/api/health");
    if (status && !status.textContent) status.textContent = result.message;
  } catch (error) {
    if (status) status.textContent = "Please start the backend, then try again.";
  }
}

initializeApp();
