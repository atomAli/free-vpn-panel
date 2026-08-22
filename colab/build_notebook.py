import json
import os

MD_INTRO = """# تونل موقت خانوادگی (Colab + Xray + Cloudflare)

این نوتبوک یک **فیلترشکن موقت چند ساعته** روی ماشین رایگان Google Colab می‌سازد.

**نحوه کار:**
```
گوشی شما ──► Cloudflare Edge (HTTPS) ◄── تونل ── Colab VM (Xray)
              *.trycloudflare.com
```

**محدودیت‌ها:**
- هر سشن حداکثر حدود ۱۲ ساعت دوام می‌آورد و با بستن مرورگر زودتر تمام می‌شود
- در هر اجرا، کانفیگ جدید است و باید دوباره اسکن شود
- تماس‌های تصویری (UDP) از این مسیر رد نمی‌شوند؛ وب، چت و دانلود اوکی است
- استفاده از Colab به عنوان پروکسی رسماً خلاف قوانین گوگل است؛ مصرف کم خانوادگی معمولاً مشکلی ندارد اما ریسک محدودیت حساب وجود دارد"""

MD_STEP1 = """## گام ۱ — نصب ابزارها

این سلول را فقط **یک بار در هر سشن** اجرا کنید (حدود ۳۰ ثانیه)."""

MD_STEP2 = """## گام ۲ — راه‌اندازی سرور و ساخت کانفیگ

اجرای این سلول، سرور را بالا می‌آورد و **QR Code** کانفیگ را نمایش می‌دهد.
اگر وسط کار خطا داد یا قطع شد، فقط همین سلول را دوباره اجرا کنید."""

MD_STEP3 = """## گام ۳ — نگه‌داشتن سشن (Keep-Alive)

این سلول را اجرا کنید و **تب مرورگر را باز نگه دارید**. برای توقف از دکمه Interrupt استفاده کنید."""

MD_CLIENT = """## دریافت کانفیگ در گوشی

### روش ۱ — اپ اختصاصی (پیشنهادی)
1. اپ **پنل خانواده** را باز کنید (اگر ندارید، روش ۲)
2. اول دکمه **«باز کردن Colab»** داخل اپ را بزنید و سلول‌های همین صفحه را اجرا کنید
3. بعد در اپ دکمه **«اسکن QR»** را بزنید و QR بالای همین صفحه را بگیرید — تمام!
   کانفیگ خودکار به v2rayNG منتقل می‌شود.

### روش ۲ — v2rayNG مستقیم
1. اپ [v2rayNG](https://github.com/2dust/v2rayNG/releases) را نصب کنید (یا از کافه‌بازار/مایکت)
2. در v2rayNG روی علامت **+** بزنید → **Scan QR code** → QR بالای همین صفحه را اسکن کنید
3. کانفیگ انتخاب شود → دکمه گرد پایین صفحه (اتصال)
4. تست: باز کردن google.com

### اگر وصل نشد:
- در v2rayNG: Settings → Fragment را فعال کنید (packets = tlshello) و دوباره وصل شوید
- یا سلول «گام ۲» را دوباره اجرا کنید تا کانفیگ جدید بسازد"""

CELL_INSTALL = '''import os
import subprocess
import sys

os.makedirs("/content/xray", exist_ok=True)

print("[..] Downloading Xray-Core ...")
subprocess.run(
    ["wget", "-q", "-O", "/tmp/xray.zip",
     "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"],
    check=True,
)
subprocess.run(["unzip", "-o", "-q", "/tmp/xray.zip", "-d", "/content/xray"], check=True)
subprocess.run(["chmod", "+x", "/content/xray/xray"], check=True)

print("[..] Downloading cloudflared ...")
subprocess.run(
    ["wget", "-q", "-O", "/usr/local/bin/cloudflared",
     "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"],
    check=True,
)
subprocess.run(["chmod", "+x", "/usr/local/bin/cloudflared"], check=True)

print("[..] Installing qrcode library ...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "qrcode", "pillow"], check=True)

print()
print("[OK] All tools installed. Run the next cell.")
'''

