// Toy sightings: sending reports, shared by the toy map (sightings.html) and the price page (index.html).
// On the price page it also asks "Where did you get it?" right after someone marks a toy in My Happy Meals,
// offering the nearest McDonald's so a report takes one tap. Location stays in the browser; only the store,
// series and toys are sent (to the Apps Script in data/sightings.json).
(function () {
  "use strict";
  const MINE_KEY = "tt-sightings-mine";   // reports sent from this browser (the map shows them before the sheet catches up)
  const SENT_KEY = "tt-sightings-sent";   // store|series -> time sent, so the map doesn't ask twice in a few hours
  const ASK_KEY = "tt-ask-where";         // "off" once someone says don't ask again
  const RECENT_DAYS = 21;                 // ask for series in restaurants now or ended this recently
  const NEAR_MILES = 25;
  const ls = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let cfgP = null, storesP = null;
  const config = () => cfgP || (cfgP = fetch("data/sightings.json", { cache: "no-store" }).then(r => r.json()).catch(() => ({})));
  const stores = () => storesP || (storesP = fetch("data/stores.json").then(r => r.json()).then(d => d.stores || []));
  const isOpen = (c) => /^https:\/\/script\.google\.com\//.test((c && c.endpoint) || "");

  // store: {id, name, address, lat, lon}. Resolves once sent; Apps Script's reply can't be read cross-site,
  // so an opaque response counts as delivered.
  async function send(store, series, toys, out) {
    const c = await config();
    if (!isOpen(c)) throw new Error("Reporting isn't open");
    const body = new URLSearchParams({
      store_id: store.id, store_name: store.name || "McDonald's", address: store.address || "",
      lat: Number(store.lat).toFixed(6), lon: Number(store.lon).toFixed(6), series, toys: toys.join(","), out: out ? "yes" : "no",
    });
    await fetch(c.endpoint, { method: "POST", mode: "no-cors", body });
    const rep = { ts: Date.now(), store_id: store.id, store_name: store.name || "McDonald's", address: store.address || "",
                  lat: store.lat, lon: store.lon, series, toys, out: !!out };
    ls.set(MINE_KEY, [...ls.get(MINE_KEY, []).filter(m => Date.now() - m.ts < 2 * 36e5), rep]);
    const sent = ls.get(SENT_KEY, {}); sent[store.id + "|" + series] = rep.ts; ls.set(SENT_KEY, sent);
    return rep;
  }

  // Closest restaurants to a point, with distance in miles (flat-earth maths is plenty at this range).
  async function nearest(lat, lon, n = 3) {
    const all = await stores(), k = Math.cos(lat * Math.PI / 180);
    return all.map(([id, la, lo, name, address]) => {
      const dy = (la - lat) * 69.05, dx = (lo - lon) * 69.17 * k;
      return { id, lat: la, lon: lo, name: name || "McDonald's", address: address || "", miles: Math.hypot(dx, dy) };
    }).filter(s => s.miles <= NEAR_MILES).sort((a, b) => a.miles - b.miles).slice(0, n);
  }

  // ---------- "Where did you get it?" prompt (price page) ----------
  let pending = null;   // {series, seriesName, toys: [{id, name}]}
  let box = null, hideT = null;

  function css() {
    if (document.getElementById("ttAskCss")) return;
    const st = document.createElement("style"); st.id = "ttAskCss";
    st.textContent = `
      .tt-ask { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); z-index: 1000; width: min(440px, calc(100vw - 32px));
                background: var(--panel, #fff); color: var(--text, #1d1d1b); border: 1px solid var(--line, #e6e5df); border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0,0,0,.18); padding: 14px 16px; font-size: 14px; line-height: 1.45; }
      .tt-ask p { margin: 0 0 10px; padding-right: 22px; }
      .tt-ask .tt-x { position: absolute; top: 8px; right: 10px; border: 0; background: none; font-size: 20px; line-height: 1; cursor: pointer; color: var(--muted, #6b6b66); }
      .tt-ask .tt-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
      .tt-ask button.tt-b { border: 1px solid var(--line, #e6e5df); background: var(--panel, #fff); color: inherit; border-radius: 999px;
                            padding: 7px 14px; font: inherit; font-weight: 600; cursor: pointer; }
      .tt-ask button.tt-b.tt-go { background: var(--accent, #d62300); border-color: var(--accent, #d62300); color: #fff; }
      .tt-ask .tt-stores { display: grid; gap: 6px; margin-bottom: 10px; }
      .tt-ask .tt-store { text-align: left; border: 1px solid var(--line, #e6e5df); background: var(--bg, #fafaf7); color: inherit; border-radius: 12px;
                          padding: 8px 12px; font: inherit; cursor: pointer; }
      .tt-ask .tt-store:hover, .tt-ask button.tt-b:hover { border-color: var(--accent, #d62300); }
      .tt-ask .tt-store small, .tt-ask .tt-fine { color: var(--muted, #6b6b66); font-size: 12px; }
      .tt-ask .tt-fine { margin: 8px 0 0; }
      .tt-ask a { color: var(--accent, #d62300); font-weight: 600; }
      .tt-ask .tt-link { border: 0; background: none; padding: 0; font: inherit; font-size: 12px; color: var(--muted, #6b6b66); text-decoration: underline; cursor: pointer; }`;
    document.head.appendChild(st);
  }
  function show(html, wire) {
    css(); clearTimeout(hideT);
    if (!box) {
      box = document.createElement("div"); box.className = "tt-ask"; box.setAttribute("role", "dialog");
      box.setAttribute("aria-label", "Where did you get it?"); document.body.appendChild(box);
    }
    box.innerHTML = `<button class="tt-x" type="button" aria-label="Close">×</button>` + html;
    box.querySelector(".tt-x").onclick = close;
    if (wire) wire(box);
  }
  function close() { clearTimeout(hideT); if (box) { box.remove(); box = null; } pending = null; }
  const names = () => {
    const n = pending.toys.map(t => t.name);
    return n.length <= 2 ? n.join(" and ") : n.slice(0, -1).join(", ") + " and " + n[n.length - 1];
  };
  const mapLink = () => `sightings.html?toy=${encodeURIComponent(pending.toys[pending.toys.length - 1].id)}`;

  function askStep() {
    show(`<p>Got <b>${esc(names())}</b> from a Happy Meal recently? Tell other collectors which McDonald's has ${pending.toys.length > 1 ? "them" : "it"}.</p>
      <div class="tt-row"><button class="tt-b tt-go" type="button" data-near>📍 Pick my McDonald's</button>
      <button class="tt-b" type="button" data-later>Not now</button></div>
      <p class="tt-fine">Anonymous: only the store and toys are sent. Your location stays on your device.
      <button class="tt-link" type="button" data-never>Don't ask again</button></p>`, (b) => {
      b.querySelector("[data-near]").onclick = locate;
      b.querySelector("[data-later]").onclick = close;
      b.querySelector("[data-never]").onclick = () => { ls.set(ASK_KEY, "off"); close(); };
    });
  }
  function locate() {
    if (!navigator.geolocation) return noLocation();
    show(`<p>Finding McDonald's near you…</p>`);
    navigator.geolocation.getCurrentPosition(async (p) => {
      let list = [];
      try { list = await nearest(p.coords.latitude, p.coords.longitude); } catch (e) {}
      if (!pending) return;
      if (!list.length) return show(`<p>No McDonald's found within ${NEAR_MILES} miles. Pick it on the <a href="${mapLink()}">toy map</a> instead.</p>`);
      show(`<p>Which one did you get ${pending.toys.length > 1 ? "them" : "it"} at?</p>
        <div class="tt-stores">${list.map((s, i) => `<button class="tt-store" type="button" data-i="${i}">
          <b>${esc(s.name)}</b> <small>· ${s.miles < 0.1 ? "here" : s.miles.toFixed(1) + " mi"}</small><br><small>${esc(s.address || "Address not on the map")}</small></button>`).join("")}</div>
        <p class="tt-fine">Somewhere else? <a href="${mapLink()}">Pick it on the toy map</a></p>`, (b) => {
        b.querySelectorAll("[data-i]").forEach(el => el.onclick = () => report(list[+el.dataset.i]));
      });
    }, noLocation, { enableHighAccuracy: false, timeout: 10000, maximumAge: 6e5 });
  }
  function noLocation() {
    if (!pending) return;
    show(`<p>Location is off, so the nearest McDonald's can't be picked for you.</p>
      <div class="tt-row"><a class="tt-b tt-go" href="${mapLink()}" style="text-decoration:none">Pick it on the toy map</a></div>`);
  }
  async function report(store) {
    const p = pending; if (!p) return;
    show(`<p>Sending…</p>`);
    try { await send(store, p.series, p.toys.map(t => t.id), false); }
    catch (e) { return show(`<p>Couldn't send that just now. You can add it on the <a href="${mapLink()}">toy map</a>.</p>`); }
    const link = mapLink(), what = names();
    pending = null;
    show(`<p>Thanks! <b>${esc(what)}</b> ${p.toys.length > 1 ? "are" : "is"} now on the map at ${esc(store.address || store.name)}.</p>
      <div class="tt-row"><a class="tt-b" href="${link}" style="text-decoration:none">See the toy map</a></div>`);
    hideT = setTimeout(close, 8000);
  }

  // item: {id, name, series, seriesName, kind, current, end}. Called when a toy's count goes up.
  async function gotToy(item) {
    if (ls.get(ASK_KEY, "") === "off" || item.kind === "cards") return;   // cards are random in every meal
    const cutoff = new Date(Date.now() - RECENT_DAYS * 864e5).toISOString().slice(0, 10);
    if (!item.current && !(item.end && item.end >= cutoff)) return;
    if (!isOpen(await config())) return;
    if (pending && pending.series !== item.series) pending = null;
    if (!pending) pending = { series: item.series, seriesName: item.seriesName, toys: [] };
    else if (box && !box.querySelector("[data-near]")) return;   // mid-way through picking a store; leave it be
    if (!pending.toys.some(t => t.id === item.id)) pending.toys.push({ id: item.id, name: item.name });
    askStep();
    stores().catch(() => {});   // warm the restaurant list while they decide
  }
  // Called when a toy is taken back off (count to 0) before the report is sent.
  function lostToy(id) {
    if (!pending || (box && !box.querySelector("[data-near]"))) return;
    pending.toys = pending.toys.filter(t => t.id !== id);
    pending.toys.length ? askStep() : close();
  }

  window.TTReport = { send, nearest, config, isOpen, gotToy, lostToy, MINE_KEY, SENT_KEY };
})();
