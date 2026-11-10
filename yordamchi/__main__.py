"""Terminal interfeysi: python -m yordamchi [--ovoz] [--no-web]"""

from __future__ import annotations

import argparse
import json
import os
import threading

import anthropic

from . import bepul, phone
from .agent import Agent
from .scheduler import SCHEDULER

# Rejalashtirilgan vazifalar fonda bajariladi - ular fayl yozmaydi va yangi
# vazifa rejalashtirmaydi (sizdan ruxsat so'rab, terminalni chalkashtirmasligi uchun).
BACKGROUND_EXCLUDE = ("write_file", "schedule_task", "cancel_scheduled")


def show_tool(name, tool_input):
    print(f"   🔧 {name}({json.dumps(tool_input, ensure_ascii=False)[:120]})")


def safe_ask(agent: Agent, text: str) -> str | None:
    try:
        return agent.ask(text, on_tool=show_tool)
    except anthropic.AuthenticationError:
        print("❌ API kalit noto'g'ri yoki o'rnatilmagan (ANTHROPIC_API_KEY).")
        raise SystemExit(1)
    except anthropic.RateLimitError:
        print("⏳ So'rovlar chegarasi. Birozdan keyin qayta urinib ko'ring.\n")
    except anthropic.APIStatusError as exc:
        print(f"❌ API xatosi ({exc.status_code}): {exc.message}\n")
    except anthropic.APIConnectionError:
        print("🌐 Internetga ulanib bo'lmadi.\n")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Yordamchi - telefoningizdagi AI agent")
    parser.add_argument("--ovoz", action="store_true", help="ovozli rejim (Termux:API kerak)")
    parser.add_argument("--no-web", action="store_true", help="veb-qidiruvni o'chirish")
    parser.add_argument("--bepul", action="store_true", help="API kalitsiz bepul rejim")
    args = parser.parse_args()

    has_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    free = args.bepul or not has_key
    agent = None if free else Agent(web_search=not args.no_web)
    lock = threading.Lock()
    voice = {"on": args.ovoz}

    def reply(answer: str) -> None:
        print(f"\nYordamchi: {answer}\n")
        if voice["on"]:
            phone.speak(answer)

    def run_scheduled(task: str) -> None:
        print(f"\n⏰ Vaqti keldi: {task}")
        with lock:
            if free:
                try:
                    answer = bepul.run_scheduled(task)
                except (phone.PhoneError, ValueError) as exc:
                    answer = str(exc)
            else:
                bg = Agent(web_search=not args.no_web, exclude_tools=BACKGROUND_EXCLUDE)
                answer = safe_ask(bg, f"[Rejalashtirilgan vazifa, hozir bajaring] {task}")
        if answer:
            reply(answer)
        print("Siz: ", end="", flush=True)

    SCHEDULER.runner = run_scheduled

    if not phone.IS_TERMUX:
        print("ℹ️  Telefon topilmadi - havolalar kompyuter brauzerida ochiladi.")
    if free:
        print("🆓 Bepul rejim (AI'siz). Buyruqlar ro'yxati: 'yordam'. Chiqish: 'chiqish'.")
    else:
        print("🤖 Yordamchi tayyor! Buyruq bering. 'yangi' - yangi suhbat, 'chiqish' - chiqish.")
    if args.ovoz:
        print("🎤 Ovozli rejim: Enter bosing va gapiring (yoki yozing).")
    print()

    while True:
        try:
            text = input("Siz: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nXayr!")
            break
        low = text.lower().replace("‘", "'").replace("ʻ", "'").replace("’", "'")
        if low in ("ovozni yoq", "ovoz yoq", "gapir", "ovozli rejim"):
            voice["on"] = True
            reply("Ovoz yoqildi. Endi javoblarni ovoz chiqarib aytaman. "
                  "Gapirish uchun bo'sh holda Enter bosing.")
            continue
        if low in ("ovozni o'chir", "ovoz o'chir", "jim"):
            voice["on"] = False
            print("\nYordamchi: Ovoz o'chirildi.\n")
            continue
        if low in ("ovozni tekshir", "ovoz tekshir", "o'qib ber", "eshityapsanmi"):
            print("\nYordamchi: Salom! Meni eshityapsizmi?\n")
            phone.speak("Salom! Meni eshityapsizmi?")
            continue
        if voice["on"] and not text:
            try:
                text = phone.listen()
            except phone.PhoneError as exc:
                print(f"🎤 {exc}")
                continue
            if text:
                print(f"Siz (ovoz): {text}")
        if not text:
            continue
        if text.lower() in ("chiqish", "exit", "quit"):
            print("Xayr!")
            break
        if free:
            with lock:
                answer = bepul.safe_handle(text)
            reply(answer)
            continue
        if text.lower() in ("yangi", "reset"):
            agent.reset()
            print("Yangi suhbat boshlandi.\n")
            continue

        with lock:
            answer = safe_ask(agent, text)
        if answer:
            reply(answer)


if __name__ == "__main__":
    main()
