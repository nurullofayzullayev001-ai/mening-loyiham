"""Terminal interfeysi: python -m yordamchi"""

import argparse
import json

import anthropic

from .agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Yordamchi - AI agent")
    parser.add_argument("--no-web", action="store_true", help="veb-qidiruvni o'chirish")
    args = parser.parse_args()

    agent = Agent(web_search=not args.no_web)
    print("🤖 Yordamchi tayyor! Chiqish: 'chiqish', yangi suhbat: 'yangi'.\n")

    def show_tool(name, tool_input):
        print(f"   🔧 {name}({json.dumps(tool_input, ensure_ascii=False)[:120]})")

    while True:
        try:
            text = input("Siz: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nXayr!")
            break
        if not text:
            continue
        if text.lower() in ("chiqish", "exit", "quit"):
            print("Xayr!")
            break
        if text.lower() in ("yangi", "reset"):
            agent.reset()
            print("Yangi suhbat boshlandi.\n")
            continue

        try:
            answer = agent.ask(text, on_tool=show_tool)
        except anthropic.AuthenticationError:
            print("❌ API kalit noto'g'ri yoki o'rnatilmagan (ANTHROPIC_API_KEY).")
            break
        except anthropic.RateLimitError:
            print("⏳ So'rovlar chegarasi. Birozdan keyin qayta urinib ko'ring.\n")
            continue
        except anthropic.APIStatusError as exc:
            print(f"❌ API xatosi ({exc.status_code}): {exc.message}\n")
            continue
        except anthropic.APIConnectionError:
            print("🌐 Internetga ulanib bo'lmadi.\n")
            continue

        print(f"\nYordamchi: {answer}\n")


if __name__ == "__main__":
    main()
