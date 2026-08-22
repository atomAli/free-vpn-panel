import io
import json
import os
import platform
import re
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid as uuidlib
import zipfile

WS_PORT = int(os.environ.get("WS_PORT", "8001"))
LIFETIME_SECONDS = int(os.environ.get("TUNNEL_LIFETIME_SECONDS", "21000"))
PING_INTERVAL_SECONDS = int(os.environ.get("PING_INTERVAL_SECONDS", "60"))
FAILURES_BEFORE_REBUILD = int(os.environ.get("FAILURES_BEFORE_REBUILD", "10"))
MAX_REBUILDS = int(os.environ.get("MAX_REBUILDS", "5"))
OUT_DIR = os.environ.get("CONFIG_OUT_DIR", "vpn-config")
TOOL_DIR = os.path.join(os.path.expanduser("~"), ".fvp-tools")
RUN_DIR = os.path.join(TOOL_DIR, "run")

XRAY_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
CFD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-linux-amd64"
)
XRAY_BIN = os.path.join(TOOL_DIR, "xray", "xray")
CFD_BIN = os.path.join(TOOL_DIR, "cloudflared")

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
PUBLISH_ENABLED = os.environ.get("PUBLISH_CONFIG", "0") == "1"

xray_proc = None
cfd_proc = None


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def download(url, dest):
    tmp = dest + ".tmp"
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, dest)


def install_tools():
    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    if not os.path.exists(XRAY_BIN):
        log("Downloading Xray-Core ...")
        xdir = os.path.join(TOOL_DIR, "xray")
        os.makedirs(xdir, exist_ok=True)
        zpath = os.path.join(TOOL_DIR, "xray.zip")
        download(XRAY_URL, zpath)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(xdir)
        os.chmod(XRAY_BIN, 0o755)

    if not os.path.exists(CFD_BIN):
        log("Downloading cloudflared ...")
        download(CFD_URL, CFD_BIN)
        os.chmod(CFD_BIN, 0o755)

    log("Tools ready.")


def build_uri(client_uuid, ws_path, tunnel_host):
    params = {
        "encryption": "none",
        "security": "tls",
        "sni": tunnel_host,
        "type": "ws",
        "host": tunnel_host,
        "path": ws_path,
    }
    uri = f"vless://{client_uuid}@{tunnel_host}:443?" + urllib.parse.urlencode(params)
    return uri + "#Family-Auto"


