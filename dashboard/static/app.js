const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const state = { providers: [], jobs: [], aspect: "9:16", picked: new Set(), uploadId: null };

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : r.statusText);
  return data;
}

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
}

/* ---------- tabs ---------- */
$$(".tab").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
function showView(v) {
  $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.view === v));
  $$(".view").forEach(s => s.classList.toggle("active", s.id === "view-" + v));
  try { localStorage.setItem("view", v); } catch {}
  if (v === "discover" && !$("#discList").children.length) scan();
}

/* ---------- providers ---------- */
async function loadProviders() {
  state.providers = await api("/api/providers");
  try {
    const saved = JSON.parse(localStorage.getItem("picked") || "null");
    if (saved) state.picked = new Set(saved.filter(id => state.providers.some(p => p.id === id)));
  } catch {}
  if (!state.picked.size) state.picked.add("ltx-video");
  renderPicker(); renderProviderList(); renderFilter(); updateDurationMax();
}

const KIND = { t2v: "text→video", i2v: "image→video (auto image)", reel: "voice + subtitles" };

function renderPicker() {
  const box = $("#providerPick"); box.innerHTML = "";
  for (const p of state.providers) {
    const unsupported = !p.aspects.includes(state.aspect);
    const disabled = !p.ready || unsupported;
    const cb = el("input", { type: "checkbox", checked: state.picked.has(p.id) && !disabled, disabled });
    cb.addEventListener("change", () => {
      cb.checked ? state.picked.add(p.id) : state.picked.delete(p.id);
      savePicked(); updateDurationMax();
    });
    const why = !p.ready ? p.status : unsupported ? `Sirf ${p.aspects.join(", ")}` : p.notes;
    box.append(el("label", { class: "pick" + (disabled ? " disabled" : "") }, cb,
      el("div", {},
        el("div", { class: "pn" }, p.name, el("span", { class: "tag" + (p.free ? " free" : "") }, p.free ? "free" : "paid"),
          p.custom ? el("span", { class: "tag" }, "auto") : null),
        el("div", { class: "pd" }, `${KIND[p.kind] || p.kind} · max ${p.max_duration}s · ${why}`))));
  }
}
function savePicked() { try { localStorage.setItem("picked", JSON.stringify([...state.picked])); } catch {} }
$("#selAll").onclick = () => { state.providers.forEach(p => p.ready && p.aspects.includes(state.aspect) && state.picked.add(p.id)); savePicked(); renderPicker(); updateDurationMax(); };
$("#selNone").onclick = () => { state.picked.clear(); savePicked(); renderPicker(); };

function renderProviderList() {
  const box = $("#providerList"); box.innerHTML = "";
  for (const p of state.providers) {
    const acts = el("div", { class: "acts" });
    if (p.source && p.source !== "local") acts.append(el("a", { href: p.source, target: "_blank", rel: "noopener" }, "Open source ↗"));
    if (p.custom) acts.append(el("button", { class: "small", onclick: async () => {
      await api("/api/providers/" + p.id, { method: "DELETE" }); loadProviders();
    } }, "Disconnect"));
    box.append(el("div", { class: "pcard" },
      el("div", { class: "pn" }, el("span", { class: "dot" + (p.ready ? " ok" : "") }), p.name,
        el("span", { class: "tag" + (p.free ? " free" : "") }, p.free ? "free" : "paid")),
      el("div", { class: "pd" }, `${KIND[p.kind] || p.kind} · max ${p.max_duration}s · ${p.aspects.join(" / ")}`),
      el("div", { class: "pd" }, p.ready ? p.notes : p.status), acts));
  }
}

function renderFilter() {
  const sel = $("#filterProvider"); const cur = sel.value;
  sel.innerHTML = ""; sel.append(el("option", { value: "" }, "All models"));
  state.providers.forEach(p => sel.append(el("option", { value: p.id }, p.name)));
  sel.value = cur;
}

/* ---------- generate form ---------- */
$$("#aspect button").forEach(b => b.addEventListener("click", () => {
  $$("#aspect button").forEach(x => x.classList.toggle("on", x === b));
  state.aspect = b.dataset.v; renderPicker();
}));
const dur = $("#duration");
dur.addEventListener("input", () => $("#durVal").textContent = dur.value);
function updateDurationMax() {
  const sel = state.providers.filter(p => state.picked.has(p.id) && p.kind !== "reel");
  const max = sel.length ? Math.max(...sel.map(p => p.max_duration)) : 8;
  dur.max = Math.max(2, Math.min(10, max));
  if (+dur.value > +dur.max) dur.value = dur.max;
  $("#durVal").textContent = dur.value;
}

$("#image").addEventListener("change", async e => {
  const f = e.target.files[0]; state.uploadId = null;
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  const d = await r.json();
  if (r.ok) state.uploadId = d.id; else setMsg(d.detail || "Upload fail", true);
});

function setMsg(t, err = false) { const m = $("#genMsg"); m.textContent = t; m.classList.toggle("err", err); }

$("#genBtn").addEventListener("click", async () => {
  const prompt = $("#prompt").value.trim();
  const providers = [...state.picked].filter(id => {
    const p = state.providers.find(x => x.id === id);
    return p && p.ready && p.aspects.includes(state.aspect);
  });
  if (prompt.length < 2) return setMsg("Prompt likho", true);
  if (!providers.length) return setMsg("Kam se kam ek AI model chuno", true);
  const btn = $("#genBtn"); btn.disabled = true; setMsg("Bhej raha hoon...");
  try {
    const r = await api("/api/generate", { method: "POST", body: JSON.stringify({
      prompt, providers, aspect: state.aspect, duration: +dur.value,
      negative_prompt: $("#negative").value, seed: +$("#seed").value || -1,
      image: state.uploadId, voice: $("#voice").value.trim() || null,
    }) });
    setMsg(`${r.jobs.length} job queue mein` + (r.errors.length ? ` · skipped: ${r.errors.join("; ")}` : ""));
    refreshJobs();
  } catch (e) { setMsg(e.message, true); }
  finally { btn.disabled = false; }
});

