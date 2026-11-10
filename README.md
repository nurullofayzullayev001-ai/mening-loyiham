# 🤖 Yordamchi — AI agent

Claude (Anthropic) modeli asosida terminalda ishlaydigan umumiy AI yordamchi.
Agent o'zi qaror qilib vositalardan (tools) foydalanadi:

| Vosita | Vazifasi |
|---|---|
| `calculate` | Matematik ifodalarni aniq hisoblash (xavfsiz, `eval` ishlatilmaydi) |
| `current_time` | Istalgan vaqt mintaqasidagi sana/vaqt |
| `list_files`, `read_file` | `ishchi_papka/` dagi fayllarni ko'rish va o'qish |
| `write_file` | Fayl yozish — **har safar sizdan ruxsat so'raydi** |
| `web_search` | Internetdan qidirish (Anthropic serverida ishlaydi) |

## O'rnatish

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

API kalitni [platform.claude.com](https://platform.claude.com) dan oling va o'rnating:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

## Ishga tushirish

```bash
python -m yordamchi            # veb-qidiruv bilan
python -m yordamchi --no-web   # veb-qidiruvsiz
```

Buyruqlar: `yangi` — yangi suhbat, `chiqish` — dasturdan chiqish.

Misol savollar:

- `125 ning kvadrat ildizini 3 ga ko'paytir`
- `Toshkentda hozir soat necha?`
- `Bugungi dollar kursini top`
- `Menga xarid ro'yxatini yozib, xarid.txt fayliga saqla`

## Qanday ishlaydi

`yordamchi/agent.py` dagi sikl:

1. Sizning xabaringiz suhbat tarixiga qo'shiladi va Claude'ga yuboriladi.
2. Agar Claude vosita chaqirsa (`stop_reason == "tool_use"`), vosita bajariladi va
   natija qaytarib yuboriladi.
3. Claude yakuniy javob berguncha takrorlanadi (eng ko'pi 20 qadam).

Model: `claude-opus-5-5`, adaptive thinking, `effort: medium`, prompt keshlash
yoqilgan. Model so'rovni rad etsa, server avtomatik zaxira modelga o'tadi
(`fallbacks: "default"`).

## Yangi vosita qo'shish

`yordamchi/tools.py` da:

1. Funksiya yozing (natijani `str` qaytarsin, xatoda `ToolError` ko'taring).
2. `TOOLS` ro'yxatiga uning nomi, tavsifi va `input_schema` sini qo'shing.
3. `HANDLERS` lug'atiga nom → funksiya juftligini qo'shing.
