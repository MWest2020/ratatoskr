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

    def test_no_long_press_or_context_menu_handler_in_the_app(self):
        for name in self.JS:
            src = read(name)
            for ev in ("touchstart", "contextmenu", "selectstart"):
                self.assertNotIn(f'"{ev}"', src, f"{name} listens to {ev}")

    def test_the_bubble_is_built_by_bubble_for(self):
        self.assertIn("bubbleFor(m.content)", read("app.js"))
        self.assertIn("holdRender(msgs, force)", read("app.js"))


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
                         [{"text": "run:"}, {"block": "ls -la\ncd /tmp", "lang": "bash"},
                          {"text": "done"}])

    def test_fenced_block_without_language(self):
        self.assertEqual(self.parts("```\necho hi\n```"), [{"block": "echo hi", "lang": ""}])

    def test_one_line_fence(self):
        self.assertEqual(self.parts("```kubectl get pods```"),
                         [{"block": "kubectl get pods", "lang": ""}])

    def test_a_first_line_that_is_not_a_language_is_content(self):
        self.assertEqual(self.parts("```git push origin main\nmore\n```"),
                         [{"block": "git push origin main\nmore", "lang": ""}])

    def test_an_unclosed_fence_stays_text(self):
        self.assertEqual(self.parts("```\nno end"), [{"text": "```\nno end"}])

    def test_markup_stays_text(self):
        # The parts go in through textContent; the splitter must not eat or
        # transform anything that looks like HTML.
        payload = "<img src=x onerror=alert(1)>"
        self.assertEqual(self.parts(f"`{payload}`"), [{"inline": payload}])


if __name__ == "__main__":
    unittest.main()