def start_xray(client_uuid, ws_path):
    conf = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "vless-ws",
                "listen": "127.0.0.1",
                "port": WS_PORT,
                "protocol": "vless",
                "settings": {"clients": [{"id": client_uuid}], "decryption": "none"},
                "streamSettings": {
                    "network": "ws",
                    "security": "none",
                    "wsSettings": {"path": ws_path},
                },
            }
        ],
        "outbounds": [{"protocol": "freedom"}, {"protocol": "blackhole", "tag": "block"}],
    }
    conf_path = os.path.join(RUN_DIR, "xray-config.json")
    with open(conf_path, "w") as f:
        json.dump(conf, f, indent=2)

    global xray_proc
    xray_proc = subprocess.Popen(
        [XRAY_BIN, "run", "-c", conf_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    if xray_proc.poll() is not None:
        raise RuntimeError("xray exited immediately")


def start_tunnel():
    global cfd_proc
    log_path = os.path.join(RUN_DIR, "cloudflared.log")
    open(log_path, "w").close()
    cfd_proc = subprocess.Popen(
        [CFD_BIN, "tunnel", "--url", f"http://127.0.0.1:{WS_PORT}", "--no-autoupdate"],
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(45):
        time.sleep(1)
        m = re.search(
            r"https://([a-z0-9-]+\.trycloudflare\.com)",
            open(log_path).read(),
        )
        if m:
            return m.group(1)
    raise RuntimeError("cloudflared failed:\n" + open(log_path).read()[-2000:])


def qr_png_bytes(text):
    import qrcode

    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def save_config(uri):
    with open(os.path.join(OUT_DIR, "vless-uri.txt"), "w") as f:
        f.write(uri + "\n")
    with open(os.path.join(OUT_DIR, "qr.png"), "wb") as f:
        f.write(qr_png_bytes(uri))


def publish_config():
    if not PUBLISH_ENABLED:
        return
    status = subprocess.run(
        ["git", "status", "--porcelain", OUT_DIR], capture_output=True, text=True
    )
    if not status.stdout.strip():
        log("No config changes to publish")
        return

    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True)

    for cmd in (
        ["config", "user.name", "github-actions[bot]"],
        ["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        ["add", OUT_DIR],
        ["commit", "-m", f"update tunnel config [{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}]"],
    ):
        r = git(*cmd)
        if r.returncode != 0:
            log(f"git {cmd[0]} failed: {(r.stderr or r.stdout).strip()[:300]}")
            return
    for _ in range(2):
        r = git("push")
        if r.returncode == 0:
            log("Config published to repo.")
            return
        log(f"push failed, retrying after rebase: {r.stderr.strip()[:300]}")
        git("pull", "--rebase", "--autostash")
    log("Config publish failed.")


def tg_call(method, data=None, files=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/{method}"
    resp = requests_post(url, data=data, files=files)
    payload = resp.json()
    if not payload.get("ok"):
        raise RuntimeError(f"telegram {method}: {payload}")
    return payload


def notify_new_config(uri, tunnel_host, hours_left):
    caption = (
        "کانفیگ جدید آماده شد\n"
        f"اعتبار: حدود {hours_left} ساعت\n"
        f"تونل: {tunnel_host}\n\n"
        f"{uri}"
    )
    photo = qr_png_bytes(uri)
    tg_call(
        "sendPhoto",
        data={"chat_id": TG_CHAT, "caption": caption[:1024]},
        files={"photo": ("qr.png", photo, "image/png")},
    )


def notify_text(text):
    tg_call("sendMessage", data={"chat_id": TG_CHAT, "text": text[:4000]})


def notify_safe(fn, *args):
    if not (TG_TOKEN and TG_CHAT):
        log("Telegram not configured; skipping notification")
        return
    try:
        fn(*args)
    except Exception as e:
        log(f"Telegram notification failed: {e}")


def ping_alive(tunnel_host, ws_path):
    try:
        urllib.request.urlopen(
            f"https://{tunnel_host}{ws_path}", timeout=15
        )
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def cleanup(*_):
    for proc_attr in ("cfd_proc", "xray_proc"):
        proc = globals().get(proc_attr)
        if proc is not None and proc.poll() is None:
            proc.terminate()
    for name in ("xray", "cloudflared"):
        subprocess.run(["pkill", "-f", name], capture_output=True)


def handle_term(signum, _frame):
    raise SystemExit(0)


def requests_post(url, data=None, files=None):
    import requests

    return requests.post(url, data=data, files=files, timeout=30)


def main():
    if platform.system() != "Linux":
        print("This script targets Linux runners (GitHub Actions / Colab VM).")
        sys.exit(1)

    signal.signal(signal.SIGTERM, handle_term)
    install_tools()

    client_uuid = str(uuidlib.uuid4())
    ws_path = "/" + secrets.token_hex(6)
    start_xray(client_uuid, ws_path)

    deadline = time.time() + LIFETIME_SECONDS
    rebuilds = 0
    failures = 0
    host = None

    try:
        while True:
            log("Building Cloudflare quick tunnel (~10s) ...")
            host = start_tunnel()
            uri = build_uri(client_uuid, ws_path, host)
            save_config(uri)
            publish_config()
            hours_left = max(1, int((deadline - time.time()) / 3600))
            log("=" * 56)
            log("Config is ready.")
            log(uri)
            log(f"Tunnel host: {host}")
            log("=" * 56)
            notify_safe(notify_new_config, uri, host, hours_left)

            failures = 0
            while time.time() < deadline:
                time.sleep(PING_INTERVAL_SECONDS)
                minutes = int((deadline - time.time()) / 60) if deadline > time.time() else 0
                if ping_alive(host, ws_path):
                    failures = 0
                    if PING_INTERVAL_SECONDS >= 60:
                        log(f"Alive. ~{minutes} min left in this run.")
                else:
                    failures += 1
                    log(f"Tunnel unreachable ({failures}/{FAILURES_BEFORE_REBUILD})")
                if failures >= FAILURES_BEFORE_REBUILD:
                    break

            if time.time() >= deadline or rebuilds >= MAX_REBUILDS:
                break

            rebuilds += 1
            log(f"Tunnel died; rebuilding (attempt {rebuilds}/{MAX_REBUILDS}) ...")
            if cfd_proc is not None and cfd_proc.poll() is None:
                cfd_proc.terminate()
            time.sleep(2)
    except SystemExit:
        log("Stopped by signal.")
    except Exception as e:
        log(f"FATAL: {e}")
        notify_safe(notify_text, f"Tunnel run failed: {e}")
        raise
    finally:
        cleanup()

    log("Run finished.")


if __name__ == "__main__":
    main()
