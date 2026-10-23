// SPDX-License-Identifier: MIT
// Reply to a message (openspec change reply-to-message). Mark, 2026-10-22:
// "can I select an agents message and reply to it, like in slack, or
// whatsapp?". A ↩ button (or a long press on the bubble) starts a reply; the
// compose bar shows what is being answered; the send carries `reply_to`, which
// the server passes to the relay as a thread reply. A reply is shown with a
// compact quote of its parent. Everything from a message goes in through
// textContent (el/add), never as markup.

let replyTarget = null;   // {id, author, line, cid}

function firstLine(t){ return (t || "").trim().split("\n")[0].slice(0, 90); }

function replyBar(){
  let bar = document.getElementById("replyBar");
  if(!bar){
    bar = el("div", "replybar"); bar.id = "replyBar"; bar.hidden = true;
    const form = document.getElementById("composer");
    if(form) form.parentNode.insertBefore(bar, form);
  }
  return bar;
}

function replyStart(m){
  const cid = (typeof current !== "undefined" && current) ? current.id : null;
  replyTarget = {id: m.id, author: m.author, line: firstLine(m.content), cid: cid};
  const bar = replyBar(); bar.textContent = "";
  const x = el("button", "replyx", "✕"); x.type = "button"; x.title = "cancel reply";
  x.onclick = replyClear;
  add(bar, el("span", "replylabel", "↩ replying to "), el("b", "", replyTarget.author), ": ",
      el("span", "replyline", replyTarget.line), x);
  bar.hidden = false;
  const input = document.getElementById("input"); if(input) input.focus();
}

function replyClear(){
  replyTarget = null;
  const bar = document.getElementById("replyBar");
  if(bar){ bar.hidden = true; bar.textContent = ""; }
}

// The id to send along — only in the channel the reply was started in, so a
// channel switch never sends a reply to the wrong place.
function replyId(){
  if(!replyTarget) return null;
  const cid = (typeof current !== "undefined" && current) ? current.id : null;
  if(replyTarget.cid !== cid){ replyClear(); return null; }
  return replyTarget.id;
}

// Called by renderMessages for every row: the quote above a reply, and the
// reply action on every message.
function decorateRow(row, m, all){
  if(!m.id) return;
  const bubble = row.querySelector(".bubble");
  if(m.reply_to){
    const p = (all || []).find(x => x.id === m.reply_to);
    const q = el("div", "quote");
    add(q, el("b", "", p ? p.author : "…"), ": ", p ? firstLine(p.content) : "(an earlier message)");
    row.insertBefore(q, bubble);
  }
  const btn = el("button", "replybtn", "↩"); btn.type = "button"; btn.title = "reply";
  btn.setAttribute("aria-label", "reply to this message");
  btn.onclick = (e) => { e.stopPropagation(); replyStart(m); };
  const meta = row.querySelector(".meta"); if(meta) meta.appendChild(btn);
  if(!bubble) return;
  let hold = null;   // long press on touch screens: 500 ms
  bubble.addEventListener("touchstart", () => { hold = setTimeout(() => replyStart(m), 500); },
                          {passive: true});
  for(const ev of ["touchend", "touchmove", "touchcancel"])
    bubble.addEventListener(ev, () => clearTimeout(hold), {passive: true});
}
