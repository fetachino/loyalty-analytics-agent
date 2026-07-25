const endpoints = {
  login: "/api/v1/auth/login",
  logout: "/api/v1/auth/logout",
  me: "/api/v1/auth/me",
  overview: "/api/v1/analytics/overview",
  categories: "/api/v1/analytics/spending-by-category",
  tiers: "/api/v1/analytics/loyalty-tiers",
  rewards: "/api/v1/analytics/reward-redemptions",
  agent: "/api/v1/agent/query",
};

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
}

async function initializeSession() {
  try {
    const user = await fetchJson(endpoints.me);
    hideLogin(user);
    await loadDashboard();
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
    const response = await fetchJson(endpoints.agent, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    pending.querySelector("p").textContent = response.answer;
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
  } catch (error) {
    showLogin(error.message);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  await fetch(endpoints.logout, { method: "POST" });
  document.querySelector("#current-user").textContent = "";
  showLogin();
});

initializeSession();
