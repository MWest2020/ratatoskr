# SPDX-License-Identifier: MIT
"""Message text stays selectable and code parts get a copy button (issue #245).

Mark, 2026-11-15: "ik kan niet copy pasten vanuit ratatoskr. de text is niet
selectable." The cause was a long press on the bubble that started a reply and
moved the focus to the composer, on the very gesture Android uses to select
text. These tests pin both halves: nothing in the shell takes the select
gesture or the selection away again, and the splitter that finds the code to
copy does what the bubble relies on.

The browser half (a real selection, a real clipboard, a phone profile) is
chat/e2e/select-copy.js.
"""
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


class NothingTakesTheSelectGesture(unittest.TestCase):
    CSS = ("app.css", "header.css", "repos.css", "board.css")
    JS = [n for n in os.listdir(HERE) if n.startswith("app") and n.endswith(".js")]

    def test_no_user_select_none_except_on_the_copy_button(self):
        for name in self.CSS:
            for rule in re.findall(r"([^{}]+)\{([^}]*)\}", read(name)):
                sel, body = rule[0].strip(), rule[1].replace(" ", "")
                if "user-select:none" in body or "touch-callout:none" in body:
                    self.assertEqual(sel.split("*/")[-1].strip(), ".copybtn", f"{name}: {sel}")

    def test_the_bubble_says_selectable_out_loud(self):
        css = read("app.css").replace(" ", "")
        self.assertRegex(css, r"\.bubble\{[^}]*user-select:text")
        self.assertRegex(css, r"\.bubble\{[^}]*-webkit-user-select:text")

    # Every way to say it: addEventListener("…"), ('…'), (`…`), and on…= .
    HANDLER = re.compile(r"""["'`](touchstart|contextmenu|selectstart)["'`]"""
                         r"|\bon(touchstart|contextmenu|selectstart)\b")

    def test_no_long_press_or_context_menu_handler_in_the_app(self):
        for name in self.JS:
            hits = [m.group(0) for m in self.HANDLER.finditer(read(name))]
            self.assertEqual(hits, [], f"{name} listens to the select gesture")

    def test_the_handler_pattern_catches_each_form(self):
        for src in ('a.addEventListener("touchstart", f)', "a.addEventListener('contextmenu', f)",
                    "a.addEventListener(`selectstart`, f)", "a.ontouchstart = f",
                    '<div ontouchstart="f()">', "a.oncontextmenu=f"):
            self.assertRegex(src, self.HANDLER)
        self.assertNotRegex("// no long press (touchstart timer) any more", self.HANDLER)

    def test_the_bubble_is_built_by_bubble_for(self):
        self.assertIn("bubbleFor(m.content)", read("app.js"))
        self.assertIn("holdRender(msgs, cid)", read("app.js"))

    def test_nothing_is_counted_as_seen_before_the_hold(self):
        # A held list is not shown, so it must not clear unread or move lastCount.
        src = read("app.js")
        body = src[src.index("async function refresh("):src.index("function takeMessages(")]
        self.assertLess(body.index("holdRender("), body.index("takeMessages("))
        self.assertNotIn("markSeen(", body)
        self.assertNotIn("lastCount=", body)


class CodeParts(unittest.TestCase):
    """codeParts() from app-copy.js, run in node (preinstalled on the runner)."""

    def parts(self, text):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is needed to run app-copy.js; it is on ubuntu-latest")
        script = (
            "const vm=require('vm');const c={document:{addEventListener(){}},window:{}};"
            "vm.createContext(c);vm.runInContext(require('fs').readFileSync(process.argv[1],'utf8'),c);"
            "process.stdout.write(JSON.stringify(vm.runInContext('codeParts('+process.argv[2]+')',c)));")
        out = subprocess.run([node, "-e", script, os.path.join(HERE, "app-copy.js"), json.dumps(text)],
                             capture_output=True, text=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_plain_text_is_one_part(self):
        self.assertEqual(self.parts("hello there"), [{"text": "hello there"}])

    def test_inline_code(self):
        self.assertEqual(self.parts("token: `abc123` ok"),
                         [{"text": "token: "}, {"inline": "abc123"}, {"text": " ok"}])

    def test_fenced_block_with_language(self):
        self.assertEqual(self.parts("run:\n```bash\nls -la\ncd /tmp\n```\ndone"),
                         [{"text": "run:"}, {"block": "ls -la\ncd /tmp"},
                          {"text": "done"}])

    def test_fenced_block_without_language(self):
        self.assertEqual(self.parts("```\necho hi\n```"), [{"block": "echo hi"}])

    def test_an_empty_fence_is_an_empty_block(self):
        # bubbleFor gives an empty block no copy button.
        self.assertEqual(self.parts("```\n```"), [{"block": ""}])

    def test_double_backticks_leave_no_stray_backtick(self):
        self.assertEqual(self.parts("a ``x ` y`` b"),
                         [{"text": "a "}, {"inline": "x ` y"}, {"text": " b"}])
        self.assertEqual(self.parts("`` `tick` ``"), [{"inline": "`tick`"}])
        self.assertEqual(self.parts("``plain`` and `one`"),
                         [{"inline": "plain"}, {"text": " and "}, {"inline": "one"}])

    def test_one_line_fence(self):
        self.assertEqual(self.parts("```kubectl get pods```"),
                         [{"block": "kubectl get pods"}])

    def test_a_first_line_that_is_not_a_language_is_content(self):
        self.assertEqual(self.parts("```git push origin main\nmore\n```"),
                         [{"block": "git push origin main\nmore"}])

    def test_an_unclosed_fence_stays_text(self):
        self.assertEqual(self.parts("```\nno end"), [{"text": "```\nno end"}])

    def test_markup_stays_text(self):
        # The parts go in through textContent; the splitter must not eat or
        # transform anything that looks like HTML.
        payload = "<img src=x onerror=alert(1)>"
        self.assertEqual(self.parts(f"`{payload}`"), [{"inline": payload}])


if __name__ == "__main__":
    unittest.main()
