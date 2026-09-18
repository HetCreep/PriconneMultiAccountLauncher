# Contributing to PriconneMultiAccountLauncher

Thanks for considering a contribution. Please read this file completely before opening a PR.

## What We Accept

- **Bug fixes** — with a reproduction case in the issue or PR description.
- **Translation improvements** — every locale under `assets/i18n/` outside `app.en_US.yml` is bootstrap-translated and welcomes native-speaker review.
- **Anti-detection hardening** — improvements that preserve the project's "Tier A" official-launch posture without expanding the attack surface (see `SECURITY.md`).
- **Documentation** — clearer setup steps, more honest disclaimers, locale-specific README translations.

## What We Do Not Accept

- **Game-automation features** — botting, auto-battle, auto-quest, daily-login scripts. Out of scope.
- **DLL injection / game-binary patching** — forbidden by design (see `SECURITY.md` "Hard No's").
- **Telemetry, analytics, crash reporters, Discord RPC** — forbidden by design.
- **New outbound hosts** — the launcher's egress allow-list is DMM + GitHub Releases only.
- **Code that re-introduces the upstream brand** (`DMMGamePlayerFastLauncher`, `fa0311`) — the fork has been fully rebranded.

## Before You Submit

1. **Open an issue first** for any feature larger than a one-line fix. We may have already decided against it.
2. **Run** `python -m py_compile` on every file you touched.
3. **Format**: code is `black` formatted (line length 180, see `pyproject.toml`).
4. **Type hints** required on new function signatures.
5. **No `print()`** outside `tools/` — use the `logging` module with `%`-style format strings.
6. **No new dependencies** without justification in the PR description (impact on supply chain, license compatibility, maintenance status, alternative considered).
7. **If you add a string visible in the GUI**, propagate the key to all 11 locale files. `python tools/i18n.py diff <locale>` lists missing keys.

## Building & Releases

- **Local development build:** run `tools/build.ps1` to produce a local `.exe`/installer for testing. Local builds are for development only and are never distributed to users.
- **Distributed releases are tag-driven:** pushing a `v*` version tag triggers the GitHub Actions workflow (`.github/workflows/release.yml`), which builds the installer + portable zip, generates `SHA256SUMS.txt` and an SBOM, and publishes them to GitHub Releases. Do not upload release artifacts built on a local machine.

## Translation Contributions

- `en_US` is the source-of-truth — never modify other locales for content changes, only for translation refinements.
- Mark refined locales by removing the `# Bootstrap translation. ...` header comment once you have native-speaker review.
- Single-PR scope: one locale per PR to keep review tractable.

## Forking

If you fork this project:

- **Change the Inno Setup `AppId`** in `setup.iss`. This fork already uses a unique AppId (`{ECD76E8C-1446-453B-BCB6-80C4CCD5FE53}`) distinct from upstream so the two installers never collide; your fork must generate its own so it does not collide with this one.
- **Change the GitHub URLs** in `PriconneMultiAccountLauncher/static/config.py` (`UrlConfig`).
- **Generate a new AppId** with Inno Setup's Tools → Generate GUID, or any UUID v4 tool.

## Security

If you discover a vulnerability, do NOT open a public issue. See `SECURITY.md` for reporting channels.

## Code of Conduct

Be technical, be respectful, stay on scope. Off-topic / hostile interactions will be closed without comment.
