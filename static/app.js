const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

async function showBudget() {
  try {
    const b = await (await fetch("/api/budget")).json();
    $("#budget").textContent = b.key_configured
      ? `SerpApi searches this month: ${b.this_month} of ${b.budget}. Repeat searches come from the cache and are free.`
      : "No SerpApi key found. Add SERPAPI_KEY to .env and restart.";
  } catch { /* budget line is optional */ }
}

function renderProfile(p) {
  const repos = p.repos.map((r) => `${esc(r.repo.split("/")[1])} (${r.merged})`).join(", ");
  $("#profile").innerHTML = `
    <div class="profile">
      <strong>${esc(p.name)}</strong>
      <div class="muted">${p.total_merged} merged pull requests in other people's projects, mostly ${esc(p.languages.slice(0, 4).join(", "))}.</div>
      <div class="muted small">Top projects: ${repos}</div>
    </div>`;
}

function renderResult(r, i) {
  const c = r.company, j = r.job, d = r.draft;
  const apply = j.apply.map((a) => `<a href="${esc(a.link)}" target="_blank" rel="noopener">${esc(a.title)}</a>`).join(" · ");
  const founded = c.founded ? `${c.founded}${c.founded_source.startsWith("http") ? ` (<a href="${esc(c.founded_source)}" target="_blank" rel="noopener">source</a>)` : ` (${esc(c.founded_source)})`}` : "Not found";
  const email = c.email ? `<a href="mailto:${esc(c.email)}">${esc(c.email)}</a> <span class="muted small">(published on <a href="${esc(c.email_source)}" target="_blank" rel="noopener">their site</a>)</span>` : "No published hiring email found. Apply through the listing.";
  const news = (c.news || []).map((n) => `<li><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a> <span class="muted small">${esc(n.source)}, ${esc(n.date)}</span></li>`).join("");
  return `
    <article class="result">
      <h2><span>${esc(c.name)}</span><span class="score">score ${r.score}</span></h2>
      <p class="meta">${esc(j.title)} · ${esc(j.location)}${j.posted ? ` · ${esc(j.posted)}` : ""}${j.via ? ` · <span class="muted">${esc(j.via)}</span>` : ""}</p>
      <ul class="reasons">${r.reasons.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      <dl class="facts">
        <dt>Founded</dt><dd>${founded}</dd>
        <dt>Website</dt><dd>${c.website ? `<a href="${esc(c.website)}" target="_blank" rel="noopener">${esc(c.website.replace(/^https?:\/\//, ""))}</a>` : "Not found"}</dd>
        <dt>Email</dt><dd>${email}</dd>
        <dt>Apply</dt><dd>${apply || "—"}</dd>
      </dl>
      ${news ? `<p class="small muted">Recent news</p><ul class="small">${news}</ul>` : ""}
      <details>
        <summary>Draft email</summary>
        <p class="small muted">Subject: ${esc(d.subject)}</p>
        <textarea id="draft-${i}">${esc(d.body)}</textarea>
        <div class="actions">
          ${d.mailto ? `<a class="btn" href="${esc(d.mailto)}">Open in my email app</a>` : ""}
          <button type="button" class="ghost" data-copy="${i}">Copy text</button>
        </div>
        <p class="note">Nothing is sent for you. Edit the draft so it sounds like you before sending.</p>
      </details>
    </article>`;
}

$("#form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const body = {
    github: f.get("github"),
    query: f.get("query"),
    location: f.get("location"),
    max_companies: Number(f.get("max_companies")),
    with_news: f.get("with_news") === "on",
  };
  const btn = e.target.querySelector("button[type=submit]");
  btn.disabled = true;
  $("#status").textContent = "Reading your merged PRs, searching Google Jobs and checking each company…";
  $("#profile").innerHTML = $("#results").innerHTML = "";
  try {
    const res = await fetch("/api/scout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const out = await res.json();
    if (!res.ok) throw new Error(out.detail || "Something went wrong");
    renderProfile(out.profile);
    $("#results").innerHTML = out.results.map(renderResult).join("") || `<p class="muted">No listings matched. Try a broader search.</p>`;
    const s = out.searches;
    $("#status").textContent = `Checked ${out.results.length} companies from ${out.listings_seen} listings. Used ${s.this_run} SerpApi searches (${s.this_month} of ${s.budget} this month).`;
  } catch (err) {
    $("#status").textContent = err.message;
  } finally {
    btn.disabled = false;
    showBudget();
  }
});

document.addEventListener("click", async (e) => {
  const i = e.target.dataset?.copy;
  if (i === undefined) return;
  await navigator.clipboard.writeText($(`#draft-${i}`).value);
  e.target.textContent = "Copied";
  setTimeout(() => (e.target.textContent = "Copy text"), 1500);
});

showBudget();
