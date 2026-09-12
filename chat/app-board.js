// SPDX-License-Identifier: EUPL-1.2
// Het werk-overzicht: vier kolommen met kaarten, en wat te lang stilstaat.
//
// Alle tekst hier is ENGELS (ADR-0001: interface standaard Engels). De rest van
// de app is nog Nederlands en gaat in één keer om via een taallaag; nieuwe
// teksten beginnen niet opnieuw in het Nederlands.
//
// Kaarttitels komen van GitHub en van mappen op de host — dus alles via `el`/
// `add` (textContent), nooit innerHTML. Een PR-titel kan door iedereen gezet
// worden die een PR opent op een publieke repo.
//
// Er is geen slepen en geen statusknop: git is de waarheid, dit is een spiegel.

function ageLabel(days) {
  if (days < 1) return Math.max(1, Math.round(days * 24)) + "h";
  return Math.round(days) + "d";
}

function boardCard(c) {
  const row = document.createElement("div");
  row.className = "bcard" + (c.stale ? " stale" : "");
  const meta = el("div", "bmeta", "");
  add(meta, el("span", "brepo", c.repo || ""),
            el("span", "bage", ageLabel(c.age_days || 0)));
  if (c.who) add(meta, el("span", "bwho", "@" + c.who));
  add(row, meta, el("div", "btitle", c.title || ""));

  // Hoe het gebouwd wordt, en waar het nú mee bezig is. Zonder dat laatste is
  // een lopende sessie een kaart die niets zegt.
  if (c.via) add(row, el("div", "bvia", c.via));
  if (c.activity) add(row, el("div", "bact", "⋯ " + c.activity));

  // Elke kaart gaat érgens heen. Een PR of een change opent op GitHub; een
  // werksessie heeft geen URL maar wel een kanaal, dus daar springt de app
  // heen. Kan een kaart nergens heen, dan is hij zichtbaar niet klikbaar —
  // een kaart die wel klikbaar lijkt en niets doet is erger dan geen link.
  if (c.url) {
    row.classList.add("blink");
    row.onclick = () => window.open(c.url, "_blank", "noopener");
  } else if (c.channel) {
    row.classList.add("blink");
    row.onclick = () => {
      const ch = channels.find((x) => x.name === c.channel);
      if (ch) { closeBoard(); selectChannel(ch); }
    };
  } else if (c.source) {
    row.title = c.source;
  }
  return row;
}

function boardColumn(col, cards) {
  const wrap = document.createElement("div");
  wrap.className = "bcol";
  const head = el("div", "bcolhead", "");
  add(head, el("span", "bcoltitle", col.title),
            el("span", "bcount", String(col.count)));
  if (col.stale) add(head, el("span", "bstale", col.stale + " stuck"));
  wrap.appendChild(head);
  const mine = cards.filter((c) => c.column === col.key);
  if (!mine.length) wrap.appendChild(el("div", "bempty", "nothing here"));
  for (const c of mine) wrap.appendChild(boardCard(c));
  return wrap;
}

async function openBoard() {
  const view = $("#boardView");
  view.innerHTML = "";
  add(view, el("div", "agenthint", "loading…"));
  $("#boardDrawer").classList.add("open");

  let d;
  try {
    d = await (await fetch("/api/board")).json();
  } catch (e) {
    view.innerHTML = "";
    add(view, el("div", "agenthint", "Could not reach the server."));
    return;
  }
  view.innerHTML = "";
  if (d.error) {
    // Een ontbrekend bord is iets anders dan geen werk — zeg dat.
    add(view, el("div", "agenthint", d.error), el("div", "agenthint", d.hint || ""));
    return;
  }

  const cards = d.cards || [];
  const stuck = cards.filter((c) => c.stale).length;
  const summary = el("div", "bsummary",
    stuck ? stuck + " item" + (stuck === 1 ? "" : "s") + " stuck"
          : "Nothing is stuck — everything is moving.");
  add(view, summary);

  if (d.stale_snapshot) {
    const mins = Math.round((d.age_seconds || 0) / 60);
    add(view, el("div", "bwarn",
      "This snapshot is " + mins + " minutes old — the producer may be down."));
  }
  for (const e of (d.errors || [])) add(view, el("div", "bwarn", e));

  const cols = document.createElement("div");
  cols.className = "bcols";
  for (const col of (d.columns || [])) cols.appendChild(boardColumn(col, cards));
  view.appendChild(cols);

  if (!boardTimer) boardTimer = setInterval(() => {
    if ($("#boardDrawer").classList.contains("open")) openBoard();
    else closeBoard();
  }, 30000);
}

// Zolang het bord openstaat, halen we elke 30 seconden een verse momentopname.
// De producent draait elke twee minuten, dus je ziet een lopende sessie echt
// vooruitgaan in plaats van één keer bij het openen.
let boardTimer = null;

function closeBoard() {
  $("#boardDrawer").classList.remove("open");
  if (boardTimer) { clearInterval(boardTimer); boardTimer = null; }
}
