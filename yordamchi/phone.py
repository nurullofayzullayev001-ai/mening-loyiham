"""Telefon (Android + Termux) bilan ishlash vositalari.

Telefonda Termux ichida ishga tushirilganda ilovalarni ochadi, video va
musiqani topib qo'yadi. Kompyuterda sinash uchun havolalar brauzerda ochiladi.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import webbrowser

IS_TERMUX = shutil.which("termux-open-url") is not None or shutil.which("am") is not None

# Mashhur ilovalar: nomi -> (paket nomi, ochish havolasi)
APPS: dict[str, tuple[str, str | None]] = {
    "youtube": ("com.google.android.youtube", "https://www.youtube.com"),
    "youtube music": ("com.google.android.apps.youtube.music", "https://music.youtube.com"),
    "telegram": ("org.telegram.messenger", "tg://resolve"),
    "instagram": ("com.instagram.android", "https://www.instagram.com"),
    "whatsapp": ("com.whatsapp", "whatsapp://send"),
    "tiktok": ("com.zhiliaoapp.musically", "https://www.tiktok.com"),
    "spotify": ("com.spotify.music", "spotify:"),
    "facebook": ("com.facebook.katana", "fb://feed"),
    "chrome": ("com.android.chrome", "https://www.google.com"),
    "google maps": ("com.google.android.apps.maps", "geo:0,0"),
    "xarita": ("com.google.android.apps.maps", "geo:0,0"),
    "gmail": ("com.google.android.gm", "mailto:"),
    "play market": ("com.android.vending", "market://search?q="),
    "kamera": ("", None),
    "sozlamalar": ("com.android.settings", None),
    "click": ("air.com.ssdsoftwaresolutions.clickuz", None),
    "payme": ("uz.dida.payme", None),
    "yandex go": ("ru.yandex.taxi", None),
}

_PKG_RE = re.compile(r"^[A-Za-z][\w]*(\.[A-Za-z_][\w]*)+$")


class PhoneError(Exception):
    pass


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise PhoneError(f"Buyruq topilmadi: {cmd[0]}. Termux:API o'rnatilganmi?") from exc
    except subprocess.TimeoutExpired as exc:
        raise PhoneError(f"Buyruq javob bermadi: {cmd[0]}") from exc


def _open_uri(uri: str) -> None:
    """Havolani telefonda tegishli ilovada (yoki kompyuterda brauzerda) ochadi."""
    if IS_TERMUX:
        if shutil.which("am"):
            r = _run(["am", "start", "-a", "android.intent.action.VIEW", "-d", uri])
            if r.returncode == 0 and "Error" not in r.stdout + r.stderr:
                return
        if shutil.which("termux-open-url"):
            r = _run(["termux-open-url", uri])
            if r.returncode == 0:
                return
        raise PhoneError(
            "Havolani ochib bo'lmadi. Termux'ga 'Boshqa ilovalar ustidan ko'rsatish' "
            "ruxsatini bering."
        )
    if not webbrowser.open(uri):
        raise PhoneError("Brauzerni ochib bo'lmadi.")


# ------------------------------------------------------------------- YouTube
def _youtube_search(query: str) -> tuple[str, str] | None:
    """YouTube'dan birinchi videoni topadi: (video_id, sarlavha) yoki None."""
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode(
        {"search_query": query, "hl": "uz"}
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "uz,ru,en"}
    )
    try:
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
    except Exception:
        return None
    m = re.search(
        r'"videoRenderer":\{"videoId":"([\w-]{11})".*?"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"',
        html,
    )
    if m:
        try:
            title = json.loads(f'"{m.group(2)}"')
        except ValueError:
            title = m.group(2)
        return m.group(1), title
    ids = re.findall(r'"videoId":"([\w-]{11})"', html)
    return (ids[0], query) if ids else None


