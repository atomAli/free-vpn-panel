# پنل فیلترشکن رایگان — راهنمای اجرا

معماری: Oracle Always Free VPS → Marzban → VLESS+Reality (پورت 443)
هزینه کل: صفر | ظرفیت: ده‌ها کاربر با سقف ۱۰TB ترافیک در ماه

---

## مرحله ۱ — ثبت‌نام Oracle Cloud (دستی، ~۱۰ دقیقه)

1. برو به: https://www.oracle.com/cloud/free/
2. **Start for free** → ایمیل و شماره موبایل (شماره خارج از ایران)
3. کارت اعتباری بین‌المللی برای وریفای (هیچ چارجی نمی‌شه؛ فقط هولد موقت)
4. ⚠️ **انتخاب Home Region خیلی مهمه و بعداً قابل تغییر نیست.**
   بهترین گزینه‌ها به ترتیب اولویت برای پینگ ایران:
   `Germany Central (Frankfurt)` > `Switzerland North (Zurich)` > `France South (Marseille)`
5. بعد از ورود به کنسول، از منو **Upgrade to Paid Account** نزن! حساب Free بمونه.

## مرحله ۲ — ساخت سرور

1. منو → **Compute → Instances → Create Instance**
2. تنظیمات:
   - Name: `marzban-vps`
   - Image: **Ubuntu 22.04** (Canonical)
   - Shape: **VM.Standard.A1.Flex** — 2 OCPU / 12 GB RAM
     - اگه خطای `Out of capacity` داد: Shape رو بذار **VM.Standard.E2.1.Micro** (رایگان همیشه)
   - SSH Keys: **Generate a key pair** → هر دو فایل `.key` و `.key.pub` رو دانلود کن
3. قبل از Create تیک **Always Free eligible** بودن shape رو چک کن
4. Create بزن

## مرحله ۳ — IP ثابت + باز کردن پورت‌ها

**IP ثابت (Reserved Public IP):**
1. Instance details → Attached VNICs → IPv4 Addresses → روی IP کلیک کن → **Edit**
2. گزینه **Reserved Public IP** → Create & attach

**باز کردن پورت 443:**
1. Instance details → Subnet → **Security List** → Add Ingress Rules
2. رول جدید: Source CIDR = `0.0.0.0/0`, Protocol = TCP, Destination Port = `443`

## مرحله ۴ — اتصال و نصب خودکار

```bash
chmod 400 ~/Downloads/*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@SERVER_IP
```

بعد از ورود:

```bash
sudo apt-get install -y git && git clone https://github.com/YOUR_REPO/free-vpn-panel.git || mkdir -p free-vpn-panel
```

یا ساده‌تر — محتویات `scripts/server-init.sh` رو کپی کن و این‌طوری اجراش کن:

```bash
nano server-init.sh    # paste, save
sudo bash server-init.sh
```

اسکریپت خودکار انجام می‌ده: آپدیت سیستم، باز کردن iptables اوراکل، فعال‌سازی BBR، ساخت swap (در صورت نیاز)، نصب Marzban، و تولید کلیدهای Reality.

⚠️ خروجی اسکریپت (`PRIVATE_KEY` / `PUBLIC_KEY` / `SHORT_ID`) رو جایی ذخیره کن.

## مرحله ۵ — ساخت ادمین و ورود به پنل

روی سرور:
```bash
marzban-cli admin create --sudo
```

روی مک خودت (ترمینال جدید):
```bash
ssh -N -L 8000:127.0.0.1:8000 -i ~/Downloads/ssh-key-*.key ubuntu@SERVER_IP
```
بعد تو مرورگر: http://localhost:8000/dashboard

## مرحله ۶ — تنظیم هسته Xray

1. تولید مقادیر از خروجی اسکریپت (قبلاً گرفتی)
2. فایل `configs/xray-core-settings.json` رو باز کن، جای `__PRIVATE_KEY__` و `__SHORT_ID__` مقادیر واقعی بذار
3. تو پنل Marzban: **Core Settings** → همه رو پاک کن → JSON آماده رو paste کن → Save → **Restart Core**

## مرحله ۷ — ساخت کاربر تست

1. پنل → **Users** → Create user (مثلاً `test`)
2. روی یوزر کلیک کن → subscription link یا QR code رو بردار
3. گوشی اندروید: اپ **v2rayNG** یا **Hiddify** → import from clipboard/QR

## مرحله ۸ — تست واقعی از ایران

- تست روی MCI (همراه اول)، ایرانسل، و نت ثابت
- اگه یکی از ISPها مشکل داشت، گزارش بده تا inbound جایگزین (WS+TLS از طریق CDN) اضافه کنیم

---

## مسیر دائمی — Cloudflare Worker (پیشنهادی)

سرور فیلترشکن واقعی روی زیرساخت Cloudflare، رایگان و بدون محدودیت زمانی. اپ با یک دکمه کانفیگ می‌گیرد.

1. راهنمای کامل: [`worker/README.md`](worker/README.md) (~۵ دقیقه، فقط یک‌بار توسط خودت)
2. آدرس `https://family-vpn.<یوزرنیم>.workers.dev/cfg` را در `MainActivity.kt` (ثابت `CONFIG_URL`) بگذار
3. APK بیلد بگیر → بین خانواده پخش کن. تمام.

اگر ISP مشکلی با دامنه workers.dev داشت: Fragment در v2rayNG یا دامنه شخصی روی CF (راهنما داخل worker/README.md).

---

## مسیر موقت — Colab + اپ اندروید

برای شروع فوری (بدون سرور): نوتبوک `colab/family-vpn-colab.ipynb` یک تونل چندساعته می‌سازد و اپ `app/` آن را با QR به گوشی‌ها می‌رساند.

### میزبانی نوتبوک روی گیت‌هاب (یک‌بار)

```bash
cd ~/Desktop/Projects/free-vpn-panel
git init && git add . && git commit -m "initial commit"
# در گیت‌هاب یک ریپوی public به اسم free-vpn-panel بساز، بعد:
git remote add origin https://github.com/YOUR_USER/free-vpn-panel.git
git push -u origin main
```

لینک Colab که باید بین خانواده پخش شود (و داخل اپ):

```
https://colab.research.google.com/github/YOUR_USER/free-vpn-panel/blob/main/colab/family-vpn-colab.ipynb
```

⚠️ ریپو حتماً **Public** باشد وگرنه Colab بازش نمی‌کند.

### استفاده روزمره

1. اپ «پنل خانواده» → دکمه **باز کردن Colab**
2. در Colab: Runtime → Run all (~۱ دقیقه)
3. برگرد به اپ → **اسکن QR** → تمام

---

## عیب‌یابی سریع

| مشکل | راه‌حل |
|---|---|
| `Out of capacity` موقع ساخت VM | Shape رو AMD Micro کن یا چند ساعت دیگه دوباره امتحان کن |
| کانفیگ وصل نمی‌شه ولی ping داره | iptables و Security List رو دوباره چک کن |
| IP سرور فیلتر شد | IP جدید Reserved کن (رایگانه) و ادامه بده |
| پنل بالا نمیاد | `docker logs marzban_marzban_1 --tail 50` |

## قدم‌های بعدی

- [x] فاز ۱b: Worker کلادفلر (VLESS+WS) — `worker/`
- [x] فاز ۲a: اپ اندروید ساده (دریافت از سرور / اسکن QR → v2rayNG)
- [ ] فاز ۲b: هسته VPN داخلی در اپ (بدون نیاز به v2rayNG)
- [ ] فاز ۳: اتصال دامنه شخصی به Worker برای پایداری بیشتر
