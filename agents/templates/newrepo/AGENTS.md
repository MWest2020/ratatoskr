# AGENTS.md: {{NAME}}

{{DESCRIPTION}}

- **Checks:** `bash verify.sh` must pass before a PR; extend it with every new
  test (CI runs only that script). Workflow files under `.github/workflows/`
  cannot be changed by habitat builders; add checks to `verify.sh` instead.
- **Decided work only:** build what is in `openspec/changes/<id>/`.
- **Docs:** `docs/index.md` plus `how-to/`, `reference/`, `explanation/`, each
  page with front matter `status` and `last_reviewed`. The docs gate fails a PR
  that changes code without docs.
- **Roadmap:** `docs/reference/roadmap.yml` feeds westerweel.work/nu; an item
  is done only with evidence.
- Commits as MWest2020 <mwest2020@hotmail.com>. No secrets in git.
