# WSL2 Keep-Alive

By default, WSL2 shuts down after a period of inactivity. To prevent the bot from stopping when you're not actively using your machine:

## 1. Enable systemd in WSL2

Edit (or create) `/etc/wsl.conf` inside WSL:

```ini
[boot]
systemd=true
```

Then restart WSL from PowerShell:

```powershell
wsl --shutdown
```

Re-open your WSL terminal. Verify with:

```bash
systemctl --version
```

## 2. Disable the idle timeout

In Windows, edit (or create) `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
vmIdleTimeout=-1
```

Restart WSL again:

```powershell
wsl --shutdown
```

## 3. Enable and start the bot service

```bash
systemctl --user enable claude-main.service
systemctl --user start claude-main.service
systemctl --user status claude-main.service
```

## 4. Enable user lingering (run services without an active login session)

```bash
loginctl enable-linger $USER
```

## Verify

After a fresh `wsl --shutdown` and re-open:

```bash
systemctl --user status claude-main.service
# Should show: active (running)
```
