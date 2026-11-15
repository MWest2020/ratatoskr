// SPDX-License-Identifier: MIT
// Selectable, copyable message text (issue #245). Mark, 2026-11-15: "ik kan
// niet copy pasten vanuit ratatoskr. de text is niet selectable." He mostly
// needs to copy tokens and commands, so:
//  - a message body is built here: plain text, ```fenced``` blocks and
//    `inline` code, each code part with a copy button. Everything still goes
//    in through textContent (el/add), never as markup.
//  - while a selection sits in the message list, a poll with new messages does
//    not re-render it (that wiped the selection), it waits until the selection
//    is gone.
// The long press on a bubble no longer starts a reply (app-reply.js): on a
// phone that is the platform's own select gesture, and the reply took the
// focus away from the selection. The ↩ button is the reply action.

// Split a message into {text}, {block, lang} and {inline} parts. A fence that
// is never closed stays plain text.
function codeParts(t){
  const out = [], re = /```([^\n`]*)\n([\s\S]*?)```|```([^`]+?)```|`([^`\n]+)`/g;
  let last = 0, m;
  while((m = re.exec(t))){
    if(m.index > last) out.push({text: t.slice(last, m.index)});
    if(m[2] !== undefined){
      // "```bash\n…": a word is the language; anything else was content.
      const lang = m[1].trim(), word = /^[\w+#.-]*$/.test(lang);
      out.push({block: ((word ? "" : m[1] + "\n") + m[2]).replace(/\n$/, ""), lang: word ? lang : ""});
    } else if(m[3] !== undefined) out.push({block: m[3].trim(), lang: ""});
    else out.push({inline: m[4]});
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
      if(p.lang) code.dataset.lang = p.lang;
      // the button sits on a wrapper, so it stays put when a long line scrolls
      add(b, add(el("div", "codeblock"), add(el("pre"), code), copyBtn(code)));
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
// it is refused, the text is selected (so the native menu can copy it) and
// execCommand gets a try. A failure says why, it never fails silently.
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
  }
  if(ok){
    btn.classList.add("ok"); btn.textContent = "✓";
    setTimeout(() => { btn.classList.remove("ok"); btn.textContent = "⧉"; }, 1200);
  } else if(typeof toast === "function"){
    toast("could not copy (" + why + ") — the text is selected, copy it from the menu", 5000);
  }
}

// --- keep a selection alive across polls ---
let heldMessages = null;

function selectingIn(box){
  const s = window.getSelection();
  return !!(box && s && s.rangeCount && !s.isCollapsed && box.contains(s.anchorNode));
}

// renderMessages asks this first: true means "not now, the person is selecting".
// A forced render (channel switch, own send) always goes through.
function holdRender(msgs, force){
  if(force){ heldMessages = null; return false; }
  if(!selectingIn(document.getElementById("msgs"))) return false;
  heldMessages = msgs; return true;
}

document.addEventListener("selectionchange", () => {
  if(!heldMessages || selectingIn(document.getElementById("msgs"))) return;
  const msgs = heldMessages; heldMessages = null;
  if(typeof renderMessages === "function") renderMessages(msgs, false);
});
