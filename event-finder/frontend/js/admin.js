const AdminPage = {
  runs: [],
  polling: null,

  async init() {
    await this.loadRuns();
    this.renderRuns();
    this.loadStats();
    this.bindForm();
  },

  async loadRuns() {
    try {
      const res = await fetch("/api/admin/runs");
      this.runs = await res.json();
    } catch { this.runs = []; }
  },

  async loadStats() {
    try {
      const res = await fetch("/api/admin/stats");
      const s = await res.json();
      document.getElementById("stat-total").textContent    = s.total;
      document.getElementById("stat-high").textContent     = s.high_priority;
      document.getElementById("stat-speaking").textContent = s.has_speaking;
      document.getElementById("stat-applied").textContent  = s.applied;
    } catch {}
  },

  async runDiscovery() {
    const btn = document.getElementById("btn-run");
    btn.disabled = true;
    btn.textContent = "Running…";
    showToast("Discovery started — this may take a few minutes");

    await fetch("/api/admin/run-discovery", { method: "POST" });
    this.startPolling(btn);
  },

  async runAI() {
    const btn = document.getElementById("btn-ai");
    btn.disabled = true;
    btn.textContent = "Running…";
    showToast("AI discovery started");
    await fetch("/api/admin/run-ai-discovery", { method: "POST" });
    this.startPolling(btn);
  },

  async rescore() {
    const btn = document.getElementById("btn-rescore");
    btn.disabled = true;
    btn.textContent = "Rescoring…";
    showToast("Rescoring started");
    await fetch("/api/admin/rescore", { method: "POST" });
    this.startPolling(btn);
  },

  startPolling(btn) {
    if (this.polling) clearInterval(this.polling);
    this.polling = setInterval(async () => {
      await this.loadRuns();
      this.renderRuns();
      const latest = this.runs[0];
      if (latest && latest.status !== "running") {
        clearInterval(this.polling);
        this.polling = null;
        btn.disabled = false;
        btn.textContent = btn.dataset.label;
        showToast(`Done — ${latest.events_new} new events`);
        await this.loadStats();
      }
    }, 4000);
  },

  renderRuns() {
    const tbody = document.getElementById("runs-tbody");
    if (!this.runs.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;padding:20px">No runs yet</td></tr>`;
      return;
    }
    tbody.innerHTML = this.runs.map(r => {
      const start = r.started_at ? r.started_at.slice(0, 16).replace("T", " ") : "—";
      const dur = r.started_at && r.finished_at
        ? `${Math.round((new Date(r.finished_at) - new Date(r.started_at)) / 1000)}s`
        : r.status === "running" ? "…" : "—";
      const badge = r.has_errors
        ? `<span class="badge badge-error">errors</span>`
        : r.status === "running"
          ? `<span class="badge badge-running">running</span>`
          : `<span class="badge badge-completed">done</span>`;
      return `<tr>
        <td>${r.id}</td>
        <td>${esc(r.run_type)}</td>
        <td>${start}</td>
        <td>${dur}</td>
        <td>${r.events_new ?? "—"} new / ${r.events_updated ?? "—"} updated</td>
        <td>${badge}</td>
      </tr>`;
    }).join("");
  },

  bindForm() {
    document.getElementById("manual-form")?.addEventListener("submit", async e => {
      e.preventDefault();
      const form = e.target;
      const payload = {
        name:           form.name.value,
        event_type:     form.event_type.value,
        date_raw:       form.date_raw.value,
        date_start:     form.date_start.value || null,
        location_city:  form.location_city.value,
        is_virtual:     form.is_virtual.checked,
        organizer:      form.organizer.value,
        description:    form.description.value,
        url:            form.url.value,
        contact_email:  form.contact_email.value,
        notes:          form.notes.value,
      };
      const res = await fetch("/api/events/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        showToast("Event added!");
        form.reset();
      } else if (res.status === 409) {
        showToast("Event already exists");
      } else {
        showToast("Error adding event");
      }
    });
  },
};
