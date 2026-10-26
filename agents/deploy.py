# SPDX-License-Identifier: MIT
"""Phase 3 of odin-runs-the-factory: a merge ends on the homelab, never on alma.

Mark, 2026-10-22: "I want to build on projects like wordsworth, but never have
to deal with a terminal or update my site." Deploying is GitOps: the cluster
follows MWest2020/homelab, so a deploy is a commit there. For a repository with
a recipe in factory.yml the steps are, one per tick:

    image   wait for the image(s) of the merge commit (tag sha-<7>), read the digests
    push    bump every digest in EVERY manifest of the recipe (api and init-job
            together, or migrations are missing), commit, push homelab main
    sync    ArgoCD hard refresh of the app
    verify  every image of the recipe runs its new digest and the rollout is complete

A recipe names one image (`package` + `image`) or several (`images:` a list of
{package, image}); a repository whose CI builds a server and a web image from
one commit deploys both together or not at all.
    done

alma is production and outside the experiment. It is not in any recipe, and
`safe_paths` refuses a manifest outside cluster-config/infra/ or naming alma.
"""
import json
import os
import re
import subprocess
import time

IMAGE_WAIT_S = 45 * 60
VERIFY_WAIT_S = 20 * 60


def safe_paths(paths):
    return all(p.startswith("cluster-config/infra/") and ".." not in p
               and "alma" not in p.lower() for p in paths or [])


def bump(text, image, digest, tag=None):
    """(new text, how many image lines changed). Only this image's lines:
    `<image>@sha256:<hex>`, and `<image>:<tag>@sha256:<hex>`, whose tag becomes
    `tag` when given (a pinned tag that names another commit than its digest
    would mislead whoever reads the manifest)."""
    pat = re.compile(rf"({re.escape(image)})(:[\w.-]+)?@sha256:[0-9a-f]{{64}}(?![0-9a-f])")

    def sub(m):
        t = m.group(2) or ""
        if t and tag:
            t = ":" + tag
        return f"{m.group(1)}{t}@{digest}"
    return pat.subn(sub, text)


def images(r):
    """A recipe's images as [(package, image)]: the `images:` list, or the
    single `package`/`image` pair."""
    if r.get("images"):
        return [(i["package"], i["image"]) for i in r["images"]]
    return [(r["package"], r["image"])]


def digests(d, r):
    """{image: digest} of deploy `d`. A deploy persisted before `images:`
    existed carries only `digest`, for the recipe's one image."""
    return d.get("digests") or {images(r)[0][1]: d["digest"]}


def _name(ref):
    """An image reference without tag or digest: `reg/path/name`."""
    head, _, last = ref.split("@")[0].rpartition("/")
    return f"{head}/{last.split(':')[0]}" if head else last.split(":")[0]


