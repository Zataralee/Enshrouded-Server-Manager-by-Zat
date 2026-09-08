# Enshrouded Manager User Guide

This guide is for regular manager users. It does not cover admin-only setup, user management, manager ports, or machine-wide storage settings.

If you do not see a tab or button mentioned here, your account probably does not have that permission. Ask the primary admin to assign the server or permission to your manager account.

The manager also has an `Instructions` tab. It shows guidance for the tabs and features your account can access.

The `Updates` tab shows the current manager version and a short history of what changed in recent releases.

## Signing In

1. Open the manager URL provided by the admin.
2. Sign in with the username and initial password the admin gave you.
3. Open `Account` > `My Account` and change your password.

If you forget your password, ask the admin to reset it. The admin will give you a new temporary password.

## Creating An Account With An Invite Code

An admin or server owner may give you a one-time invite code instead of creating your account manually. They may also send you an invite link with the code already included.

1. Open the manager URL, or click the invite link you were given.
2. Use `Create Account With Invite`.
3. Enter the invite code if it was not filled in automatically.
4. Choose your username and password.
5. Enter your Steam name and Steam email.
6. Click `Create Account`.

Invite codes can expire and can only be used once. If the code is expired, already used, or invalidated, ask the person who gave it to you for a new one.

Steam name and Steam email are stored with your manager account so admins can cross-reference server access later if needed.

If you are given a plain code, paste it into `Invite code`. If you are given an invite URL, opening the link fills in the code for you.

## Generating Invite Codes

If your account has access to `Account` > `Invites`, you can create one-time invite codes for other users.

Use the optional title and description to record who the code is for or why it was created. `Expires in` uses days / hours / minutes. For example, `01 / 00 / 00` means 1 day and `00 / 02 / 30` means 2 hours and 30 minutes.

After generating a code, use either `Copy code` or `Copy Invite URL`. Used and expired invite-code history can be cleared from the invite lists.

## Choosing a Server

Use the server dropdown in the top-right of the page to switch between servers assigned to you.

You can only see servers that you created or that an admin assigned to your account.

## Dashboard

The `Dashboard` tab is used to:

- Start a server.
- Stop a server.
- Restart a server.
- Run an update check.
- Enable update checks before start/restart.
- Add scheduled restart times.

If a server crashes, the manager may restart it automatically depending on how the admin or server owner configured it.

Running servers are meant to stay online if the manager itself is restarted for an update. Use `Stop` when you actually want to shut down the selected game server.

## Adding an Existing Server

Use this when the Enshrouded dedicated server already exists on the hosting machine.

### Existing Server On The Pathfinders Hosted Machine

1. Open `Server Setup & Config` > `Setup & Instances`.
2. Under `Use Existing Install`, enter a friendly `Instance name`.
3. Enter the full install folder path given to you by the Pathfinders admin.
4. Click `Add Existing Server`.

The folder must be the server install folder that contains `enshrouded_server.exe`.

If you do not know the path, ask the Pathfinders admin. Do not guess by creating a new server unless you actually want a new install.

### Existing Server On A Non-Pathfinders Machine

1. Open the manager running on that hosting machine.
2. Open `Server Setup & Config` > `Setup & Instances`.
3. Under `Use Existing Install`, enter a friendly `Instance name`.
4. Enter the full local path to that machine's Enshrouded dedicated server install folder.
5. Click `Add Existing Server`.

Examples of valid paths might look like:

```text
F:\Servers\My_Enshrouded_Server
C:\Enshrouded\DedicatedServer
D:\SteamCMD\steamapps\common\EnshroudedServer
```

The path must be local to the machine running the manager. A path on your personal PC will not work unless the manager is also running on your personal PC.

Adding an existing server is usually quick. It does not reinstall the game.

## Installing A New Server

Use this when you want the manager to create a fresh Enshrouded dedicated server install.

1. Open `Server Setup & Config` > `Setup & Instances`.
2. Under `Install New Server`, enter an `Instance name`.
3. Enter an `Instance name`. `Directory` fills in automatically from the instance name.
4. Change `Directory` only if you want the server folder to use a different name.
5. Enter a `Query port` only if you do not want the default port. The default is `15637`.
6. Click `Download SteamCMD & Install Server` once.
7. Watch the `Install Status` panel.
8. Wait until it says the server is installed and ready for configuration.
9. Click `Use Server` in the install status row to select the new server.
10. Click `Dismiss` after you no longer need the completed install message.

Important: do not click the install button again while the install is running.

New installs can take several minutes. On a slow connection, or when SteamCMD is being downloaded for the first time, it can take 10-20 minutes or longer. During that time the manager is working server-side even if the page looks quiet between status updates.

The `Install Status` panel shows active and recent installs for your account. If you refresh the page or leave the Setup tab and come back, the status panel should still show that the install is running. Admins can also see active install jobs.

