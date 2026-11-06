# Downloading logs

Starting with Windows stable **0.9.6.4a** and beta **0.9.6.4b**, Logs is a file
download view. It does not stream or preview log contents in the browser.

1. Select a server and open **Logs**.
2. Find a file by name or category. Each entry shows its size and modification
   time in your browser's local timezone.
3. Click **Download**. The browser saves the full file to the computer using
   ESM-Z, including when that computer is different from the server host.
4. Open the file from the browser's Downloads list using your preferred text editor.
5. Click **Refresh** for newly created logs or updated sizes. Search filters
   the current file list without contacting the server.

The download contains the file from its beginning through its size when the
download starts. Later appends are excluded so active logs finish downloading.
Download again for newer entries. If a log is removed, rotated or truncated during
transfer, refresh and retry; an incomplete transfer must not be treated as a full log.
Zero-byte logs can also be downloaded. Files are transferred as their original bytes.
The browser controls save location and opening; ESM-Z does not launch programs.

## Permissions and available files

Users need **logs** permission and an assigned or owned server. Downloads are
restricted to approved log files in that server's `logs` folder and its immediate
`backup` folder. Standard Steam diagnostic text logs are included. Unrelated text
files, configuration, saves, mod packages and arbitrary host paths are excluded.
Symlinks, Windows junctions and hard-linked files are rejected.

Only administrators can download `manager.log`, `manager_updates/update-console.log`
and update-job `helper.log` files. These are available even before adding a server.
Manager logs may contain sensitive operational history; review files before sharing.

## Performance

The file list loads only when needed and on explicit Refresh. Routine status
polls do not scan log directories. Discovery uses fixed locations without recursively
walking mod packages or staged updates. Downloads transfer bounded chunks directly
to the browser; neither side loads a whole log into JavaScript or a JSON response.

The old arbitrary-path `/api/log` preview is retired. Reload older open browser
pages after updating to use the new download interface.
