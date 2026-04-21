# Cloudflare Tunnel — Access the Dashboard from Your Phone

The dashboard runs on `localhost:8000` by default. To reach it from your phone or outside your home network, use a Cloudflare Tunnel.

## Prerequisites

- A Cloudflare account (free tier works)
- `cloudflared` installed on your Linux machine

```bash
# Install cloudflared on Debian/Ubuntu
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

## Quick tunnel (no domain, temporary URL)

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare prints a `*.trycloudflare.com` URL. Open it on your phone.  
**This URL changes every time you restart the tunnel.**

## Persistent tunnel (recommended)

1. Log in: `cloudflared tunnel login`
2. Create a tunnel: `cloudflared tunnel create claude-dashboard`
3. Create a config file at `~/.cloudflared/config.yml`:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /home/<you>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: dashboard.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

4. Route DNS: `cloudflared tunnel route dns claude-dashboard dashboard.yourdomain.com`
5. Run: `cloudflared tunnel run claude-dashboard`

## Security

The dashboard is localhost-only by default — no auth is needed when tunneled from your own machine. If you expose it via Cloudflare, add protection:

**Option A — Cloudflare Access (recommended):**  
In the Cloudflare dashboard → Zero Trust → Access → Applications → add your dashboard URL with an email policy.

**Option B — Shared secret header:**  
Set `DASHBOARD_SECRET=<random string>` in `.env`. The dashboard middleware will require `X-Dashboard-Secret: <value>` on all requests.
