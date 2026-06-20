This release fixes a "DMM API error (result_code=203)" that could appear when you create a shortcut, if the selected account's saved login had expired.

## Highlights & Fixes

- **"Create Shortcut" no longer fails with `DMM API error (result_code=203)`**:
  - Creating a shortcut used to fire a live DMM launch request just to read the game's title. That request fails with `result_code=203` ("refresh token is invalid") whenever the selected account's saved login token has expired — which commonly happens after the DMM Game Player client updates. The token is only refreshed when you actually launch the game, never during shortcut creation, so making a shortcut could error out (and pop a misleading message) even though launching the game still worked.
  - Shortcut creation now reads the game icon from your local DMM install and names the shortcut after the filename you type — with no live login call. The error is gone, shortcut creation works even with an expired/offline session, and your saved token is left untouched. Token refresh still happens normally the moment you launch the game.
  - As a side benefit, this removes a launch request that was being sent outside of an actual, user-initiated game launch.

## Note

- If clicking a shortcut shows a login/expired-session error when the game tries to start, that account's saved DMM login has expired. Re-import that account (Account tab → import) to refresh it, then launch again.

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- The latest release ships the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM. Older releases keep only their source code.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
