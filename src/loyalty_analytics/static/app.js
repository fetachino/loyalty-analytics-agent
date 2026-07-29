const endpoints = {
  login: "/api/v1/auth/login",
  logout: "/api/v1/auth/logout",
  me: "/api/v1/auth/me",
  overview: "/api/v1/analytics/overview",
  categories: "/api/v1/analytics/spending-by-category",
  tiers: "/api/v1/analytics/loyalty-tiers",
  rewards: "/api/v1/analytics/reward-redemptions",
  customers: "/api/v1/customers",
  createCustomer: "/api/v1/admin/customers",
  createTransaction: "/api/v1/admin/transactions",
  createReward: "/api/v1/admin/rewards",
  agent: "/api/v1/agent/query",
  agentHistory: "/api/v1/agent/history",
};

let currentUser = null;
let customerCache = [];

const colors = ["#173f35", "#7da8d9", "#f29b63", "#9d8bc4", "#8ebc55"];
const tierColors = {
  Bronze: "#b77a52",
  Silver: "#9aa6a1",
  Gold: "#dab346",
  Platinum: "#6e8f94",
};
const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const number = new Intl.NumberFormat("en-US");

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401 && url !== endpoints.login && url !== endpoints.me) {
    showLogin();
  }
  if (!response.ok) {
    let detail = "The service could not complete this request.";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Preserve the safe fallback message for non-JSON errors.
    }
    throw new Error(detail);
  }
  return response.json();
}

function showLogin(message = "") {
  document.querySelector("#login-screen").classList.add("visible");
  const error = document.querySelector("#login-error");
  error.textContent = message;
  error.hidden = !message;
}

function hideLogin(user) {
  document.querySelector("#login-screen").classList.remove("visible");
  document.querySelector("#current-user").textContent = user.full_name;
  currentUser = user;
  document.querySelector("#manage").hidden = !user.is_admin;
  document.querySelector("#manage-nav").hidden = !user.is_admin;
}

