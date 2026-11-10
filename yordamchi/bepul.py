"""Bepul rejim: API kalitsiz, AI'siz ishlaydigan buyruqlar.

O'zbekcha buyruqlarni so'z-qoliplar orqali tushunadi. Ilovalar, telefondagi
qo'shiqlar, vaqt va eslatmalar internetsiz ham ishlaydi; YouTube uchun internet kerak.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from . import phone
from .scheduler import SCHEDULER, TZ
from .tools import ToolError, calculate

HELP = """\
Men tushunadigan buyruqlar (misollar):
  📱 Telegramni och | Instagramga kir | kamerani och | YouTube och
  🎵 Sevara Nazarxon qo'shig'ini qo'y | musiqa qo'y | telefondagi musiqani qo'y
  🎬 O'tkan kunlar filmini qo'y | multfilm qo'y | Shahzoda klipini ko'rsat
  ⏹  musiqani to'xtat
  🕐 soat nechi | bugun nechanchi sana
  ⏰ soat 7:00 da musiqa qo'y | 20 daqiqadan keyin choyni eslat | ertaga 6:30 da uyg'ot
     rejalar | 2-rejani bekor qil
  🔎 qidir: Toshkent ob-havosi | kun.uz ni och
  📞 qo'ng'iroq qil +998901234567
  🧮 hisobla 125*4+10"""

# Ilova nomining turli yozilishlari -> phone.APPS kaliti
ALIASES = {
    "telegram": "telegram", "telegramm": "telegram", "telega": "telegram", "tg": "telegram",
    "instagram": "instagram", "insta": "instagram", "instagramm": "instagram",
    "youtube": "youtube", "yutub": "youtube", "youtub": "youtube", "you tube": "youtube", "yutube": "youtube",
    "youtube music": "youtube music", "yutub muzik": "youtube music",
    "whatsapp": "whatsapp", "watsap": "whatsapp", "vatsap": "whatsapp", "whatsap": "whatsapp", "vatsapp": "whatsapp",
    "tiktok": "tiktok", "tik tok": "tiktok", "tik-tok": "tiktok",
    "spotify": "spotify", "facebook": "facebook", "feysbuk": "facebook",
    "chrome": "chrome", "xrom": "chrome", "brauzer": "chrome", "google": "chrome",
    "xarita": "xarita", "karta": "xarita", "maps": "xarita", "google maps": "xarita",
    "gmail": "gmail", "pochta": "gmail",
    "play market": "play market", "pley market": "play market", "playmarket": "play market", "market": "play market",
    "kamera": "kamera", "kamira": "kamera", "camera": "kamera",
    "sozlamalar": "sozlamalar", "sozlama": "sozlamalar", "nastroyka": "sozlamalar", "sozlamalarni": "sozlamalar",
    "click": "click", "klik": "click", "payme": "payme", "peyme": "payme",
    "yandex go": "yandex go", "yandex taksi": "yandex go", "taksi": "yandex go",
}

FILLER = {
    "iltimos", "menga", "bizga", "qo'y", "qo'yib", "qo'ygin", "qo'ying", "ber", "bering",
    "bergin", "yoq", "yoqib", "eshittir", "ijro", "et", "qil", "ko'rsat", "ko'rsatib",
    "ochib", "och", "ko'r", "ko'raylik", "eshitaylik", "tingla", "top", "topib",
    "qo'shiq", "qo'shig'ini", "qo'shig'i", "qo'shiqlarini", "qo'shiqni", "qo'shiqlar",
    "musiqa", "musiqasini", "musiqani", "muzika", "ashula", "ashulasini",
    "video", "videosini", "videoni", "film", "filmini", "filmni", "kino", "kinoni",
    "kinosini", "klip", "klipini", "klipni", "youtube", "youtubeda", "youtube'da", "yutubda",
    "bitta", "biror", "yangi", "endi", "hozir", "ham", "chi", "bilan",
}


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[‘’ʻʼ`´]", "'", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .!?,")


def strip_filler(text: str) -> str:
    words = [w for w in re.split(r"[\s,]+", text) if w and w not in FILLER]
    return " ".join(words).strip(" .!?,'\"")


def _find_app(text: str) -> str | None:
    for alias in sorted(ALIASES, key=len, reverse=True):
        if re.search(rf"(^|\s){re.escape(alias)}(ni|ga|da|ning)?(\s|$)", text):
            return ALIASES[alias]
    return None


# --------------------------------------------------------- vaqtni ajratish
_TIME_PATTERNS = [
    # 20 daqiqadan keyin / 1 soatdan so'ng / 30 minutdan keyin
    (re.compile(r"(\d+)\s*(daqiqa|minut|min)\w*\s*(keyin|so'ng)"), "min"),
    (re.compile(r"(\d+)\s*soat\w*\s*(keyin|so'ng)"), "hour"),
    # (ertaga) (soat) 7:30 da / soat 7 da
    (re.compile(r"(ertaga\s+)?(ertalab\s+|kechqurun\s+|kechki\s+)?(soat\s+)?(\d{1,2})[:.](\d{2})\s*(da|ga)?\b"), "clock"),
    (re.compile(r"(ertaga\s+)?(ertalab\s+|kechqurun\s+|kechki\s+)?soat\s+(\d{1,2})\s*(da|ga)\b"), "clock_h"),
]


def extract_time(text: str) -> tuple[str | None, str]:
    """Matndan vaqtni ajratadi: (scheduler uchun vaqt, qolgan buyruq)."""
    now = datetime.now(TZ)
    for pattern, kind in _TIME_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        rest = (text[: m.start()] + " " + text[m.end():]).strip()
        if kind == "min":
            return f"+{m.group(1)}", rest
        if kind == "hour":
            return f"+{int(m.group(1)) * 60}", rest
        if kind == "clock":
            tomorrow, part, h, mnt = m.group(1), m.group(2), int(m.group(4)), int(m.group(5))
        else:
            tomorrow, part, h, mnt = m.group(1), m.group(2), int(m.group(3)), 0
        if part and part.strip() in ("kechqurun", "kechki") and h < 12:
            h += 12
        if h > 23 or mnt > 59:
            return None, text
        if tomorrow:
            day = (now + timedelta(days=1)).date()
            return f"{day:%Y-%m-%d} {h:02d}:{mnt:02d}", rest
        return f"{h:02d}:{mnt:02d}", rest
    return None, text


# ---------------------------------------------------------------- buyruqlar
def handle(raw: str) -> str:
    text = normalize(raw)
    if not text:
        return "Buyruq bering. Masalan: Telegramni och."

    if text in ("yordam", "help", "nima qila olasan", "buyruqlar", "nimalar qila olasan"):
        return HELP

    # Rejalar
    if text in ("rejalar", "rejalarim", "eslatmalar", "rejalarni ko'rsat"):
        return SCHEDULER.list()
    m = re.search(r"(\d+)\s*-?\s*(reja\w*|eslatma\w*)\s*(ni)?\s*bekor", text)
    if m:
        return SCHEDULER.cancel(int(m.group(1)))

    # Vaqtga rejalashtirish
    when, rest = extract_time(text)
    if when and rest and not re.fullmatch(r"(soat )?nech\w*", rest):
        rest = re.sub(r"^(va|keyin)\s+", "", rest).strip()
        if re.search(r"eslat|esimga sol|uyg'ot", rest) and not re.search(r"qo'shiq|qo'shig'|musiqa|video", rest):
            task = "eslatma: " + (re.sub(r"\s*(ni|ga)?\s*(eslat\w*|esimga sol\w*)", "", rest).strip() or rest)
            if "uyg'ot" in rest:
                task = "uyg'otish"
        else:
            task = rest
        try:
            return SCHEDULER.add(when, task)
        except ValueError as exc:
            return str(exc)

    # Vaqt va sana
    if re.search(r"soat\s+nech|vaqt\s+(qancha|nech)|hozir\s+soat", text):
        return f"Hozir soat {datetime.now(TZ):%H:%M}."
    if re.search(r"(nechanchi|qaysi)\s+(sana|kun)|bugun\s+(nechanchi|qaysi|sana)|sana\s+nech", text):
        days = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
        months = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
                  "sentabr", "oktabr", "noyabr", "dekabr"]
        now = datetime.now(TZ)
        return f"Bugun {now.day}-{months[now.month - 1]}, {now.year}-yil, {days[now.weekday()]}."

    # Hisoblash
    m = re.match(r"^(hisobla|hisoblab ber|nechchi|necha)\s*:?\s*(.+)$", text)
    expr = m.group(2) if m else (text if re.fullmatch(r"[\d\s+\-*/().,x×÷^%]+", text) else None)
    if expr and re.search(r"\d", expr):
        expr = expr.replace("x", "*").replace("×", "*").replace("÷", "/").replace("^", "**").replace(",", ".")
        expr = expr.rstrip("= ?")
        try:
            return f"{expr} = {_fmt(calculate(expr))}"
        except ToolError as exc:
            return str(exc)

    # Musiqani to'xtatish
    if re.search(r"(to'xtat|o'chir|stop)", text) and re.search(r"musiqa|qo'shiq|qo'shig'|muzika|ashula|^to'xtat|^stop", text):
        return phone.stop_music()

    # Qo'ng'iroq
    m = re.search(r"(\+?\d[\d\s\-()]{6,})", text)
    if m and re.search(r"qo'ng'iroq|telefon qil|zvon|chaqir", text):
        return phone.call_number(m.group(1))

    # Telefondagi musiqa
    if re.search(r"telefondagi|yuklangan|o'zimdagi|offlayn|oflayn", text) and re.search(r"musiqa|qo'shiq|qo'shig'|muzika|ashula", text):
        query = strip_filler(re.sub(r"telefondagi|yuklangan|o'zimdagi|offlayn|oflayn", "", text))
        return phone.play_local_music(query)

    # Video
    if re.search(r"video|film|kino|multfilm|multik|klip|serial|ko'rsat|ko'raylik", text):
        query = strip_filler(text)
        if "multfilm" not in query and "multik" in text:
            query = (query + " multfilm").strip()
        if not query:
            query = "yangi o'zbek filmlari"
        if not phone.has_internet():
            return "Video uchun internet kerak. Internetni yoqib, qayta urinib ko'ring."
        return phone.play_video(query)

    # Musiqa
    if re.search(r"musiqa|qo'shiq|qo'shig'|muzika|ashula|eshittir|tingla", text):
        query = strip_filler(text)
        try:
            return phone.play_local_music(query) if query else phone.play_local_music()
        except phone.PhoneError:
            pass
        if not phone.has_internet():
            return "Internet yo'q va telefonda mos qo'shiq topilmadi."
        app = "spotify" if "spotify" in text else "youtube_music"
        return phone.play_music(query or "o'zbek qo'shiqlari", app)

    # Qidiruv
    m = re.match(r"^(qidir|google'da qidir|googleda qidir|izla|top)\s*:?\s*(.+)$", text) or \
        re.match(r"^(.+?)\s*(ni|haqida)?\s*(qidir|izla)$", text)
    if m:
        query = m.group(2) if m.re.pattern.startswith("^(qidir") else m.group(1)
        return phone.open_url("https://www.google.com/search?q=" + phone.urllib.parse.quote(query))

    # Sayt
    m = re.search(r"\b([a-z0-9-]+(\.[a-z0-9-]+)*\.(uz|com|ru|org|net|io|tv))\b", text)
    if m:
        return phone.open_url("https://" + m.group(1))

    # Ilovani ochish
    if re.search(r"\b(och|ochib|kir|ochgin|oching|kirgin|ishga tushir)\w*", text):
        app = _find_app(text)
        if app:
            return phone.open_app(app)
        name = strip_filler(re.sub(r"(ni|ga)?\s*(och|kir|ishga tushir)\w*", "", text))
        return phone.open_app(name) if name else "Qaysi ilovani ochay?"
    app = _find_app(text)
    if app:
        return phone.open_app(app)

    if re.fullmatch(r"(salom|assalomu alaykum|assalom|salom alaykum)\w*", text):
        return "Va alaykum assalom! Buyruq bering. Buyruqlar ro'yxati uchun: yordam"
    if re.search(r"rahmat|raxmat|tashakkur", text):
        return "Arzimaydi! 😊"

    return "Tushunmadim. 🤔 Buyruqlar ro'yxatini ko'rish uchun 'yordam' deb yozing."


def run_scheduled(task: str) -> str:
    """Rejalashtirilgan vazifani bajaradi."""
    if task == "uyg'otish":
        phone.notify("Turish vaqti bo'ldi! ☀️")
        try:
            phone.play_local_music()
        except phone.PhoneError:
            if phone.has_internet():
                phone.play_music("tetiklashtiruvchi o'zbek qo'shiqlari", "youtube_music")
        return "Xayrli tong! Turish vaqti bo'ldi ☀️"
    if task.startswith("eslatma: "):
        note = task.removeprefix("eslatma: ")
        phone.notify(note)
        return f"⏰ Eslatma: {note}"
    return handle(task)


def safe_handle(text: str) -> str:
    try:
        return handle(text)
    except (phone.PhoneError, ValueError) as exc:
        return str(exc)


def _fmt(value: str) -> str:
    try:
        f = float(value)
        return str(int(f)) if f.is_integer() and abs(f) < 1e15 else f"{f:.6g}"
    except ValueError:
        return value
