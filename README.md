# PriconneMultiAccountLauncher

A secure, ultra-fast, and flawless multi-account switcher and launcher for the PC version of Princess Connect! Re:Dive (DMM version).

[![Latest Release](https://img.shields.io/github/v/release/HetCreep/PriconneMultiAccountLauncher?sort=semver)](https://github.com/HetCreep/PriconneMultiAccountLauncher/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Key Features

*   **Flawless Swapping (Registry-Only):** Snapshots and restores **only** the Cygames Windows registry subtree (`HKCU\Software\Cygames\PrincessConnectReDive`) per account. Shared game assets (`manifest.db` and the LocalLow asset cache) are account-agnostic and are never copied, so switching accounts does not trigger massive asset re-downloads.
*   **Baseline & Restore-on-Exit:** Your pre-launcher account state is captured as a baseline and restored after each launched game session closes. If a previous run was force-killed, the baseline is restored on the next launch (crash recovery).
*   **Per-Account Anti-Detection:** Generates and locks a persistent synthetic hardware identity (`mac_address`, `hdd_serial`, `motherboard`) for each account. No re-randomization on every run, so DMM's server consistently sees the "same physical computer" for a given account.
*   **Direct Launch:** After the registry swap, the game executable is launched directly without opening the DMM Game Player interface, saving time and RAM.
*   **Auto-Updater (Notify-Only):** Checks GitHub Releases for a newer version and notifies you. It opens the release page in your browser and never auto-downloads or auto-installs. Can be disabled in Settings → Advanced.

---

## 💾 Installation

1.  Download the latest installer or portable zip from the [Releases](https://github.com/HetCreep/PriconneMultiAccountLauncher/releases) page only. Release artifacts are built by GitHub Actions on a version tag, not from a maintainer's machine.
2.  Each release attaches `SHA256SUMS.txt` and an SBOM (`sbom.cdx.json`) so you can verify the download before running it.
3.  Double-click the setup file and follow the installation wizard (or extract the portable zip).

---

## 🛠️ How to Use

1.  Launch the main program from its desktop shortcut or the install folder.
2.  Go to the **Account** tab and import your DMM account. Two methods are available:
    *   **Import from DMM** — reads the token from the DMM Game Player you are already logged into on this machine.
    *   **Import from Browser** — logs into DMM through your system default browser (the default browser is auto-detected; there is no browser picker).
3.  Create a launch shortcut for each account you want.
4.  Double-click a shortcut to play and swap between accounts instantly!

> **Region note:** The DMM build of the game is region-locked to Japan (JP). If you are outside Japan, configure a Japanese proxy under **Settings → Advanced** before logging in and launching.

---

## 🤝 Contribution & Support

*   **Bug Reports:** Report any issues on the [Issues](https://github.com/HetCreep/PriconneMultiAccountLauncher/issues) page.
*   **Contribute:** Fork, submit PRs, or check out the code at the main repository [HetCreep/PriconneMultiAccountLauncher](https://github.com/HetCreep/PriconneMultiAccountLauncher).

---

## ⚠️ Disclaimer

This is an **unofficial third-party launcher**. It is **not affiliated with, endorsed by, or supported by DMM.com LLC or Cygames Inc.**

- "Princess Connect! Re:Dive" and "プリンセスコネクト！Re:Dive" are trademarks of Cygames Inc.
- "DMM", "DMM GAMES", and "DMM Game Player" are trademarks of DMM.com LLC.
- Use of this launcher may violate DMM's or Cygames' Terms of Service and may result in account suspension.
- The maintainers provide this software **AS-IS** with no warranty and accept no liability for any action DMM or Cygames may take against your account.
- **USE AT YOUR OWN RISK.**

Read [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md) before use.

---

## 📄 License

This software is licensed under the **MIT License**.
