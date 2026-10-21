# Windows beta channel

Version 0.9.6.1a adds **Manager > Run beta version**. Save the setting, choose
**Check Now**, then **Download & Install Update** and restart ESM-Z. Installation
remains manual. The checkbox selects Windows beta releases and excludes the
separate Linux alpha channel.

Version 0.9.6.1b adds **Server Setup & Config > Mods**. Mod installation is an
administrator operation because mod packages execute code on the server host.
Players may still need EML and matching mods on their own computers.

To return to the paired stable version, disable modding on each managed server
first, uncheck **Run beta version**, save, check, install, and restart ESM-Z.
Server worlds and manager data are preserved by manager updates.

## Upgrading from 0.9.6 or earlier

The old updater compares only three numeric version components. Install
0.9.6.1a manually once: stop ESM-Z, back up the existing installation, extract
the package over it while preserving `enshrouded_manager/data`, and restart.
The corrected updater then distinguishes 0.9.6.1a from 0.9.6.1b.

The stable package has no EML integration or third-party EML binary.

## Remote updates from 0.9.6.2a/b

After this updater has been activated, Download & Install Update also restarts
ESM-Z and reconnects the browser automatically. It preserves the selected channel;
beta retains Mods and stable does not acquire it. Installing this updater through
an older manager still requires one final manual restart. See [Remote Updates](REMOTE_UPDATES.md).
