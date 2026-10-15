<div align="center">

# ⚡️ Cloudflare Worker Auto-Deployer Bot
### ربات هوشمند مدیریت، ساخت و استقرار خودکار ورکرهای کلودفلر

<p align="center">
  <a href="https://t.me/NeoTenet"><img src="https://img.shields.io/badge/Developer-@NeoTenet-0088cc?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Developer"/></a>
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"/>
  <img src="https://img.shields.io/badge/Cloudflare-Workers%20API%20v4-F38020?style=for-the-badge&logo=cloudflare&logoColor=white" alt="Cloudflare API"/>
  <img src="https://img.shields.io/badge/Database-Upstash%20Redis-00E599?style=for-the-badge&logo=redis&logoColor=white" alt="Upstash"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <b>یک ربات تلگرامی همه‌فن‌حریف و خودکار جهت دیپلوی اسکریپت‌های Worker.js، مدیریت Secretها، ساخت دیتابیس‌های KV و D1 بدون ارورهای رایج کلودفلر</b>
</p>

---

[ویژگی‌ها](#-ویژگیهای-برجسته) • [نمودار روند کار](#-نمودار-روند-کار-ربات) • [پیش‌نیازها](#-پیشنیازها) • [راهنمای راه‌اندازی](#-راهنمای-نصب-و-راهاندازی-صفر-تا-صد) • [متغیرهای محیطی](#-متغیرهای-محیطی-environment-variables) • [پشتیبانی](#-توسعهدهنده-و-پشتیبانی)

</div>

---

## 🌟 ویژگی‌های برجسته

- ⚡️ **لینک جادویی ساخت توکن (تک‌کلیک):** تولید مستقیم توکن کلودفلر با تنظیم خودکار `All accounts` و `All zones`.
- 🚀 **پشتیبانی از ES Modules:** پشتیبانی از اسکریپت‌های Worker مبتنی بر ES Modules با متادیتای مناسب `multipart/form-data`.
- 📁 **داشبورد تعاملی ورکرها:** نمایش ورکرهای اکانت و امکان انتخاب، بازنویسی کد یا ساخت ورکر جدید.
- 🔐 **مدیریت Secrets:** ثبت مقادیر محرمانه مانند `UUID`، پسوردها یا توکن‌ها روی ورکر.
- 🗄 **دیتابیس KV Storage:** ایجاد KV Namespace و اتصال آن به کد با نام متغیر دلخواه.
- 💾 **دیتابیس D1 SQL:** ساخت دیتابیس D1 و اتصال آن به ورکر.
- 📊 **آمار آنلاین:** نمایش تعداد کاربران و کاربران فعال با استفاده از **Upstash Redis**.
- 🧠 **ذخیره‌سازی ابری:** نگهداری اطلاعات لازم برای کاهش نیاز به ورود مکرر کلید.
- 🔙 **ناوبری یکپارچه:** دکمه‌های بازگشت به منو و لغو عملیات در مراحل مختلف.

---

## 🧭 نمودار روند کار ربات

نمودار زیر همان ساختار گردش کار موجود در فایل SVG ارسالی شماست. فایل `workflow.svg` در کنار README قرار دارد تا نمودار در صفحه اصلی مخزن GitHub نمایش داده شود.

<p align="center">
  <img src="./workflow.svg" alt="نمودار روند کار Cloudflare Worker Auto-Deployer Bot" width="760"/>
</p>

---

## 🏗 ساختار فنی پروژه

```text
├── bot.py                # کد اصلی ربات و ارتباط با Telegram و Cloudflare API
├── requirements.txt      # وابستگی‌های پایتون
├── workflow.svg          # نمودار روند کار ربات
└── README.md             # مستندات پروژه
```

## 📋 پیش‌نیازها

پیش از راه‌اندازی، مطمئن شوید اطلاعات زیر را در اختیار دارید:

1. **توکن ربات تلگرام:** از طریق [@BotFather](https://t.me/BotFather) دستور `/newbot` را ارسال کنید و توکن بگیرید.
2. **اکانت Cloudflare:** یک حساب در [Cloudflare](https://dash.cloudflare.com/) برای استفاده از API.
3. **دیتابیس Upstash Redis (پیشنهادی):** در [کنسول Upstash](https://console.upstash.com/) دیتابیس بسازید و مقادیر REST URL و REST TOKEN را دریافت کنید.

---

## ⚙️ متغیرهای محیطی (Environment Variables)

| نام متغیر | وضعیت | توضیحات |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | اجباری | توکن دریافتی از BotFather |
| `UPSTASH_REST_URL` | اختیاری / پیشنهادی | آدرس REST دیتابیس Upstash |
| `UPSTASH_REST_TOKEN` | اختیاری / پیشنهادی | توکن اتصال به دیتابیس Upstash |

> 💡 اگر متغیرهای Upstash تنظیم نشوند، طبق توضیحات پروژه ممکن است ذخیره‌سازی ابری نشست کاربران و آمار همگانی غیرفعال بماند.

---

## 🚀 راهنمای نصب و راه‌اندازی (صفر تا صد)

### روش اول: اجرا روی سرویس‌های ابری (Botkeep / Zerops / Render / Railway)

1. فایل‌های پروژه را در سرویس میزبانی موردنظر بارگذاری کنید.
2. متغیرهای محیطی را در تنظیمات سرویس وارد کنید.
3. وابستگی‌ها را با استفاده از `requirements.txt` نصب کنید.
4. دستور اجرای متناسب با ساختار پروژه و سرویس را تنظیم کنید.

### روش دوم: اجرا روی سرور لینوکس (Ubuntu / Debian VPS)

1. Python 3.11 یا 3.12 را نصب کنید.
2. فایل‌های پروژه را به سرور منتقل کنید.
3. وابستگی‌ها را نصب کنید:

   ```bash
   pip install -r requirements.txt
   ```

4. متغیرهای محیطی را تنظیم کنید؛ `TELEGRAM_BOT_TOKEN` ضروری است.
5. ربات را با دستور اجرای تعریف‌شده در پروژه اجرا کنید.

> **نکته:** دستور دقیق اجرای برنامه باید با فایل‌ها و کد واقعی پروژه تطبیق داده شود؛ در متن ارائه‌شده دستور قطعی مشخص نشده بود.

---

## 📖 نحوه کارکرد ربات برای کاربران

1. کاربر فرایند شروع را اجرا می‌کند.
2. ربات امکان دریافت توکن Cloudflare را فراهم می‌کند.
3. اطلاعات اکانت استخراج و در صورت پیکربندی، در Upstash ذخیره می‌شود.
4. کاربر یک Worker را انتخاب می‌کند یا Worker جدید می‌سازد.
5. از پنل مدیریت می‌تواند عملیات مربوط به اسکریپت، Secrets، KV و D1 را انجام دهد.

---

## 👨‍💻 توسعه‌دهنده و پشتیبانی

این پروژه با عشق توسط **NeoTenet** طراحی و بهینه‌سازی شده است.

- 📢 **کانال تلگرام:** [@NeoTenet](https://t.me/NeoTenet)
- 💡 **پیشنهادها و گزارش باگ:** از طریق تلگرام یا بخش Issues مخزن GitHub.

<div align="center">
  <sub>ساخته‌شده با ❤️ برای راحتی جامعه اوپن‌سورس</sub>
</div>