/* ---------- jobs ---------- */
function jobCard(j) {
  const n = $("#jobTpl").content.firstElementChild.cloneNode(true);
  n.dataset.id = j.id; n.dataset.sig = j.status + j.message;
  const media = $(".media", n);
  if (j.status === "done" && j.url) {
    media.append(el("video", { src: j.url, controls: true, loop: true, playsinline: true, preload: "metadata" }));
  } else if (j.status === "error") {
    n.classList.add("err");
    media.append(el("div", { class: "ph" }, "Failed"));
  } else {
    media.append(el("div", { class: "ph" }, el("div", { class: "spin" }), j.status === "queued" ? "Queue mein" : "Generating..."));
  }
  $(".prov", n).textContent = j.provider_name;
  const st = $(".st", n); st.textContent = j.status; st.classList.add(j.status);
  $(".prompt", n).textContent = j.prompt; $(".prompt", n).title = j.prompt;
  $(".jmsg", n).textContent = (j.elapsed ? `${j.elapsed}s · ` : "") + (j.message || "");
  const acts = $(".actions", n);
  if (j.url) acts.append(el("a", { href: j.url, download: `${j.provider}-${j.id}.mp4` }, "Download"));
  acts.append(el("button", { onclick: () => { $("#prompt").value = j.prompt; showView("generate"); } }, "Reuse prompt"));
  if (j.status === "done" || j.status === "error")
    acts.append(el("button", { onclick: async () => { await api("/api/jobs/" + j.id, { method: "DELETE" }); refreshJobs(); } }, "Delete"));
  return n;
}

function renderJobs(box, list) {
  const existing = new Map($$(".job", box).map(n => [n.dataset.id, n]));
  const frag = document.createDocumentFragment();
  for (const j of list) {
    const old = existing.get(j.id);
    frag.append(old && old.dataset.sig === j.status + j.message ? old : jobCard(j));
  }
  box.replaceChildren(frag);
  if (!list.length) box.append(el("div", { class: "muted" }, "Abhi koi video nahi."));
}

async function refreshJobs() {
  try { state.jobs = await api("/api/jobs"); } catch { return; }
  renderJobs($("#recent"), state.jobs.slice(0, 8));
  const q = $("#search").value.toLowerCase(), fp = $("#filterProvider").value, fs = $("#filterStatus").value;
  renderJobs($("#gallery"), state.jobs.filter(j =>
    (!q || j.prompt.toLowerCase().includes(q)) && (!fp || j.provider === fp) && (!fs || j.status === fs)));
  const running = state.jobs.filter(j => j.status === "running" || j.status === "queued").length;
  const b = $("#runningBadge"); b.textContent = running; b.classList.toggle("hidden", !running);
}
["#search", "#filterProvider", "#filterStatus"].forEach(s => $(s).addEventListener("input", refreshJobs));

/* ---------- discover ---------- */
async function scan() {
  const m = $("#discMsg"); m.textContent = "Hugging Face scan ho raha hai..."; m.classList.remove("err");
  try {
    const items = await api("/api/discover");
    const box = $("#discList"); box.innerHTML = "";
    for (const it of items) {
      const btn = el("button", { class: "small", disabled: it.connected }, it.connected ? "Connected" : "Connect");
      btn.onclick = () => connect(it.space, btn);
      box.append(el("div", { class: "pcard" },
        el("div", { class: "pn" }, el("span", { class: "dot" + (it.stage === "RUNNING" ? " ok" : "") }), it.space),
        el("div", { class: "pd" }, `♥ ${it.likes} · ${it.hardware || "?"} · ${it.stage || "?"}` + (it.free_gpu ? " · free GPU" : "")),
        el("div", { class: "acts" }, btn, el("a", { href: it.url, target: "_blank", rel: "noopener" }, "Open ↗"))));
    }
    m.textContent = `${items.length} video Spaces mile. Running + free GPU wale upar hain.`;
  } catch (e) { m.textContent = e.message; m.classList.add("err"); }
}
async function connect(space, btn) {
  const m = $("#discMsg"); m.classList.remove("err");
  if (btn) { btn.disabled = true; btn.textContent = "Analyzing..."; }
  m.textContent = `${space} ka API check ho raha hai...`;
  try {
    const cfg = await api("/api/connect", { method: "POST", body: JSON.stringify({ space }) });
    m.textContent = `Connected: ${cfg.space} (${cfg.api_name}). Generate tab mein dikhega.`;
    if (btn) btn.textContent = "Connected";
    loadProviders();
  } catch (e) {
    m.textContent = `${space}: ${e.message}`; m.classList.add("err");
    if (btn) { btn.disabled = false; btn.textContent = "Connect"; }
  }
}
$("#scanBtn").onclick = scan;
$("#manualBtn").onclick = () => { const s = $("#manualSpace").value.trim(); if (s) connect(s); };

/* ---------- boot ---------- */
(async function boot() {
  try {
    const s = await api("/api/status");
    const t = $("#tokenState");
    t.textContent = s.hf_token ? "HF token: connected" : "HF token: none (low free quota)";
    t.classList.toggle("ok", s.hf_token);
  } catch {}
  await loadProviders();
  await refreshJobs();
  setInterval(refreshJobs, 3000);
  let v = "generate"; try { v = localStorage.getItem("view") || v; } catch {}
  if (v !== "discover") showView(v);
})();
