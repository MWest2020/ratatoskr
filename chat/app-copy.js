// SPDX-License-Identifier: MIT
// Selectable, copyable message text (issue #245, openspec change
// selectable-message-text). Mark, 2026-11-15: "ik kan niet copy pasten vanuit
// ratatoskr. de text is niet selectable." He mostly copies tokens and commands:
//  - a message body is built here: plain text, ```fenced``` blocks and
//    `inline` code, each non-empty code part with a copy button. Everything
//    still goes in through textContent (el/add), never as markup.
//  - while a selection sits in the message list, a poll with new messages does
//    not re-render it (that wiped the selection). A pill says how many wait;
//    a tap, the end of the selection, or 30 s shows them.
// The long press on a bubble no longer starts a reply (app-reply.js): on a
// phone that is the platform's own select gesture. ↩ is the reply action.

// Split a message into {text}, {block} and {inline} parts. A fence that is
// never closed stays plain text. ``double`` backticks may hold a single one.
function codeParts(t){
  const out = [];
  const re = /```([^\n`]*)\n([\s\S]*?)```|```([^`]+?)```|``(?!`)([^\n]+?)``(?!`)|`([^`\n]+)`/g;
  let last = 0, m;
  while((m = re.exec(t))){
    if(m.index > last) out.push({text: t.slice(last, m.index)});
    if(m[2] !== undefined){
      // "```bash\n…": a word is the language (dropped); anything else was content.
      const word = /^[\w+#.-]*$/.test(m[1].trim());
      out.push({block: ((word ? "" : m[1] + "\n") + m[2]).replace(/\n$/, "")});
    } else if(m[3] !== undefined) out.push({block: m[3].trim()});
    else if(m[4] !== undefined) out.push({inline: m[4].replace(/^ (.*) $/, "$1")});
    else out.push({inline: m[5]});
    last = re.lastIndex;
  }
  if(last < t.length) out.push({text: t.slice(last)});
  // A block is a box of its own: the newline next to it would be a blank line.
  out.forEach((p, i) => {
    if(p.block === undefined) return;
    const a = out[i - 1], z = out[i + 1];
    if(a && a.text !== undefined) a.text = a.text.replace(/\n$/, "");
    if(z && z.text !== undefined) z.text = z.text.replace(/^\n/, "");
  });
  return out;
}

function copyBtn(code){
  const b = el("button", "copybtn", "⧉"); b.type = "button";
  b.title = "copy"; b.setAttribute("aria-label", "copy to clipboard");
  b.onclick = (e) => { e.stopPropagation(); copyCode(code, b); };
  return b;
}

// The message bubble for `content`. Called by renderMessages (app.js).
function bubbleFor(content){
  const b = el("div", "bubble");
  for(const p of codeParts(String(content == null ? "" : content))){
    if(p.text !== undefined){ add(b, p.text); continue; }
    if(p.block !== undefined){
      const code = el("code", "", p.block);
      // the button sits on a wrapper, so it stays put when a long line scrolls;
      // an empty fence has nothing to copy, so it gets no button
      add(b, add(el("div", "codeblock"), add(el("pre"), code), p.block.trim() ? copyBtn(code) : null));
    } else {
      const code = el("code", "inline", p.inline);
      add(b, code, copyBtn(code));
    }
  }
  return b;
}

function selectNode(node){
  const s = window.getSelection(), r = document.createRange();
  r.selectNodeContents(node); s.removeAllRanges(); s.addRange(r);
}

// One tap copies. The clipboard API needs a secure context and permission; when
// it is refused, execCommand gets a try on the selected code. If that copies, the
// selection goes again (it would hold the list back); if not, it stays, so the
// native menu can copy it, and a toast says why. Never a silent failure.
async function copyCode(code, btn){
  const text = code.textContent;
  let ok = false, why = "";
  try{
    if(!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("no clipboard API here");
    await navigator.clipboard.writeText(text); ok = true;
  }catch(e){ why = (e && e.message) || String(e); }
  if(!ok){
    selectNode(code);
    try{ ok = document.execCommand("copy"); }catch(e){ why = why || String(e); }
    if(ok) window.getSelection().removeAllRanges();
  }
  if(ok){
    btn.classList.add("ok"); btn.textContent = "✓";
    setTimeout(() => { btn.classList.remove("ok"); btn.textContent = "⧉"; }, 1200);
  } else if(typeof toast === "function"){
    toast("could not copy (" + why + ") — the text is selected, copy it from the menu", 5000);
  }
}

// --- keep a selection alive across polls ---
const HOLD_MS = 30000;      // a selection left open must not freeze the chat
let held = null;            // {msgs, cid, timer}

function selectingIn(box){
  const s = window.getSelection();
  return !!(box && s && s.rangeCount && !s.isCollapsed && box.contains(s.anchorNode));
}

function pill(){
  let p = document.getElementById("newPill");
  if(!p){
    p = el("button", "newpill"); p.id = "newPill"; p.type = "button"; p.hidden = true;
    p.onclick = () => { window.getSelection().removeAllRanges(); releaseHeld(true); };
    document.body.appendChild(p);
  }
  return p;
}

// refresh (app.js) asks this before it shows or counts anything: true means
// "not now, the person is selecting". The list is kept with its channel.
function holdRender(msgs, cid){
  if(!selectingIn(document.getElementById("msgs"))) return false;
  if(!held || held.cid !== cid){ dropHeld(); held = {cid, timer: setTimeout(() => releaseHeld(false), HOLD_MS)}; }
  held.msgs = msgs;
  const n = msgs.length - (typeof lastCount === "number" ? lastCount : 0), p = pill();
  p.textContent = (n === 1 ? "1 new message" : n + " new messages") + " — tap to show";
  p.hidden = false;
  return true;
}

function dropHeld(){
  if(held) clearTimeout(held.timer);
  held = null;
  const p = document.getElementById("newPill"); if(p) p.hidden = true;
}

// Show the held list, but only in the channel it was fetched for.
function releaseHeld(force){
  const h = held; dropHeld();
  if(!h || typeof current === "undefined" || !current || current.id !== h.cid) return;
  if(typeof takeMessages === "function") takeMessages(h.msgs, force);
}

document.addEventListener("selectionchange", () => {
  if(held && !selectingIn(document.getElementById("msgs"))) releaseHeld(false);
});