async function initializeSession() {
  try {
    const user = await fetchJson(endpoints.me);
    hideLogin(user);
    await loadDashboard();
    if (user.is_admin) await loadCustomers();
  } catch {
    showLogin();
  }
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderMetrics(data) {
  const metrics = [
    {
      icon: "◎",
      label: "Total customers",
      value: number.format(data.total_customers),
      detail: `${number.format(data.active_customers)} with purchase activity`,
      tint: "#e5f2eb",
    },
    {
      icon: "↗",
      label: "Purchase volume",
      value: currency.format(Number(data.total_purchase_amount)),
      detail: `${number.format(data.total_transactions)} transactions`,
      tint: "#e8f0f8",
    },
    {
      icon: "◆",
      label: "Points in circulation",
      value: number.format(data.total_points_balance),
      detail: `${number.format(data.total_points_earned)} lifetime earned`,
      tint: "#f5eedc",
    },
    {
      icon: "◇",
      label: "Rewards redeemed",
      value: number.format(data.total_rewards_redeemed),
      detail: `${number.format(data.total_points_redeemed)} points used`,
      tint: "#efeaf7",
    },
  ];

  const grid = document.querySelector("#metric-grid");
  grid.replaceChildren();
  metrics.forEach((metric) => {
    const card = createElement("article", "metric-card");
    card.style.setProperty("--card-tint", metric.tint);
    card.append(
      createElement("span", "metric-icon", metric.icon),
      createElement("span", "metric-label", metric.label),
      createElement("strong", "metric-value", metric.value),
      createElement("small", "metric-detail", metric.detail),
    );
    grid.append(card);
  });
}

function renderCategories(categories) {
  const chart = document.querySelector("#category-chart");
  chart.classList.remove("loading-block");
  chart.replaceChildren();
  const max = Math.max(...categories.map((item) => Number(item.total_purchase_amount)), 1);

  categories.forEach((item, index) => {
    const row = createElement("div", "bar-row");
    const label = createElement("span", "bar-label", item.category);
    const track = createElement("div", "bar-track");
    const fill = createElement("div", "bar-fill");
    fill.style.setProperty(
      "--bar-width",
      `${(Number(item.total_purchase_amount) / max) * 100}%`,
    );
    fill.style.setProperty("--bar-color", colors[index % colors.length]);
    track.append(fill);
    row.append(
      label,
      track,
      createElement("span", "bar-value", currency.format(Number(item.total_purchase_amount))),
    );
    chart.append(row);
  });
}

function renderTiers(tiers) {
  const summary = document.querySelector("#tier-summary");
  summary.classList.remove("loading-block");
  summary.replaceChildren();
  const total = tiers.reduce((sum, item) => sum + item.customer_count, 0) || 1;
  const strip = createElement("div", "tier-strip");
  strip.setAttribute("aria-label", "Customer distribution by loyalty tier");
  const list = createElement("div", "tier-list");

  tiers.forEach((tier) => {
    const color = tierColors[tier.loyalty_tier] || "#759488";
    const segment = document.createElement("span");
    segment.style.setProperty("--tier-width", `${(tier.customer_count / total) * 100}%`);
    segment.style.setProperty("--tier-color", color);
    segment.title = `${tier.loyalty_tier}: ${tier.customer_count}`;
    strip.append(segment);

    const row = createElement("div", "tier-row");
    const dot = createElement("span", "tier-dot");
    dot.style.setProperty("--tier-color", color);
    const details = document.createElement("div");
    details.append(
      createElement("div", "tier-name", tier.loyalty_tier),
      createElement(
        "div",
        "tier-meta",
        `${number.format(Number(tier.average_points_balance))} avg. points`,
      ),
    );
    row.append(dot, details, createElement("strong", "tier-count", tier.customer_count));
    list.append(row);
  });
  summary.append(strip, list);
}

function renderRewards(rewards) {
  const table = document.querySelector("#reward-table");
  table.replaceChildren();
  rewards.forEach((reward) => {
    const row = document.createElement("tr");
    row.append(
      createElement("td", "", reward.reward_name),
      createElement("td", "", number.format(reward.redemption_count)),
      createElement("td", "", number.format(reward.total_points_used)),
    );
    table.append(row);
  });
}

async function loadDashboard() {
  const refreshButton = document.querySelector("#refresh-button");
  const error = document.querySelector("#global-error");
  refreshButton.classList.add("loading");
  refreshButton.disabled = true;
  error.hidden = true;

  try {
    const [overview, categories, tiers, rewards] = await Promise.all([
      fetchJson(endpoints.overview),
      fetchJson(endpoints.categories),
      fetchJson(endpoints.tiers),
      fetchJson(endpoints.rewards),
    ]);
    renderMetrics(overview);
    renderCategories(categories);
    renderTiers(tiers);
    renderRewards(rewards);
    document.querySelector("#last-updated").textContent =
      `Updated ${new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" }).format(new Date())}`;
  } catch (loadError) {
    error.textContent = `Dashboard data unavailable: ${loadError.message}`;
    error.hidden = false;
  } finally {
    refreshButton.classList.remove("loading");
    refreshButton.disabled = false;
  }
}

function localDateTimeValue(date = new Date()) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function setFormDefaults() {
  document.querySelector('#customer-create-form [name="join_date"]').value = new Date()
    .toISOString()
    .slice(0, 10);
  document.querySelector('#transaction-create-form [name="purchase_date"]').value =
    localDateTimeValue();
  document.querySelector('#reward-create-form [name="redeemed_at"]').value =
    localDateTimeValue();
}

async function loadCustomers() {
  if (!currentUser?.is_admin) return;
  const page = await fetchJson(`${endpoints.customers}?page=1&page_size=100`);
  customerCache = page.items;
  document.querySelectorAll(".customer-select").forEach((select) => {
    const selected = select.value;
    select.replaceChildren(new Option("Select a customer", ""));
    customerCache.forEach((customer) => {
      const label = `${customer.first_name} ${customer.last_name} · ${number.format(customer.points_balance)} pts`;
      select.append(new Option(label, customer.id));
    });
    if (customerCache.some((customer) => customer.id === selected)) {
      select.value = selected;
    }
  });
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function compactPayload(values, excluded = []) {
  return Object.fromEntries(
    Object.entries(values).filter(([key, value]) => !excluded.includes(key) && value !== ""),
  );
}

async function submitManagementForm(form, url, payload, successMessage) {
  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector(".form-status");
  button.disabled = true;
  status.className = "form-status";
  status.textContent = "Saving…";
  try {
    await fetchJson(url, {
      method: form.id === "customer-update-form" ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    status.classList.add("success");
    status.textContent = successMessage;
    form.reset();
    setFormDefaults();
    await loadCustomers();
    await loadDashboard();
  } catch (error) {
    status.classList.add("error");
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

document.querySelector("#customer-create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  await submitManagementForm(
    form,
    endpoints.createCustomer,
    formValues(form),
    "Customer created successfully.",
  );
});

document.querySelector("#customer-update-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const values = formValues(form);
  const customerId = values.customer_id;
  const payload = compactPayload(values, ["customer_id"]);
  if (!Object.keys(payload).length) {
    const status = form.querySelector(".form-status");
    status.className = "form-status error";
    status.textContent = "Enter at least one field to update.";
    return;
  }
  await submitManagementForm(
    form,
    `${endpoints.createCustomer}/${encodeURIComponent(customerId)}`,
    payload,
    "Customer updated successfully.",
  );
});

document.querySelector("#transaction-create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formValues(form);
  payload.purchase_amount = Number(payload.purchase_amount);
  payload.points_earned = Number(payload.points_earned);
  payload.purchase_date = new Date(payload.purchase_date).toISOString();
  await submitManagementForm(
    form,
    endpoints.createTransaction,
    payload,
    "Purchase recorded and points credited.",
  );
});

document.querySelector("#reward-create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formValues(form);
  payload.points_used = Number(payload.points_used);
  payload.redeemed_at = new Date(payload.redeemed_at).toISOString();
  await submitManagementForm(
    form,
    endpoints.createReward,
    payload,
    "Reward redeemed and points deducted.",
  );
});

function addMessage(text, role) {
  const conversation = document.querySelector("#conversation");
  const message = createElement("div", `message ${role}-message`);
  if (role === "assistant") {
    message.append(createElement("span", "message-icon", "✦"));
  }
  message.append(createElement("p", "", text));
  conversation.append(message);
  conversation.scrollTop = conversation.scrollHeight;
  return message;
}

async function loadAgentHistory() {
  const container = document.querySelector("#agent-history");
  try {
    const history = await fetchJson(`${endpoints.agentHistory}?limit=5`);
    container.replaceChildren();
    if (!history.length) {
      container.append(createElement("p", "history-empty", "Your recent analyses will appear here."));
      return;
    }
    history.forEach((item) => {
      const button = createElement("button", "history-item");
      button.type = "button";
      button.append(
        createElement("span", "", item.question),
        createElement(
          "small",
          "",
          new Intl.DateTimeFormat("en-US", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          }).format(new Date(item.created_at)),
        ),
      );
      button.addEventListener("click", () => {
        document.querySelector("#agent-question").value = item.question;
        document.querySelector("#agent-question").focus();
      });
      container.append(button);
    });
  } catch {
    container.replaceChildren();
  }
}

