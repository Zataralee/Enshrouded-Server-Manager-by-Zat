# SteamCMD Update Recovery

## First Install: Exit Code 7

ESM-Z v0.9.5 and Linux alpha.6 initialize SteamCMD with `+quit` before sending the game installation command. SteamCMD's initial download contains a bootstrap executable; its first launch downloads and replaces SteamCMD itself and can return exit code 7. This was reproduced on a clean Windows SteamCMD download on 2026-10-19: the first run printed the localization warning, updated the client, and returned 7; the second run reached the console client and returned 0.

The `ILocalize::AddFile()` message about `public/steambootstrapper_english.txt` can be a first-run warning rather than the cause of a failed game installation. Valve's [Steamworks documentation](https://partner.steamgames.com/doc/sdk/uploading?language=english) recommends running SteamCMD once to bootstrap it. A separate server tool also [reported premature server launches after SteamCMD's self-update](https://github.com/soda3x/ArmaReforgerServerTool/issues/248).

ESM-Z now shows an initialization stage, allows up to three initialization launches with a three-minute timeout per launch, and requires the client and Steam API to report ready with a successful exit before continuing. If a game install still exits with code 7, ESM-Z reinitializes SteamCMD and retries that game command once. Game installation success must still be explicitly confirmed.

Current additions to SteamCMD's own bootstrap and stderr logs are included in the server's `esm-steamcmd.log`. Error summaries prioritize fatal and operational errors over the localization warning. If an install fails or the manager is interrupted, **Retry Install** reuses the existing instance and directory and keeps its selected query port. A ready server uses the ordinary Update Check instead.

The web UI refreshes status about every five seconds and polls an active install about every 1.5 seconds. These are ordinary GET requests, not new install attempts. Successful background polling is quiet in the console from v0.9.5; failed requests and user actions remain logged.

## Enshrouded State 0x6

ESM-Z v0.9.4 and Linux alpha.5 add automatic recovery for this specific SteamCMD response:

```text
Error! App '2278520' state is 0x6 after update job.
```

SteamCMD exit code 8 indicates an unsuccessful process run. It does not identify the cause by itself. An Enshrouded install can become stuck with stale Steam app manifests; Steam content-server or authorization failures can produce the same state. The screenshot provided for this fix confirms the `0x6` state, but does not establish which underlying Steam error caused it on the live host. The workspace clone contains older successful Steam logs, not the live failure's content log.

Other Enshrouded server projects have reproduced this error and recovered by removing the game and redistributable app manifests. One project merged that repair into its force-update command:

- [Original report and maintainer discussion](https://github.com/mornedhels/enshrouded-server/issues/119)
- [Merged manifest-reset fix](https://github.com/mornedhels/enshrouded-server/pull/120)
- [Independent Enshrouded report](https://github.com/jsknnr/enshrouded-server/issues/129)

## What ESM-Z Does

1. Runs one SteamCMD install/update job at a time for this manager process.
2. Saves SteamCMD stdout and stderr directly to the selected server's `logs/esm-steamcmd.log`, which can be read from its Logs tab while the update runs.
3. Requires SteamCMD to exit successfully and confirm that app 2278520 is fully installed or already up to date.
4. If that attempt reports the exact Enshrouded `0x6` state, moves `appmanifest_2278520.acf` and `appmanifest_228980.acf`, when present, from the selected install's `steamapps` folder into a timestamped `steamapps/esm-manifest-backups` subfolder.
5. Retries the same install/update command once. With a fresh install and no manifests, this is a single retry for a possible transient Steam failure.
6. If the retry also fails, restores any original manifests that SteamCMD has not recreated, retains the backups, and reports the failure with its Steam error text and log location.

Recovery only targets these two metadata files in the selected instance. It does not delete game files, saves, configuration, the shared SteamCMD installation, or another instance's manifests. A retry may validate or download game files normally. Manifests remain backed up after a successful repair.

## Using It

Stop the selected server before clicking **Update Check**, or enable **Always run update check before start/restart** and click **Start** or **Restart**. New server installs use the same recovery path and show the retry in Install Status.

On successful recovery, ESM-Z clears the previous update warning and records the successful check time. If both attempts fail during Start/Restart, ESM-Z still tries to launch the existing installation and displays a warning. A new install with no working executable cannot use that fallback.

The **Last update** timestamp records the last successful install/update check, including a check where Steam says the installation is already current. It does not guarantee files changed during that check.

## If Recovery Fails

Open **Logs**, select `esm-steamcmd.log`, and inspect both attempts. SteamCMD's own `<manager folder>/Steamcmd/logs/content_log.txt` on the host can provide more detail about network failures, depot authorization, insufficient storage, or permissions. Resolve the reported problem and run Update Check again. A failed check does not establish that the installed server is current; players may encounter a version mismatch until an update succeeds.
