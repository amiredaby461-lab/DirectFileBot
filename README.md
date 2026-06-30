# Direct File Transfer Bot on GitHub Actions

این پروژه یک ربات تلگرام برای دریافت لینک دانلود مستقیم، اعتبارسنجی لینک، دانلود فایل روی GitHub Actions، و ارسال همان فایل به‌صورت Document در تلگرام است.

## نکته مهم درباره محدودیت فنی

با توجه به این‌که فقط GitHub Actions مجاز است، این پروژه **نمی‌تواند یک بات 24/7 واقعی و همیشه‌آنلاین** مثل یک VPS باشد.  
پس معماری این ریپو بر پایهٔ این اصل طراحی شده است:

- GitHub Actions به‌صورت زمان‌بندی‌شده اجرا می‌شود.
- هر اجرا، پیام‌های جدید تلگرام را می‌خواند.
- لینک‌ها را اعتبارسنجی می‌کند.
- در صورت عبور از بررسی‌ها، فایل را دانلود و سپس به تلگرام ارسال می‌کند. سقف ارسال به تلگرام روی ۱۹۵۰ مگابایت قفل شده است.
- وضعیت صف و آمار داخل خود ریپو ذخیره می‌شود.

اگر پاسخ فوریِ لحظه‌ای در حد وب‌هوک/سرور همیشه‌روشن لازم باشد، آن سناریو با محدودیت‌های این پروژه عملاً قابل‌اجرا نیست. این پروژه نزدیک‌ترین پیاده‌سازی عملی در چارچوب محدودیت‌های شماست.

## قابلیت‌ها

- سقف سخت‌گیرانهٔ ارسال به تلگرام: 1950 MB

- Python 3.12
- AsyncIO
- aiogram 3.x
- aiohttp
- Clean Architecture-inspired modular layout
- Repository Pattern
- Service Layer
- Dependency Injection
- Type hints everywhere
- Logging
- Retry for download and upload
- Resume download with HTTP Range
- Queue per user
- Cancellation support for queued jobs
- Admin panel inside Telegram
- State persisted in GitHub repository files
- No external database
- No artifacts for user files

## ساختار پروژه

- `bot.py` — نقطه شروع
- `config.py` — تنظیمات محیطی
- `handlers/` — هندلرهای تلگرام
- `services/` — سرویس‌های دامنه
- `repositories/` — ذخیره‌سازی JSON-based
- `models/` — مدل‌ها و enumها
- `middlewares/` — تزریق وابستگی
- `filters/` — فیلترهای سفارشی
- `keyboards/` — کیبوردهای اینلاین
- `utils/` — ابزارهای کمکی
- `.github/workflows/` — فایل workflow
- `workflows/` — یادداشت‌های معماری workflow
- `tests/` — تست‌های واحد

## نصب

### 1) ساخت بات
1. در BotFather بات بسازید.
2. `BOT_TOKEN` را دریافت کنید.
3. `BOT_USERNAME` را هم اگر خواستید در `.env` بگذارید.

### 2) ساخت ریپو
1. این پروژه را در یک GitHub repository قرار دهید.
2. Actions را فعال کنید.
3. در Settings → Secrets and variables → Actions، این Secretها را اضافه کنید:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - `ALLOWED_USER_IDS` (اختیاری)
   - `BLACKLISTED_USER_IDS` (اختیاری)

### 3) تنظیم متغیرها
فایل `.env.example` را به `.env` تبدیل کنید و مقدارها را تنظیم کنید.

## راه‌اندازی روی GitHub Actions

فایل workflow اصلی در مسیر `.github/workflows/bot.yml` قرار دارد.

این workflow:
- به‌صورت زمان‌بندی‌شده اجرا می‌شود
- از secrets استفاده می‌کند
- state را از خود repository می‌خواند و می‌نویسد
- فایل کاربران را داخل `temp/` نگه می‌دارد و در پایان پاک می‌کند

## اجرای محلی

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

اجرای محلی برای توسعه و تست است. سناریوی اصلی، اجرای GitHub Actions است.

## استفاده

### دستورات
- `/start`
- `/help`
- `/status`
- `/queue`
- `/cancel`
- `/settings`
- `/admin`

### جریان کار
1. کاربر لینک مستقیم HTTP/HTTPS را می‌فرستد.
2. ربات HEAD request انجام می‌دهد.
3. اگر لینک معتبر و مستقیم باشد، اطلاعات فایل نمایش داده می‌شود.
4. فایل دانلود می‌شود.
5. همان فایل به‌صورت Document در تلگرام ارسال می‌شود.
6. فایل‌های موقت حذف می‌شوند.

## نکات عملی

- سقف فایل برای ارسال به تلگرام به‌صورت hard cap روی 1950 MB تنظیم شده است تا از خطاهای upload جلوگیری شود.

- لینک HTML، لینک نیازمند لاگین، لینک نیازمند JavaScript، و لینک‌های خصوصی/لوکال رد می‌شوند.
- اگر سرور از Range پشتیبانی کند، دانلود resume می‌شود.
- Retry دانلود و آپلود داخل همان workflow انجام می‌شود.
- فایل‌های کاربر در GitHub artifact ذخیره نمی‌شوند.

## توسعه

- منطق دامنه را در `services/` نگه دارید.
- وضعیت پایدار را فقط از طریق `repositories/` تغییر دهید.
- برای دسترسی‌های جدید، فیلتر و middleware اضافه کنید.
- برای تغییر UI، کیبوردها و message templateها را در `keyboards/` و `handlers/` اصلاح کنید.

## محدودیت‌های واقعی

- GitHub Actions برای پردازش‌های طولانی مناسب است، نه سرویس دائم‌اجرا.
- دریافت پیام‌ها به‌صورت scheduled polling انجام می‌شود.
- cancel روی jobهای در حال دانلود، best-effort است و در نقطه‌های کنترل اعمال می‌شود.
- آمار مصرف GitHub Actions در این پروژه به‌صورت runtime/usage تقریبی ذخیره می‌شود، نه یک حسابداری دقیق billing-level.

## مجوز

MIT


## سقف فایل

Telegram در راهنمای رسمی خود اعلام کرده که فایل‌های ارسالی تا 2 GB برای کاربران عادی و تا 4 GB برای Premium پشتیبانی می‌شوند؛ این پروژه برای اطمینان و جلوگیری از خطای ارسال، سقف را روی 1950 MB نگه می‌دارد.