document.querySelector("#agent-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#agent-question");
  const button = event.currentTarget.querySelector("button");
  const question = input.value.trim();
  if (!question) return;

  addMessage(question, "user");
  input.value = "";
  button.disabled = true;
  const pending = addMessage("Reviewing program data…", "assistant");

  try {
    let response = await fetchJson(endpoints.agent, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (response.status === "approval_required") {
      const approved = window.confirm(response.approval_request);
      response = await fetchJson(
        `/api/v1/agent/workflows/${encodeURIComponent(response.workflow_id)}/approval`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved }),
        },
      );
    }
    pending.querySelector("p").textContent = response.answer;
    await loadAgentHistory();
  } catch (agentError) {
    pending.querySelector("p").textContent =
      `I couldn't complete that analysis. ${agentError.message}`;
  } finally {
    button.disabled = false;
    input.focus();
  }
});

document.querySelector("#refresh-button").addEventListener("click", loadDashboard);
document.querySelector(".menu-button").addEventListener("click", () => {
  document.querySelector(".app-shell").classList.toggle("menu-open");
});
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelector(".app-shell").classList.remove("menu-open");
  });
});

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  try {
    const result = await fetchJson(endpoints.login, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.querySelector("#login-email").value,
        password: document.querySelector("#login-password").value,
      }),
    });
    hideLogin(result.user);
    document.querySelector("#login-password").value = "";
    await loadDashboard();
    await loadAgentHistory();
    if (result.user.is_admin) await loadCustomers();
  } catch (error) {
    showLogin(error.message);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  await fetch(endpoints.logout, { method: "POST" });
  currentUser = null;
  document.querySelector("#current-user").textContent = "";
  document.querySelector("#manage").hidden = true;
  document.querySelector("#manage-nav").hidden = true;
  showLogin();
});

document.querySelector("#export-button").addEventListener("click", () => {
  const report = document.querySelector("#export-select").value;
  window.location.assign(`/api/v1/exports/${report}.csv`);
});

setFormDefaults();
initializeSession();
