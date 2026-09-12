// SPDX-License-Identifier: EUPL-1.2
// The work overview: four columns of cards, and whatever stands still too long.
//
// All text here is ENGLISH (ADR-0001: the interface is English by default).
//
// Card titles come from GitHub and from directories on the host — so everything
// goes through `el`/`add` (textContent), never innerHTML. A PR title can be set
// by anyone who opens a PR on a public repo.
//
// There is no dragging and no status button: git is the truth, this is a mirror.

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

  // How it is being built, and what it is busy with right now. Without that last
  // part a running session is a card that says nothing.
  if (c.via) add(row, el("div", "bvia", c.via));
  if (c.activity) add(row, el("div", "bact", "⋯ " + c.activity));

  // Every card goes somewhere. A PR or a change opens on GitHub; a work session
  // has no URL but does have a channel, so that is where the app jumps. If a card
  // can go nowhere it is visibly not clickable — a card that looks clickable and
  // does nothing is worse than no link at all.
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
    // A missing board is something other than no work — say so.
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

// While the board is open we fetch a fresh snapshot every 30 seconds. The
// producer runs every two minutes, so you really see a running session move
// along instead of only once at opening time.
let boardTimer = null;

function closeBoard() {
  $("#boardDrawer").classList.remove("open");
  if (boardTimer) { clearInterval(boardTimer); boardTimer = null; }
}
