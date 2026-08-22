# اپ پنل خانواده (اندروید)

اپ ساده سه‌مرحله‌ای:

```
[۱ باز کردن Colab] → سلول‌ها را اجرا می‌کنید
[۲ اسکن QR]       → کانفیگ گرفته می‌شود، کپی و به v2rayNG فرستاده می‌شود
(یا ورود دستی vless:// برای مواقع اضطراری)
```

## ساخت APK

1. **Android Studio** (نسخه Koala یا جدیدتر) را نصب کنید
2. `File → Open` و پوشه `app/` همین ریپو را باز کنید (گریدل خودکار sync می‌شود)
3. در `app/src/main/java/com/family/vpnpanel/MainActivity.kt` مقدار `COLAB_URL` را با آدرس واقعی ریپوی گیت‌هاب خودتان عوض کنید:
   ```
   https://colab.research.google.com/github/<YOUR_USER>/free-vpn-panel/blob/main/colab/family-vpn-colab.ipynb
   ```
4. از منو `Build → Build App Bundle(s) / APK(s) → Build APK(s)`
5. فایل خروجی: `app/app/build/outputs/apk/debug/app-debug.apk` — به گوشی‌های خانواده بفرستید

## نکات

- اولین بار موقع اسکن، اجازه **دوربین** را تایید کنید
- بعد از دریافت کانفیگ، اپ آن را به v2rayNG می‌فرستد؛ اگر نصب نباشد فقط کپی می‌شود
- هر بار که نوتبوک Colab دوباره اجرا شود QR جدید است — فقط دوباره اسکن کنید

## بعداً (فاز ۳)

- هسته VPN داخلی (Xray/AndroidLibXrayLite) تا نیاز به v2rayNG نباشد
- انتقال خودکار بدون اسکن (رله Cloudflare + کد جفت‌سازی)