CELL_RUN = '''import json
import re
import secrets
import subprocess
import time
import urllib.parse
import uuid as uuidlib

WS_PORT = 8001


def stop_old():
    for name in ("xray", "cloudflared"):
        subprocess.run(["pkill", "-f", name], capture_output=True)


stop_old()
time.sleep(1)

CLIENT_UUID = str(uuidlib.uuid4())
WS_PATH = "/" + secrets.token_hex(6)

xray_conf = {
    "log": {"loglevel": "warning"},
    "inbounds": [
        {
            "tag": "vless-ws",
            "listen": "127.0.0.1",
            "port": WS_PORT,
            "protocol": "vless",
            "settings": {"clients": [{"id": CLIENT_UUID}], "decryption": "none"},
            "streamSettings": {
                "network": "ws",
                "security": "none",
                "wsSettings": {"path": WS_PATH},
            },
        }
    ],
    "outbounds": [{"protocol": "freedom"}, {"protocol": "blackhole", "tag": "block"}],
}

with open("/content/xray/config.json", "w") as f:
    json.dump(xray_conf, f, indent=2)

xray_proc = subprocess.Popen(
    ["/content/xray/xray", "run", "-c", "/content/xray/config.json"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(2)

LOG_PATH = "/content/cf.log"
open(LOG_PATH, "w").close()
cf_proc = subprocess.Popen(
    [
        "/usr/local/bin/cloudflared",
        "tunnel",
        "--url",
        f"http://localhost:{WS_PORT}",
        "--no-autoupdate",
    ],
    stdout=open(LOG_PATH, "a"),
    stderr=subprocess.STDOUT,
)

print("[..] Building Cloudflare tunnel (takes ~10s) ...")
tunnel_host = None
for _ in range(30):
    time.sleep(1)
    m = re.search(r"https://([a-z0-9-]+\\.trycloudflare\\.com)", open(LOG_PATH).read())
    if m:
        tunnel_host = m.group(1)
        break

if not tunnel_host:
    print(open(LOG_PATH).read())
    raise RuntimeError("Tunnel failed - just run this cell again")

params = {
    "encryption": "none",
    "security": "tls",
    "sni": tunnel_host,
    "type": "ws",
    "host": tunnel_host,
    "path": WS_PATH,
}
uri = f"vless://{CLIENT_UUID}@{tunnel_host}:443?" + urllib.parse.urlencode(params)
uri += "#Colab-Family"

import qrcode
from IPython.display import Image, display

img = qrcode.make(uri)
img.save("/content/vless-config.png")

print("=" * 56)
print("Config is ready. Scan this QR with v2rayNG:")
print("=" * 56)
print()
print(uri)
print()
display(Image("/content/vless-config.png"))

print(f"UUID  : {CLIENT_UUID}")
print(f"Path  : {WS_PATH}")
print(f"Tunnel: {tunnel_host}")
print()
print("This config works while THIS notebook stays open and running.")
'''

CELL_KEEPALIVE = '''import datetime
import time

import requests

INTERVAL_SECONDS = 90
start_time = time.time()
print("Keep-alive started. To stop: Runtime > Interrupt execution")
while True:
    try:
        requests.get(f"https://{tunnel_host}{WS_PATH}", timeout=15)
    except Exception:
        pass
    minutes = int((time.time() - start_time) // 60)
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] Session alive for {minutes} min", flush=True)
    time.sleep(INTERVAL_SECONDS)
'''


def src_lines(text):
    return text.splitlines(keepends=True)


cells = []
for md in (MD_INTRO, MD_STEP1):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": src_lines(md)})
for code_cell in (CELL_INSTALL,):
    compile(code_cell, "<install>", "exec")
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
                  "outputs": [], "source": src_lines(code_cell)})
cells.append({"cell_type": "markdown", "metadata": {}, "source": src_lines(MD_STEP2)})
compile(CELL_RUN, "<run>", "exec")
cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
              "outputs": [], "source": src_lines(CELL_RUN)})
cells.append({"cell_type": "markdown", "metadata": {}, "source": src_lines(MD_STEP3)})
compile(CELL_KEEPALIVE, "<keepalive>", "exec")
cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
              "outputs": [], "source": src_lines(CELL_KEEPALIVE)})
cells.append({"cell_type": "markdown", "metadata": {}, "source": src_lines(MD_CLIENT)})

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {"name": "family-vpn-colab.ipynb", "provenance": []},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "cells": cells,
}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "family-vpn-colab.ipynb")
with open(out, "w") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)
print(f"Wrote {out} with {len(cells)} cells")
