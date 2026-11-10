# 🤖 Yordamchi — telefoningizdagi AI agent

O'zbek tilida gapiradigan AI yordamchi (Claude modeli asosida). Siz buyruq berasiz,
u bajaradi:

- 🎬 **Video qo'yadi** — "Mehribon film qo'y", "bolalar uchun multfilm"
- 🎵 **Musiqa qo'yadi** — "Sevara Nazarxonning qo'shig'ini qo'y" (YouTube Music / Spotify)
- 📱 **Ilovalarni ochadi** — Telegram, Instagram, YouTube, WhatsApp, TikTok, Click, Payme, kamera...
- ⏰ **Aytilgan vaqtda bajaradi** — "Ertalab 7:00 da musiqa qo'y", "20 daqiqadan keyin eslat"
- 🔎 **Internetdan topadi** — yangiliklar, kurslar, ob-havo, ma'lumotlar
- 📞 Qo'ng'iroq oynasini ochadi, 🧮 hisoblaydi, 🕐 vaqtni aytadi, 📄 fayllar bilan ishlaydi
- 🎤 **Ovozli rejim** — gapirib buyruq berasiz, u ovoz chiqarib javob beradi

> Xavfsizlik uchun pul o'tkazish, xabar yuborish va qo'ng'iroqni yakuniy tasdiqlashni
> agent qilmaydi — kerakli oynani ochadi, tugmani o'zingiz bosasiz.

## 🆓 Bepul rejim (API kalitsiz)

API kalit bo'lmasa, Yordamchi avtomatik **bepul rejimda** ishlaydi. Bu rejimda AI yo'q:
buyruqlarni so'z-qoliplar orqali tushunadi, shuning uchun aniqroq gapiring.

| Buyruq misoli | Internet kerakmi? |
|---|---|
| `Telegramni och`, `kamerani och`, `YouTube'ni och` | Yo'q |
| `telefondagi musiqani qo'y`, `musiqani to'xtat` | Yo'q |
| `soat nechi`, `bugun nechanchi sana`, `hisobla 125*4` | Yo'q |
| `20 daqiqadan keyin choyni eslat`, `ertaga 6:30 da uyg'ot`, `rejalar` | Yo'q |
| `Sevara Nazarxon qo'shig'ini qo'y` | Ha (YouTube Music) |
| `O'tkan kunlar filmini qo'y`, `multfilm qo'y` | Ha (YouTube) |
| `qidir: Toshkent ob-havosi`, `kun.uz ni och` | Ha |

Barcha buyruqlar ro'yxati uchun `yordam` deb yozing.

Telefondagi qo'shiqlarni qo'yish uchun Termux'da bir marta yozing va ruxsat bering:

```bash
termux-setup-storage
```

## 📱 Android telefonga o'rnatish

1. **F-Droid** (f-droid.org) orqali ikkita ilova o'rnating: **Termux** va **Termux:API**.
   (Play Market'dagi Termux eskirgan — F-Droid'dan oling.)
2. Telefon sozlamalarida: *Ilovalar → Termux → Boshqa ilovalar ustidan ko'rsatish* →
   **ruxsat bering** (aks holda Termux ilovalarni ocha olmaydi).
   Ovozli rejim uchun *Termux:API* ga **mikrofon** ruxsatini ham bering.
3. Termux'ni ochib, quyidagilarni yozing:

```bash
pkg update -y
pkg install -y python git termux-api rust binutils
git clone -b claude/yordamchi-oohthg https://github.com/nurullofayzullayev001-ai/mening-loyiham.git
cd mening-loyiham
pip install -r requirements.txt
```

4. *(Ixtiyoriy — bepul rejim uchun kerak emas)* API kalitni [platform.claude.com](https://platform.claude.com) saytidan oling va saqlang:

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc
```

## ▶️ Ishga tushirish

```bash
cd mening-loyiham
python -m yordamchi          # yozib buyruq berish (kalit bo'lmasa - bepul rejim)
python -m yordamchi --bepul  # kalit bo'lsa ham bepul rejim
python -m yordamchi --ovoz   # ovozli: Enter bosing va gapiring
```

Buyruqlar: `yangi` — yangi suhbat, `chiqish` — chiqish.

Misollar:

```
Siz: YouTube'da "O'tkan kunlar" filmini qo'y
Siz: Ozodbek Nazarbekovning qo'shig'ini qo'y
Siz: Telegramni och
Siz: Ertaga soat 6:30 da meni uyg'otish uchun tetiklashtiruvchi musiqa qo'y
Siz: Bugun Toshkentda ob-havo qanday?
```

⏰ Rejalashtirilgan vazifalar dastur **ochiq turganda** bajariladi. Termux fonda
uxlab qolmasligi uchun bildirishnomadagi **"Acquire wakelock"** tugmasini bosing.

## 💻 Kompyuterda sinab ko'rish

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python -m yordamchi
```

Kompyuterda video va musiqa brauzerda ochiladi; ilovalar faqat telefonda ochiladi.

## ⚠️ Cheklovlar

- **iPhone** qo'llab-quvvatlanmaydi — iOS tashqi dasturlarga ilovalarni boshqarishga ruxsat bermaydi.
- Agent ilova **ichida** tugma bosa olmaydi (masalan, Telegram'da kimgadir yozish) — u ilovani
  yoki kerakli sahifani ochib beradi.
- Ovozli javob telefoningizda o'zbekcha ovoz (TTS) o'rnatilgan bo'lsa o'zbekcha eshitiladi.

## 🛠 Tuzilishi

| Fayl | Vazifasi |
|---|---|
| `yordamchi/agent.py` | Agent sikli: Claude vositani chaqiradi → natija qaytariladi → yakuniy javob |
| `yordamchi/phone.py` | Telefon vositalari: video, musiqa, ilovalar, havolalar, ovoz |
| `yordamchi/bepul.py` | Bepul rejim: API'siz buyruqlarni tushunish |
| `yordamchi/scheduler.py` | Vaqtga rejalashtirish |
| `yordamchi/tools.py` | Barcha vositalar ro'yxati va kalkulyator, vaqt, fayllar |
| `yordamchi/__main__.py` | Terminal interfeysi |

Yangi ilova qo'shish: `phone.py` dagi `APPS` lug'atiga `"nomi": ("paket.nomi", None)` yozing.