When an install completes, the installed server should also appear in the `Instances` list. If the completed install message is still visible, it is only a status record. Use `Use Server` to select the server, or `Dismiss` to clear the completed status from your view.

The manager does the following during a new install:

1. Registers the server instance.
2. Downloads SteamCMD if needed.
3. Installs or validates the Enshrouded dedicated server.
4. Creates `enshrouded_server.json`.
5. Starts the server once so Enshrouded can finish generating required files.
6. Stops the server.
7. Marks the server ready for configuration.

If the install fails, the `Install Status` panel will show an error. If you refresh the browser and are not sure what happened, check the `Instances` list first or ask an admin before starting another install.

## Removed Servers

Removing a server removes it from the manager list. The manager asks whether you also want to delete the server files.

Removed servers appear under `Removed Servers` if you created them or they were assigned to you. Use `Restore` to add one back to the manager. Use `Delete Files` only when you are sure the server folder should be permanently deleted.

If you cannot see a removed server you expected, ask an admin to assign or restore it.

## Server Config

Use `Server Setup & Config` > `Server Config` to edit the selected server's `enshrouded_server.json`.

Common settings include:

- Server name.
- IP bind.
- Query port.
- Player slots.
- Save/log folders.
- Voice and text chat.
- Difficulty preset.

Public/passwordless access is handled through game server groups. A group with a blank password can be joined without a group password.

If the server is running, the manager will warn you before applying config changes that require a restart.

## Game Server Accounts

This tab manages Enshrouded in-game groups and bans, not manager login accounts.

Use `Game Server Accounts` to manage game access groups and group passwords. Use `Bans` to manage banned game accounts. The default groups are `Admin` and `Friends`; `Friends` has normal world permissions but cannot kick or ban.

Manager login accounts are controlled by the admin and are not available to regular users.

## Logs

Use `Logs` to read manager and server log files for the selected server.

Logs are helpful when:

- A server will not start.
- A player cannot connect.
- You need to confirm whether an update or backup ran.
- A setting did not behave as expected.

## Webhooks

Use `Server Setup & Config` > `Webhooks` to configure notifications for the server selected in the header.

Each server has its own webhook list. You will only see webhooks for the currently selected server. A server can have multiple webhooks, and each one can use a different name, destination, mode, and set of events.

Use `Add Webhook` for a new destination. Current Webhooks lets you edit, test, enable or disable, and delete each saved webhook independently. Saved URLs are hidden after saving.

## Saves & Backups

Use `Server Setup & Config` > `Saves & Backups` to:

- Import a save folder from your own PC into the selected server.
- Upload a zipped save game from your own PC.
- Find local saves on the machine running the manager, if you are using the manager locally.
- Review the imported save history for the selected server.
- Create a local backup.
- Push a backup to FTP, if FTP is configured for that server.
- Enable automatic backups for that server.
- Set the automatic backup interval.

When you import a save, the manager creates a backup of the current save first.

Most users should use `Choose Save Folder From This PC`.

After you choose a folder, the manager looks for Enshrouded world file groups. A single world usually has files that share the same ID, such as:

```text
3ad85aea
3ad85aea-0
3ad85aea-1
3ad85aea-index
3ad85aea_inf
```

If the folder has several worlds, you will see several world file IDs. Select one world ID and import only that world. The world file ID may not match the world name you see in-game because Enshrouded names local save files by creation order.

During import, the manager stops the server if needed, backs up the current server save, and installs the selected world into the server's primary save slot. This matters because dedicated servers often load the primary world filename even when your local save came from a different world file ID.

Look in these locations on your PC:

```text
C:\Program Files (x86)\Steam\userdata\YOUR_STEAM_ID\1203620\remote
%USERPROFILE%\Saved Games\enshrouded
```

The Steam Cloud location is the most common. If Steam is installed somewhere other than `C:\Program Files (x86)\Steam`, open your Steam install folder, then browse to:

```text
userdata\YOUR_STEAM_ID\1203620\remote
```

If you cannot use folder upload in your browser, zip the save folder and use `Upload Save ZIP`.

`Find Local Saves` only searches the machine running the manager. Remote users should normally use `Choose Save Folder From This PC`.

Automatic backups are stored under the manager's configured backup location in a subfolder for each server. The admin controls the root backup location and the minimum/maximum allowed backup interval.

## If Something Seems Stuck

For new installs, wait longer than you think you need to. SteamCMD and game validation can be slow, especially the first time.

Before creating another server:

1. Check the `Install Status` panel.
2. Check the `Instances` list.
3. Check `Logs`, if you have permission.
4. Ask an admin to look at the manager log.

Creating the same server again can leave you with duplicate folders, duplicate ports, or confusing instance names.
