const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";

function drawGlucoseChart() {
  const svg = document.getElementById("glucose-chart");
  const dataElement = document.getElementById("chart-data");
  if (!svg || !dataElement) return;

  const entries = JSON.parse(dataElement.textContent || "[]");
  if (!entries.length) return;

  const width = 760;
  const height = 250;
  const padding = { top: 20, right: 24, bottom: 32, left: 44 };
  const values = entries.map((entry) => Number(entry.value));
  const isMmol = entries[0]?.unit === "mmol/L";

  // Target educational range: 80-130 mg/dL or 4.4-7.2 mmol/L
  const targetLow = isMmol ? 4.4 : 80;
  const targetHigh = isMmol ? 7.2 : 130;

  const dataLow = Math.min(...values);
  const dataHigh = Math.max(...values);
  const low = Math.min(dataLow, targetLow);
  const high = Math.max(dataHigh, targetHigh);

  const spread = high - low || Math.max(Math.abs(high) * 0.15, 1);
  const min = Math.max(0, low - spread * 0.15);
  const max = high + spread * 0.15;

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const x = (index) =>
    padding.left +
    (entries.length === 1 ? plotWidth / 2 : (index * plotWidth) / (entries.length - 1));
  const y = (val) => padding.top + ((max - val) / (max - min)) * plotHeight;

  const namespace = "http://www.w3.org/2000/svg";
  const element = (name, attributes = {}) => {
    const node = document.createElementNS(namespace, name);
    Object.entries(attributes).forEach(([k, v]) => node.setAttribute(k, v));
    return node;
  };

  svg.replaceChildren();

  // Draw background target range band
  const targetY1 = y(targetHigh);
  const targetY2 = y(targetLow);
  const bandHeight = Math.max(2, targetY2 - targetY1);
  const targetBand = element("rect", {
    x: padding.left,
    y: targetY1,
    width: plotWidth,
    height: bandHeight,
    class: "chart-target-zone",
  });
  svg.append(targetBand);

  // Draw horizontal grid lines
  for (let i = 0; i < 4; i += 1) {
    const gridY = padding.top + (plotHeight / 3) * i;
    svg.append(
      element("line", {
        x1: padding.left,
        x2: width - padding.right,
        y1: gridY,
        y2: gridY,
        class: "chart-gridline",
      })
    );
  }

  // Draw trend polyline
  const points = entries.map((entry, index) => `${x(index)},${y(Number(entry.value))}`).join(" ");
  if (entries.length > 1) {
    svg.append(element("polyline", { points, class: "chart-line" }));
  }

  // Draw individual points with tooltips
  entries.forEach((entry, index) => {
    const val = Number(entry.value);
    const point = element("circle", {
      cx: x(index),
      cy: y(val),
      r: entries.length < 15 ? 4.5 : 3.5,
      class: "chart-point",
    });
    const title = element("title");
    title.textContent = `${val} ${entry.unit} · ${entry.context} · ${entry.recorded_at.replace("T", " ")}`;
    point.append(title);
    svg.append(point);
  });

  // Date labels at edges
  const firstDate = new Date(entries[0].recorded_at);
  const lastDate = new Date(entries[entries.length - 1].recorded_at);
  [firstDate, lastDate].forEach((date, idx) => {
    const label = element("text", {
      x: idx ? width - padding.right : padding.left,
      y: height - 6,
      class: "chart-date",
      "text-anchor": idx ? "end" : "start",
    });
    label.textContent = Number.isNaN(date.getTime())
      ? ""
      : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    svg.append(label);
  });
}

function setDefaultTimes() {
  const reminderInput = document.getElementById("reminder-time");
  if (reminderInput && !reminderInput.value) {
    const localDate = new Date(Date.now() + 60 * 60 * 1000);
    localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
    reminderInput.value = localDate.toISOString().slice(0, 16);
  }
}

function setupAssistant() {
  const form = document.getElementById("assistant-form");
  const questionInput = document.getElementById("assistant-question");
  const status = document.getElementById("assistant-status");
  const button = form?.querySelector("button");
  if (!form || !questionInput || !status || !button) return;

  // Setup prompt chips
  const chips = document.querySelectorAll(".chip-btn");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt) {
        questionInput.value = prompt;
        questionInput.focus();
        form.requestSubmit();
      }
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = questionInput.value.trim();
    if (!question) {
      questionInput.focus();
      return;
    }

    status.textContent = "DiaBuddy is reviewing your saved readings and journal logs…";
    status.className = "assistant-status is-loading";
    button.disabled = true;
    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({ question }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || "The assistant request could not be completed.");
      }
      status.textContent = result.answer;
      status.className = "assistant-status is-answer";
    } catch (error) {
      status.textContent = error.message || "The assistant request could not be completed.";
      status.className = "assistant-status is-error";
    } finally {
      button.disabled = false;
    }
  });
}

drawGlucoseChart();
setDefaultTimes();
setupAssistant();