def play_video(query: str) -> str:
    found = _youtube_search(query)
    if found:
        vid, title = found
        _open_uri(f"https://www.youtube.com/watch?v={vid}")
        return f"Video qo'yildi: \"{title}\" (https://youtu.be/{vid})"
    _open_uri("https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query}))
    return "Aniq video topilmadi, YouTube qidiruv natijalari ochildi."


def play_music(query: str, app: str = "youtube_music") -> str:
    if app == "spotify":
        _open_uri("spotify:search:" + urllib.parse.quote(query))
        return f"Spotify'da qidirildi: {query}"
    found = _youtube_search(query)
    if found:
        vid, title = found
        base = "https://music.youtube.com" if app == "youtube_music" else "https://www.youtube.com"
        _open_uri(f"{base}/watch?v={vid}")
        return f"Musiqa qo'yildi: \"{title}\""
    _open_uri("https://music.youtube.com/search?" + urllib.parse.urlencode({"q": query}))
    return "Aniq qo'shiq topilmadi, YouTube Music qidiruvi ochildi."


# ------------------------------------------------------------------ ilovalar
def open_app(name: str) -> str:
    key = name.strip().lower()
    package, uri = APPS.get(key, (key if _PKG_RE.match(key) else "", None))

    if key == "kamera" and IS_TERMUX:
        r = _run(["am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"])
        if r.returncode == 0:
            return "Kamera ochildi."

    if IS_TERMUX and package and shutil.which("monkey"):
        r = _run(["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
        if r.returncode == 0 and "No activities found" not in r.stdout + r.stderr:
            return f"{name} ochildi."
    if uri:
        _open_uri(uri)
        return f"{name} ochildi."
    if package:
        _open_uri(f"market://details?id={package}" if IS_TERMUX
                  else f"https://play.google.com/store/apps/details?id={package}")
        return f"{name} to'g'ridan-to'g'ri ochilmadi, Play Market sahifasi ochildi."
    raise PhoneError(
        f"'{name}' ilovasini tanimayman. list_apps bilan paket nomini toping "
        "va open_app ga paket nomini bering."
    )


def list_apps(filter: str = "") -> str:
    if not IS_TERMUX:
        return "Bu vosita faqat telefonda (Termux) ishlaydi. Ma'lum ilovalar: " + ", ".join(APPS)
    r = _run(["pm", "list", "packages", "-3"])
    if r.returncode != 0:
        return "Ilovalar ro'yxatini olib bo'lmadi. Ma'lum ilovalar: " + ", ".join(APPS)
    pkgs = sorted(line.removeprefix("package:") for line in r.stdout.splitlines())
    if filter:
        pkgs = [p for p in pkgs if filter.lower() in p.lower()]
    return "\n".join(pkgs[:200]) or "Mos ilova topilmadi."


def open_url(url: str) -> str:
    if not re.match(r"^(https?|tg|whatsapp|spotify|market|geo|tel|mailto|sms):", url):
        raise PhoneError("Faqat http(s), tg, whatsapp, spotify, market, geo, tel, mailto, sms havolalari.")
    _open_uri(url)
    return f"Ochildi: {url}"


def call_number(number: str) -> str:
    if not re.fullmatch(r"\+?[\d\s\-()]{3,20}", number):
        raise PhoneError("Telefon raqami noto'g'ri.")
    _open_uri("tel:" + re.sub(r"[\s\-()]", "", number))
    return "Qo'ng'iroq oynasi ochildi - 'Qo'ng'iroq' tugmasini o'zingiz bosing."


# ---------------------------------------------------------- ovoz (ixtiyoriy)
def speak(text: str) -> None:
    """Javobni ovoz chiqarib o'qiydi (Termux:API).

    Til YORDAMCHI_OVOZ_TILI muhit o'zgaruvchisidan olinadi (masalan uz, tr, ru);
    berilmasa telefonning standart ovozi ishlatiladi.
    """
    import os
    if not shutil.which("termux-tts-speak"):
        print("🔇 Ovoz uchun 'pkg install termux-api' va Termux:API ilovasi kerak.")
        return
    # Emoji va belgilarni olib tashlaymiz - ular o'qilmaydi yoki xalaqit beradi.
    clean = re.sub(r"[^\w\s.,!?:;'\"()+\-%/]", "", text).strip()
    if not clean:
        return
    cmd = ["termux-tts-speak"]
    lang = os.environ.get("YORDAMCHI_OVOZ_TILI", "").strip()
    if lang:
        cmd += ["-l", lang]
    cmd += ["-s", "MUSIC", clean]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or r.stderr.strip():
            print(f"🔇 Ovoz chiqmadi: {(r.stderr or r.stdout).strip()[:200]}")
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"🔇 Ovoz chiqmadi: {exc}")


def listen() -> str:
    if not shutil.which("termux-speech-to-text"):
        raise PhoneError("Ovozli kiritish uchun Termux:API kerak.")
    r = _run(["termux-speech-to-text"], timeout=60)
    # Oraliq natijalar ham chiqishi mumkin - oxirgi to'liq gapni olamiz.
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


# ------------------------------------------------- internet va mahalliy musiqa
def has_internet() -> bool:
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2).close()
        return True
    except OSError:
        return False


_MUSIC_EXT = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac", ".aac"}


def local_music() -> list:
    """Telefondagi qo'shiqlar (Music, Download papkalari)."""
    from pathlib import Path
    roots = [Path.home() / "storage" / d for d in ("music", "downloads", "shared/Music", "shared/Download")]
    roots.append(Path("/sdcard/Music"))
    found = {}
    for root in roots:
        if root.is_dir():
            try:
                for f in root.rglob("*"):
                    if f.suffix.lower() in _MUSIC_EXT and f.is_file():
                        found.setdefault(f.name, f)
            except OSError:
                continue
    return list(found.values())


def play_local_music(query: str = "") -> str:
    import random
    files = local_music()
    if not files:
        raise PhoneError(
            "Telefonda qo'shiq topilmadi. Termux'da 'termux-setup-storage' buyrug'ini "
            "bir marta bajaring va qo'shiqlar Music yoki Download papkasida bo'lsin."
        )
    if query:
        words = [w for w in query.lower().split() if len(w) > 1]
        scored = [(sum(w in f.stem.lower() for w in words), f) for f in files]
        best = max(s for s, _ in scored)
        if best == 0:
            raise PhoneError(f"Telefonda '{query}' nomli qo'shiq topilmadi.")
        files = [f for s, f in scored if s == best]
    song = random.choice(files)
    if shutil.which("termux-media-player"):
        _run(["termux-media-player", "play", str(song)])
    else:
        _open_uri(song.as_uri())
    return f"Qo'yildi: {song.stem}"


def stop_music() -> str:
    if shutil.which("termux-media-player"):
        _run(["termux-media-player", "stop"])
        return "Musiqa to'xtatildi."
    return "To'xtatish faqat telefondagi qo'shiqlar uchun ishlaydi."


def notify(text: str) -> None:
    if shutil.which("termux-notification"):
        try:
            _run(["termux-notification", "--title", "Yordamchi eslatmasi",
                  "--content", text, "--sound", "--vibrate", "500,300,500"])
        except PhoneError:
            pass
    if shutil.which("termux-vibrate"):
        try:
            _run(["termux-vibrate", "-d", "800"])
        except PhoneError:
            pass
