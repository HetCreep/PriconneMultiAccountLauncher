# Security Policy — PriconneMultiAccountLauncher

This document covers supported versions, supply-chain integrity, dependency policy, and how to report a vulnerability.

## Supported Versions

Security patches are released only for the **latest stable version**. Older versions receive no fixes — update to the current build.

| Version | Status |
|---|---|
| Latest stable (see [Releases](https://github.com/HetCreep/PriconneMultiAccountLauncher/releases/latest)) | Supported |
| Older versions | Unsupported |
| Pre-release / `-rc` / `-beta` | Test-only, no support guarantee |

**Platform:** Windows 10 (1809+) / Windows 11, 64-bit.

## Reporting a Vulnerability

**Do not** open a public GitHub issue for security reports.

Use one of these channels:

1. **GitHub Security Advisories** — <https://github.com/HetCreep/PriconneMultiAccountLauncher/security/advisories/new> (preferred — keeps the report private until a patch is ready)
2. Direct contact with the maintainer listed in the repository profile

Please include:

- Affected version (run the launcher → Home tab shows version)
- Reproduction steps
- Impact assessment (credential leak / RCE / privilege escalation / etc.)
- Suggested fix if you have one

We aim to acknowledge within 72 hours and ship a patch within:

| Severity | Patch timeline |
|---|---|
| Critical (CVSS ≥ 9.0) | 72 hours |
| High (7.0 – 8.9) | 7 days |
| Medium (4.0 – 6.9) | Next scheduled release |
| Low (< 4.0) | Next major release |

## Secure Software Supply Chain

- **Deterministic dependency locking.** Runtime deps are pinned in `requirements.lock.txt`. PyInstaller, Inno Setup, and the Python toolchain versions are recorded in the build pipeline.
- **No remote one-shot tooling at runtime.** The launcher never calls `pipx run`, `uvx`, `curl | sh`, or similar.
- **Dependency audits.** PRs that add or upgrade a dependency must include: package name, version, license, justification, and a `pip-audit` clean result.
- **No new outbound hosts without review.** Any source change that introduces a new URL constant or import from `requests`/`urllib`/`socket`/`httpx`/`aiohttp` requires a maintainer audit per the project's egress allow-list (DMM + GitHub Releases only).

## Build & Distribution Integrity

- Releases are built by GitHub Actions on a version tag, not from a maintainer laptop. Local builds (`tools/build.ps1`) are for development only and are never distributed.
- Every release attaches `SHA256SUMS.txt` (installer + portable zip hashes) and an SBOM (`sbom.cdx.json`). Old releases are auto-deleted so only the latest installer is offered.
- When a code-signing certificate is available, the installer and main executable are Authenticode-signed.
- The installer uses a unique AppId distinct from the upstream project, refuses to install into a directory containing the upstream binary or named `DMMGamePlayerFastLauncher`, and never deletes or modifies upstream's files.
- See [verification steps in the release notes](https://github.com/HetCreep/PriconneMultiAccountLauncher/releases/latest) for the current procedure.

## Hard No's (Forbidden by Design)

The launcher will not, in any release:

- Patch, hook, or modify the Princess Connect Re:Dive game binary or any Cygames-shipped file
- Inject DLLs into the game process
- Read game-process memory after launch
- Send synthetic game-server requests on a schedule (no auto-login, auto-battle, auto-quest)
- Bundle Cygames or DMM game assets in source or releases
- Include telemetry, analytics, crash reporting, or Discord RPC
- Auto-download or auto-install updates (you confirm + verify each release)

## Coordinated Disclosure

If a vulnerability affects more than this project (for example, a bug in `pywin32`, `customtkinter`, or `requests`), we coordinate with the upstream maintainer before disclosing. Reporters who follow responsible disclosure are credited in the release notes (or kept anonymous on request).

## Out of Scope

The following are not considered security issues for this project:

- DMM account suspensions caused by use of multi-account tooling (see `LEGAL` / disclaimer in `README.md`)
- Issues that require physical access to an unlocked Windows session under the user's own account (DPAPI is per-user; physical-access compromise is outside our threat model)
- Vulnerabilities in optional browsers used for the import flow (Chrome, Edge, Firefox)
- Sandboxie / Cameyo redirection effects on per-account isolation (mitigation: warning surfaced; full prevention requires bypassing the sandbox, which we won't do)

## Related Documents

- [PRIVACY.md](PRIVACY.md) — what we do and do not collect
- [README.md](README.md) — install + verification flow
