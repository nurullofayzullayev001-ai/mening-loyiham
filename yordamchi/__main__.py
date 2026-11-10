"""Terminal interfeysi: python -m yordamchi [--ovoz] [--no-web]"""

from __future__ import annotations

import argparse
import json
import threading

import anthropic

from . import phone
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
    args = parser.parse_args()

    agent = Agent(web_search=not args.no_web)
    lock = threading.Lock()

    def reply(answer: str) -> None:
        print(f"\nYordamchi: {answer}\n")
        if args.ovoz:
            phone.speak(answer)

    def run_scheduled(task: str) -> None:
        print(f"\n⏰ Vaqti keldi: {task}")
        with lock:
            bg = Agent(web_search=not args.no_web, exclude_tools=BACKGROUND_EXCLUDE)
            answer = safe_ask(bg, f"[Rejalashtirilgan vazifa, hozir bajaring] {task}")
        if answer:
            reply(answer)
        print("Siz: ", end="", flush=True)

    SCHEDULER.runner = run_scheduled

    if not phone.IS_TERMUX:
        print("ℹ️  Telefon topilmadi - havolalar kompyuter brauzerida ochiladi.")
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
        if args.ovoz and not text:
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
