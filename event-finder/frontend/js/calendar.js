const CalendarPage = {
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  data: null,

  async init() {
    await this.load();
    this.render();
  },

  async load() {
    const m = String(this.month).padStart(2, "0");
    try {
      const res = await fetch(`/api/calendar/events?month=${this.year}-${m}`);
      this.data = await res.json();
    } catch (e) {
      this.data = { events: [], blocked_dates: [] };
    }
  },

  async prevMonth() {
    this.month--;
    if (this.month < 1) { this.month = 12; this.year--; }
    await this.load();
    this.render();
  },

  async nextMonth() {
    this.month++;
    if (this.month > 12) { this.month = 1; this.year++; }
    await this.load();
    this.render();
  },

  async deleteBlock(id) {
    if (!confirm("Remove this blocked date?")) return;
    await fetch(`/api/calendar/blocked-dates/${id}`, { method: "DELETE" });
    await this.load();
    this.render();
    showToast("Blocked date removed");
  },

  async addBlock() {
    const start = document.getElementById("block-start").value;
    const end   = document.getElementById("block-end").value;
    const reason = document.getElementById("block-reason").value;
    if (!start || !end) return;
    await fetch("/api/calendar/blocked-dates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date_start: start, date_end: end, reason }),
    });
    document.getElementById("block-modal").style.display = "none";
    await this.load();
    this.render();
    showToast("Date blocked");
  },

  monthName(m) {
    return ["January","February","March","April","May","June",
            "July","August","September","October","November","December"][m - 1];
  },

  render() {
    document.getElementById("cal-month-label").textContent =
      `${this.monthName(this.month)} ${this.year}`;

    const events = this.data?.events || [];
    const blocks = this.data?.blocked_dates || [];

    // Build lookup by date
    const byDate = {};
    for (const ev of events) {
      if (!ev.date_start) continue;
      if (!byDate[ev.date_start]) byDate[ev.date_start] = [];
      byDate[ev.date_start].push(ev);
    }

    const isBlocked = (dateStr) => blocks.some(b => b.date_start <= dateStr && dateStr <= b.date_end);

    const today = new Date().toISOString().slice(0, 10);
    const firstDay = new Date(this.year, this.month - 1, 1).getDay();
    const daysInMonth = new Date(this.year, this.month, 0).getDate();

    let calHTML = `
      <div class="cal-day-header">Sun</div><div class="cal-day-header">Mon</div>
      <div class="cal-day-header">Tue</div><div class="cal-day-header">Wed</div>
      <div class="cal-day-header">Thu</div><div class="cal-day-header">Fri</div>
      <div class="cal-day-header">Sat</div>
    `;

    for (let i = 0; i < firstDay; i++) calHTML += `<div class="cal-day cal-empty"></div>`;

    for (let d = 1; d <= daysInMonth; d++) {
      const m = String(this.month).padStart(2, "0");
      const day = String(d).padStart(2, "0");
      const dateStr = `${this.year}-${m}-${day}`;
      const dayEvents = byDate[dateStr] || [];
      const blocked = isBlocked(dateStr);
      const isToday = dateStr === today;

      const dots = dayEvents.slice(0, 4).map(ev => {
        const cls = ev.conflict ? "conflict" : ev.has_speaking ? "speaking" : "ok";
        return `<div class="cal-dot ${cls}" title="${esc(ev.name)}"></div>`;
      }).join("");

      calHTML += `
        <div class="cal-day ${blocked ? "blocked" : ""} ${isToday ? "today" : ""}"
             onclick="CalendarPage.showDay('${dateStr}')">
          <div class="cal-date">${d}</div>
          ${dots}
          ${dayEvents.length > 4 ? `<div style="font-size:0.6rem;color:#64748b">+${dayEvents.length - 4} more</div>` : ""}
          ${blocked ? `<div class="blocked-badge">Blocked</div>` : ""}
        </div>`;
    }

    document.getElementById("cal-grid").innerHTML = calHTML;

    // Render blocked dates list
    const blockedList = document.getElementById("blocked-list");
    if (blocks.length === 0) {
      blockedList.innerHTML = `<p style="color:#64748b;font-size:0.85rem">No blocked dates this month.</p>`;
    } else {
      blockedList.innerHTML = blocks.map(b => `
        <div class="blocked-item">
          <div>
            <div style="font-size:0.85rem;font-weight:600">${b.date_start} → ${b.date_end}</div>
            ${b.reason ? `<div style="font-size:0.75rem;color:#64748b">${esc(b.reason)}</div>` : ""}
          </div>
          <button class="delete-btn" onclick="CalendarPage.deleteBlock(${b.id})">✕ Remove</button>
        </div>`).join("");
    }
  },

  showDay(dateStr) {
    const events = (this.data?.events || []).filter(e => e.date_start === dateStr);
    if (!events.length) return;
    const details = events.map(e => `
      <div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #2d2d44">
        <div style="font-weight:700;margin-bottom:4px">${esc(e.name)}</div>
        <div style="font-size:0.8rem;color:#64748b">${esc(e.location_city || "—")} · Score: ${e.score}/10</div>
        ${e.conflict ? `<div style="color:#f472b6;font-size:0.75rem;margin-top:4px">⚠ Conflicts with blocked date</div>` : ""}
        ${e.has_speaking ? `<div style="color:#60a5fa;font-size:0.75rem;margin-top:2px">🎤 Speaking opportunity</div>` : ""}
      </div>`).join("");
    document.getElementById("day-modal-date").textContent = dateStr;
    document.getElementById("day-modal-events").innerHTML = details;
    document.getElementById("day-modal").style.display = "flex";
  },
};
