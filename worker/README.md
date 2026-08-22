# دیپلوی سرور خانوادگی روی Cloudflare Workers

این Worker یک سرور VLESS+WS کامل روی زیرساخت Cloudflare است — رایگان، دائمی، بدون سرور شخصی.

## روش ۱ — داشبورد (پیشنهادی، بدون نصب چیزی)

1. برو به [dash.cloudflare.com](https://dash.cloudflare.com) (اگر اکانت نداری، ثبت‌نام رایگان)
2. منوی **Workers & Pages** → **Create** → **Create Worker**
3. اسم: `family-vpn` → **Deploy** (کد پیش‌فرض مهم نیست)
4. روی **Edit code** بزن → همه‌چیز داخل ادیتور را پاک کن → محتوای `worker/vless-worker.js` را Paste کن → **Deploy**
5. آدرس سرورت می‌شود: `https://family-vpn.<یوزرنیم>.workers.dev`

### تست
مرورگر: `https://family-vpn.<یوزرنیم>.workers.dev/` → باید «✅ سرور فعال است» ببینی.

### دریافت کانفیگ
آدرس کانفیگ که به اپ و خانواده می‌دهی:

```
https://family-vpn.<یوزرنیم>.workers.dev/cfg
```

(خروجی `/sub` هم فرمت subscription پایه ۶۴ است برای اپ‌های دیگر)

## روش ۲ — خط فرمان (wrangler)

```bash
npm install -g wrangler
wrangler login
cd worker
wrangler deploy
```

## نکات مهم برای ایران

- دامنه `workers.dev` گاهی روی برخی ISPها مختل است. دو راه‌حل:
  1. در v2rayNG: Settings → **Fragment** فعال (packets = tlshello) ← ساده‌ترین
  2. اگر دامنه ارزان داری (مثلاً از Namecheap)، آن را روی CF ببر و در تنظیمات Worker بخش Settings → Domains اضافه کن — بدون fragment هم پایدار می‌شود.
- در v2rayNG می‌توانی Address کانفیگ را با یکی از IPهای تمیز Cloudflare (از لیست‌های speed-test معروف) عوض کنی؛ Host و SNI باید همان workers.dev بماند.

## تغییر UUID (اختیاری)

اگر خواستی UUID عوض کنی: در داشبورد Worker → Settings → Variables → متغیر `UUID` بساز، یا در `wrangler.toml` مقدارش را ست کن. بعد همه باید کانفیگ دوباره بگیرند.

## محدودیت پلن رایگان

۱۰۰٬۰۰۰ درخواست در روز — برای مصرف خانوادگی خیلی بیشتر از کافیست.
