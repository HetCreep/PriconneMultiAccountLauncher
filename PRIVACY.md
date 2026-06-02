# Privacy Policy — PriconneMultiAccountLauncher

PriconneMultiAccountLauncher follows a **zero-telemetry, zero-knowledge** posture. The launcher runs entirely on your machine and never sends your account data anywhere.

## 1. Zero-Knowledge Data Isolation

- **Local execution only.** All credential handling, session swaps, hardware identity, and registry isolation happen on your computer.
- **No cloud collection.** No external database, no synchronization service, no telemetry, no analytics, no crash-reporting endpoint.
- **No third-party DLLs phone home.** Dependencies are pinned (`requirements.lock.txt`) and audited.

## 2. Outbound Network — Strict Allow-List

The launcher only initiates outbound HTTPS to:

| Host | Purpose | Trigger |
|---|---|---|
| `*.dmm.com`, `*.dmmgame.com` (and related DMM domains) | DMM authentication / launch | User login or game launch |
| Cygames game hosts | Game traffic from the launched game itself | User launches the game |
| `api.github.com`, `github.com`, `objects.githubusercontent.com` | Update-check + release download | App start (cached 24h, opt-out in Settings) |

Anything else is a bug. There is no Discord RPC, no Sentry, no Bugsnag, no GA, no PostHog, no Mixpanel, no maintainer-owned "heartbeat" endpoint.

## 3. Cryptographic Session Protection

- **Windows DPAPI per-user encryption.** Account credentials in `.bytes` files are wrapped via `win32crypt.CryptProtectData`. The encryption key is held by your Windows user account — files copied off your machine cannot be decrypted by anyone else.
- **AES-256 GCM** for the swap-in `authAccessTokenData.enc` blob, matching the official DMM Game Player format.
- **Synthetic hardware identity** (`mac_address`, `hdd_serial`, `motherboard`, `cpu_id`, `machine_guid`) is generated once per account from a CSPRNG and stored DPAPI-encrypted alongside the token. Never randomized at runtime — randomization triggers DMM's multi-account anomaly detection.
- **Cross-machine backup/export** does not use DPAPI (which is bound to one Windows user). Instead, the exported bundle is encrypted with an AES-256-GCM key derived from a passphrase you choose (PBKDF2-HMAC-SHA256). Only someone with the passphrase can restore it; the file never leaves your machine unless you move it yourself.

## 4. Credential Masking in Logs

- A redaction filter (`lib/log_sanitizer.py`) is attached to the root logger at startup.
- Filter rules: JWT tokens, `Bearer …` headers, long hex blobs, and key/value pairs whose key matches `token|cookie|password|secret|auth|session|hwid|mac_address|hdd_serial|motherboard|cpu_id|machine_guid|access_token|refresh_token|client_secret|api_key`.
- Redacted output: `access_token=[REDACTED]` / `[REDACTED:token]`.
- Toggle "Hide tokens on the log" in Settings is the user-facing knob.

## 5. Per-Account State Isolation

- Account switching is **registry-only**: only the Cygames `HKEY_CURRENT_USER\Software\Cygames\PrincessConnectReDive` registry subtree is snapshotted to a per-account backup directory and restored when that account is launched again. Shared game assets (`manifest.db` and the LocalLow asset cache) are account-agnostic and are never copied.
- A baseline of your pre-launcher account state is captured on the first managed swap and restored after each launched game session closes (crash recovery restores it on the next launch if a run was force-killed).
- Backups live under your local `data\` directory and never leave the machine.

## 6. Sandbox Awareness

If the launcher detects it is running inside Sandboxie or Cameyo, it logs a warning. Inside a sandbox, registry/file writes are redirected and per-account isolation is best-effort.

## 7. Update Check

- Connects to `api.github.com/repos/HetCreep/PriconneMultiAccountLauncher/releases/latest`.
- Cached on disk for 7 days to avoid spamming the API.
- Disable in Settings → "Disable update check (no calls to GitHub)".
- The launcher never auto-downloads or auto-installs. A toast notifies you, and clicking it opens the GitHub release page in your default browser.

## 8. Right to be Forgotten

The installer's uninstaller preserves your `data\` directory by default (accounts, shortcuts, registry snapshots). To wipe everything, delete the installation folder manually after uninstall, or clear `data\` from inside the Settings UI before uninstalling.

## 9. What We Do Not Collect

| Data | Collected? |
|---|---|
| DMM login email / password | No |
| Session tokens | No (only stored locally, DPAPI-encrypted) |
| Hardware identifiers | No (only synthetic per-account, stored locally) |
| Crash dumps | No |
| Usage analytics | No |
| Machine identifiers (Windows UUID, install ID) | No |
| IP address | No (the launcher itself does not log or transmit it) |

## Reporting Privacy Concerns

If you find the launcher contacting an unexpected host, reading data you did not authorize, or storing credentials outside DPAPI: open an issue at <https://github.com/HetCreep/PriconneMultiAccountLauncher/issues> with the offending log lines (redacted by the filter) and reproduction steps.
