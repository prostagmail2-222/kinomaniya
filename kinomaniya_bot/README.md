# Kinomaniya bot

aiogram 3.x · async SQLAlchemy · PostgreSQL · webhook (Render)

## Rollar
- **Foydalanuvchi** — nom / kod / janr bo'yicha qidiradi, barcha kinolarni ko'radi (uz/ru). Avval majburiy kanallarga a'zo bo'ladi.
- **Admin** — kino qo'shadi (kino yoki serial), qism qo'shadi, tahrirlaydi/o'chiradi, postni kanallarga joylaydi.
- **Owner** (`OWNER_IDS`) — admin qila oladigan hamma ishni + adminlarni, majburiy obuna kanallarni va post kanallarni boshqaradi.

Admin panel: `/admin`. O'z ID ni bilish: `/id`.

## Render'ga joylash
1. GitHub'ga yuklang → Render → **New Web Service** (Free).
2. **Build:** `pip install -r requirements.txt`  **Start:** `python main.py`
3. **Environment:**
   - `PYTHON_VERSION` = `3.12.8`
   - `BOT_TOKEN`, `OWNER_IDS`, `DATABASE_URL` (`.env.example` ga qarang)
   - `WEBHOOK_BASE_URL` shart emas — Render `RENDER_EXTERNAL_URL` ni o'zi beradi.
4. UptimeRobot: **HTTP(s)** monitor → `https://<servis-nomi>.onrender.com/health`, interval **5 daqiqa**.
5. Botni kanallarga **admin** qiling (majburiy obuna va post kanallar uchun).

## Baza haqida (muhim)
Render'ning bepul PostgreSQL bazasi **30 kundan keyin o'chadi** (14 kun imtiyoz muddati bor). Kinolar yo'qolmasligi uchun
bepul va muddatsiz baza ishlating (masalan Neon yoki Supabase) va `DATABASE_URL` ga shuni yozing. Jadvallar birinchi ishga tushishda avtomatik yaratiladi.

## Lokal sinov
`.env` yarating (`WEBHOOK_BASE_URL` bo'sh) → `python main.py` (polling rejimi).