def _run(argv, runner, timeout=60, cwd=None):
    try:
        p = runner(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "", f"{argv[0]} did not finish: {e}"
    if p.returncode != 0:
        return p.stdout, (p.stderr.strip().splitlines() or [f"{argv[0]} failed"])[-1]
    return p.stdout, ""


class Deployer:
    def __init__(self, cfg, runner=subprocess.run, now=time.time):
        self.cfg, self.run, self.now = cfg, runner, now
        self.home = cfg.get("homelab") or {}
        self.kubectl = (self.home.get("kubectl") or "ssh -o BatchMode=yes jumpy kubectl").split()

    def recipe(self, repo):
        r = (self.cfg.get("deploy") or {}).get(repo)
        return r if r and safe_paths(r.get("manifests")) else None

    def step(self, d):
        """Advance deploy `d` (a dict, persisted by the caller) by at most one
        step. Returns (state, message): state is 'wait', 'next', 'done' or 'fail'."""
        r = self.recipe(d["repo"])
        if not r:
            return "fail", f"no safe deploy recipe for {d['repo']}"
        return getattr(self, "_" + d["phase"])(d, r)

    def _image(self, d, r):
        tag = "sha-" + d["sha"][:7]
        found = {}
        for package, image in images(r):
            out, err = _run(["gh", "api", f"/users/{self.cfg['owner']}/packages/container/"
                             f"{package}/versions?per_page=30"], self.run)
            rows = [] if err else json.loads(out or "[]")
            hit = next((v["name"] for v in rows if tag in v["metadata"]["container"]["tags"]), "")
            if not hit:
                if self.now() - d["started"] > IMAGE_WAIT_S:
                    return "fail", f"no image {package}:{tag} after {IMAGE_WAIT_S // 60} minutes"
                return "wait", ""
            found[image] = hit
        d["digests"], d["digest"], d["phase"] = found, next(iter(found.values())), "push"
        return "next", f"image {tag} built: " + ", ".join(f"{h[:19]}…" for h in found.values())

    def _push(self, d, r):
        wt = os.path.expanduser(self.home["worktree"])
        git = ["git", "-C", wt]
        if not os.path.isdir(wt):
            _, err = _run(["git", "-C", self.home["repo_dir"], "worktree", "add", "--detach",
                           wt, "origin/main"], self.run)
            if err:
                return "fail", f"homelab worktree: {err}"
        # -f: this worktree is the deployer's own; a half-written earlier attempt
        # must never block the next one.
        for argv in (git + ["fetch", "-q", "origin"], git + ["checkout", "-q", "-f", "--detach",
                                                               "origin/main"]):
            _, err = _run(argv, self.run)
            if err:
                return "wait", f"homelab: {err}"
        bumped = {}   # all or nothing: api without init-job misses its migrations
        tag, want = "sha-" + d["sha"][:7], digests(d, r)
        seen = {image: 0 for image in want}
        for m in r["manifests"]:
            with open(os.path.join(wt, m)) as fh:
                text = fh.read()
            total = 0
            for image, digest in want.items():
                text, n = bump(text, image, digest, tag)
                seen[image] += n
                total += n
            if total == 0:
                return "fail", f"{m}: no `{'` or `'.join(want)}@sha256:` line to bump"
            bumped[m] = text
        missing = [image for image, n in seen.items() if n == 0]
        if missing:
            return "fail", f"no `{missing[0]}@sha256:` line to bump in {', '.join(r['manifests'])}"
        for m, text in bumped.items():
            with open(os.path.join(wt, m), "w") as fh:
                fh.write(text)
        status, _ = _run(git + ["status", "--porcelain", "--", *r["manifests"]], self.run)
        if not status.strip():   # already on this digest: nothing to commit or push
            d["phase"] = "sync"
            return "next", "homelab already carries this digest"
        msg = (f"{d['repo']}: deploy {d['sha'][:7]} ({d['digest'][:19]}…) — by the factory, "
               f"{d['repo']}#{d['issue']}")
        for argv in (git + ["add", *r["manifests"]],
                     git + ["-c", "user.name=MWest2020", "-c", "user.email=mwest2020@hotmail.com",
                            "commit", "-q", "-m", msg],
                     git + ["push", "-q", "origin", "HEAD:main"]):
            _, err = _run(argv, self.run, timeout=120)
            if err:
                return "wait", f"homelab: {err}"
        d["phase"] = "sync"
        return "next", f"homelab bumped: {', '.join(r['manifests'])}"

    def _sync(self, d, r):
        _, err = _run(self.kubectl + ["-n", "argocd", "annotate", "application", r["app"],
                                      "argocd.argoproj.io/refresh=hard", "--overwrite"], self.run)
        if err:
            return "wait", f"argocd refresh: {err}"
        d["phase"], d["synced"] = "verify", self.now()
        return "next", f"ArgoCD refresh of {r['app']}"

    def _verify(self, d, r):
        out, _ = _run(self.kubectl + ["-n", r["namespace"], "get", "deploy", r["deployment"],
                                      "-o", "json"], self.run)
        want = digests(d, r)
        try:
            dep = json.loads(out)
            running = [c["image"] for c in dep["spec"]["template"]["spec"]["containers"]]
            st, replicas = dep.get("status", {}), dep["spec"].get("replicas", 1)
            ready = (st.get("updatedReplicas") == replicas and st.get("availableReplicas") == replicas
                     and st.get("observedGeneration", 0) >= dep["metadata"]["generation"])
        except (ValueError, KeyError, IndexError, TypeError):
            running, ready = [], False
        # Every image of the recipe, matched by name: a container's index says
        # nothing about which image it runs.
        on_new = all(any(_name(i) == image and i.endswith(digest) for i in running)
                     for image, digest in want.items())
        if on_new and ready:
            d["phase"] = "done"
            return "done", f"{r['deployment']} runs " + ", ".join(f"{g[:19]}…" for g in want.values())
        if self.now() - d["synced"] > VERIFY_WAIT_S:
            return "fail", f"{r['deployment']} not on the new digest after {VERIFY_WAIT_S // 60} min"
        return "wait", ""
