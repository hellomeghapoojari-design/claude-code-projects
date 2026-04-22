const EventsPage = {
  data: null,
  filters: { city: "", eventType: "", status: "", minScore: 0, speaking: false, shortlisted: false, sort: "score" },
  statusOptions: ["new", "interested", "applied", "confirmed", "rejected", "passed"],

  async init() {
    await this.load();
    this.render();
    this.bindFilters();
  },

  async load() {
    const params = new URLSearchParams();
    if (this.filters.city)       params.set("city", this.filters.city);
    if (this.filters.eventType)  params.set("event_type", this.filters.eventType);
    if (this.filters.status)     params.set("status", this.filters.status);
    if (this.filters.minScore)   params.set("min_score", this.filters.minScore);
    if (this.filters.speaking)   params.set("has_speaking", "true");
    if (this.filters.shortlisted) params.set("shortlisted", "true");
    params.set("sort_by", this.filters.sort);
    params.set("limit", "200");

    try {
      const res = await fetch(`/api/events?${params}`);
      this.data = await res.json();
    } catch (e) {
      console.error("Failed to load events", e);
      this.data = [];
    }
  },

  async updateStatus(id, status) {
    await fetch(`/api/events/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    showToast("Status updated");
  },

  async toggleShortlist(id, current) {
    await fetch(`/api/events/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shortlisted: !current }),
    });
    await this.load();
    this.render();
  },

  tagClass(tag) {
    if (tag.includes("leadership")) return "tag-leadership";
    if (tag.includes("motivation")) return "tag-motivation";
    if (tag.includes("team"))       return "tag-leadership";
    if (tag.includes("hr") || tag.includes("l&d")) return "tag-hr";
    if (tag.includes("coaching"))   return "tag-coaching";
    if (tag.includes("keynote"))    return "tag-speaking";
    return "tag-default";
  },

  scoreClass(score) {
    if (score >= 8) return "score-high";
    if (score >= 5) return "score-medium";
    return "score-low";
  },

  cardHTML(ev) {
    const tags = (ev.relevance_tags || []).map(t =>
      `<span class="tag ${this.tagClass(t)}">${esc(t)}</span>`
    ).join("");
    const speakingTag = ev.has_speaking ? `<span class="tag tag-speaking">Speaking Opp</span>` : "";
    const statusOpts = this.statusOptions.map(s =>
      `<option value="${s}" ${ev.status === s ? "selected" : ""}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`
    ).join("");

    return `
    <div class="event-card ${this.scoreClass(ev.score)} ${ev.shortlisted ? "shortlisted" : ""}" data-id="${ev.id}">
      <div class="card-top">
        <div class="event-name">${esc(ev.name)}</div>
        <button class="star-btn ${ev.shortlisted ? "active" : ""}" onclick="Events.toggleShortlist(${ev.id}, ${ev.shortlisted})" title="Shortlist">★</button>
      </div>
      <div class="score-row">
        <div class="score-num">${ev.score}</div>
        <div class="score-bar-wrap"><div class="score-bar" style="width:${ev.score * 10}%"></div></div>
        <div class="score-denom">/10</div>
      </div>
      <div class="meta-grid">
        <div class="meta-item"><div class="meta-label">Type</div><div class="meta-value">${esc(ev.event_type || "—")}</div></div>
        <div class="meta-item"><div class="meta-label">Date</div><div class="meta-value">${esc(ev.date_raw || ev.date_start || "—")}</div></div>
        <div class="meta-item"><div class="meta-label">Location</div><div class="meta-value">${esc(ev.is_virtual ? "Virtual" : (ev.location_city || "—"))}</div></div>
        <div class="meta-item"><div class="meta-label">Organiser</div><div class="meta-value">${esc(ev.organizer || "—")}</div></div>
      </div>
      ${ev.description ? `<div class="meta-item" style="margin-bottom:12px"><div class="meta-label">About</div><div class="meta-value">${esc(ev.description.slice(0, 140))}${ev.description.length > 140 ? "…" : ""}</div></div>` : ""}
      <div class="tags">${speakingTag}${tags}</div>
      <div class="card-footer">
        <select class="status-select" onchange="Events.updateStatus(${ev.id}, this.value)">${statusOpts}</select>
        ${ev.url ? `<a class="card-link" href="${esc(ev.url)}" target="_blank" rel="noopener">Event Page ↗</a>` : ""}
      </div>
    </div>`;
  },

  render() {
    const container = document.getElementById("events-grid");
    if (!this.data || !this.data.length) {
      container.innerHTML = `<div class="empty-state">No events found. Try running discovery or adjusting filters.</div>`;
      return;
    }
    container.innerHTML = this.data.map(ev => this.cardHTML(ev)).join("");
    this.renderStats();
  },

  renderStats() {
    const d = this.data || [];
    document.getElementById("stat-total").textContent    = d.length;
    document.getElementById("stat-high").textContent     = d.filter(e => e.score >= 8).length;
    document.getElementById("stat-speaking").textContent = d.filter(e => e.has_speaking).length;
    document.getElementById("stat-applied").textContent  = d.filter(e => e.status === "applied").length;
  },

  bindFilters() {
    const apply = async () => {
      await this.load();
      this.render();
    };

    document.getElementById("filter-city")?.addEventListener("input", e => {
      this.filters.city = e.target.value;
    });
    document.getElementById("filter-type")?.addEventListener("change", e => {
      this.filters.eventType = e.target.value;
      apply();
    });
    document.getElementById("filter-status")?.addEventListener("change", e => {
      this.filters.status = e.target.value;
      apply();
    });
    document.getElementById("filter-score")?.addEventListener("input", e => {
      this.filters.minScore = parseInt(e.target.value) || 0;
      document.getElementById("score-val").textContent = this.filters.minScore;
      apply();
    });
    document.getElementById("filter-city")?.addEventListener("keyup", e => {
      if (e.key === "Enter") apply();
    });
    document.getElementById("filter-speaking")?.addEventListener("change", e => {
      this.filters.speaking = e.target.checked;
      apply();
    });
    document.getElementById("filter-shortlisted")?.addEventListener("change", e => {
      this.filters.shortlisted = e.target.checked;
      apply();
    });
    document.getElementById("sort-select")?.addEventListener("change", e => {
      this.filters.sort = e.target.value;
      apply();
    });

    document.querySelectorAll(".filter-btn[data-filter]").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn[data-filter]").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const f = btn.dataset.filter;
        this.filters.speaking = f === "speaking";
        this.filters.shortlisted = f === "shortlisted";
        if (f === "high") { this.filters.minScore = 8; document.getElementById("filter-score").value = 8; document.getElementById("score-val").textContent = 8; }
        else if (f === "all") { this.filters.minScore = 0; document.getElementById("filter-score").value = 0; document.getElementById("score-val").textContent = 0; }
        apply();
      });
    });
  },
};
