from cachetools import TTLCache

# Hammasi xotirada (bitta jarayon) — 50k foydalanuvchi uchun bir necha MB.
lang_cache: TTLCache = TTLCache(maxsize=300_000, ttl=3600)      # user_id -> "uz"/"ru"
seen_users: TTLCache = TTLCache(maxsize=300_000, ttl=3600)      # bazaga yozilganlar
sub_ok_cache: TTLCache = TTLCache(maxsize=300_000, ttl=180)     # obuna tekshiruvi natijasi
throttle_cache: TTLCache = TTLCache(maxsize=100_000, ttl=0.5)   # spamdan himoya
channels_cache: TTLCache = TTLCache(maxsize=8, ttl=30)          # kanallar ro'yxati
genres_cache: TTLCache = TTLCache(maxsize=1, ttl=60)            # janrlar ro'yxati
