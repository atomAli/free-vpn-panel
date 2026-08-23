# فیلترشکن خانوادگی — کانفیگ خودکار هر ۶ ساعت

GitHub Actions هر ۶ ساعت یک تونل جدید (Xray + Cloudflare) بالا می‌آورد و کانفیگ VLESS را همین‌جا منتشر می‌کند. هیچ سروری لازم نیست؛ فقط این ریپو.

## لینک‌های کانفیگ

| فایل | کاربرد |
|---|---|
| [`vpn-config/vless-uri.txt`](https://raw.githubusercontent.com/atomAli/free-vpn-panel/main/vpn-config/vless-uri.txt) | ۵ کانفیگ متنی |
| [`vpn-config/qr.png`](https://raw.githubusercontent.com/atomAli/free-vpn-panel/main/vpn-config/qr.png) | QR کانفیگ اصلی |

هر خط یک کانفیگ مستقل است:

- `Family-Auto` — کانفیگ اصلی (دامنه تونل)
- `Family-Auto-CF1` تا `CF4` — همان سرور با IPهای مختلف کلادفلر؛ اگر ISP شما دامنه تونل را با DNS/IP ببندد، این‌ها از مسیر دیگری وصل می‌شوند

همه ۵ کانفیگ یک UUID و مسیر دارند و به یک سرور می‌رسند.

## استفاده در گوشی

1. متن کامل `vless-uri.txt` را کپی کن
2. **v2rayNG** → دکمه `+` → **Import config from clipboard** → هر ۵ تا ایمپورت می‌شوند
3. یکی‌یکی تست کن (`●` اتصال → باز کردن google.com) → هرکدام که وصل شد همان را نگه دار

### اگر در ایران وصل نشد

1. v2rayNG → **Settings** → **Fragment settings** → فعال:
   - Packets: `tlshello`
   - Length: `100-200`
   - Interval: `10-20`
2. دوباره تک‌تک کانفیگ‌ها (به‌خصوص CF1 تا CF4) را تست کن
3. هیچ‌کدام وصل نشد؟ ران بعدی را صبر کن (حداکثر ۶ ساعت) یا از تب Actions دستی اجرا بزن

## نحوه کار

```
GitHub Actions (هر ۶ ساعت، cron 30 */6 * * *)
   └─ scripts/run_tunnel.py
        ├─ Xray (VLESS+WS روی 127.0.0.1:8001)
        ├─ cloudflared quick tunnel → *.trycloudflare.com
        ├─ ساخت ۵ کانفیگ + QR
        ├─ commit و push در vpn-config/
        └─ پایش سلامت هر ۶۰ ثانیه؛ در صورت قطعی، تونل جدید می‌سازد
```

هر سشن ~۵٫۸ ساعت دوام دارد؛ بعدش ران بعدی خودکار شروع می‌شود.

## اجرای دستی

تب **Actions** → **family-tunnel** → **Run workflow** — کانفیگ جدید حدود ۲–۳ دقیقه دیگر منتشر می‌شود.

## نوتیفیکیشن تلگرم (اختیاری)

با تعریف این secrets در تنظیمات ریپو، هر کانفیگ جدید به تلگرام هم می‌آید:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| لینک قدیمی است | تب Actions → آخرین ران family-tunnel را چک کن؛ موفق بوده؟ فایل تازه شده |
| ران شکست خورده | Run workflow را دستی بزن |
| در ایران قطع شد | اول Fragment، بعد صبر برای ران بعدی |
