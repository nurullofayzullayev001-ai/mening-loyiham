"""Yordamchi agentning asosiy sikli (agentic loop)."""

from __future__ import annotations

from typing import Any

import anthropic

from .tools import TOOLS, WEB_SEARCH_TOOL, run_tool

MODEL = "claude-opus-5-5"
MAX_STEPS = 20  # bitta savol uchun model chaqiruvlari chegarasi

SYSTEM_PROMPT = """\
Siz "Yordamchi" - foydalanuvchining telefonidagi shaxsiy AI yordamchisiz.

- Har doim o'zbek tilida (lotin yozuvida) gapiring, foydalanuvchi boshqa tilni \
so'ramaguncha. Samimiy va hurmat bilan "siz" deb murojaat qiling.
- Foydalanuvchi buyurgan ishni gapirib o'tirmasdan darhol vositalar bilan bajaring: \
video ko'rmoqchi bo'lsa `play_video`, musiqa/qo'shiq so'rasa `play_music`, ilova \
ochishni so'rasa `open_app`. Qo'shiqchi yoki film nomini kerak bo'lsa to'g'ri \
yozilishiga keltirib qidiring.
- "Soat 7 da", "20 daqiqadan keyin", "ertaga ertalab" kabi vaqt aytilsa, \
`schedule_task` bilan rejalashtiring (kerak bo'lsa avval `current_time` ni bilib oling).
- Ishni bajargach, nima qilganingizni bir-ikki gapda ayting.
- Pul o'tkazish, xabar yuborish, qo'ng'iroqni yakuniy tasdiqlash kabi ishlarni \
foydalanuvchining o'zi bajaradi - siz faqat kerakli oyna yoki ilovani ochasiz.
- Hisob-kitoblar uchun `calculate`, sana/vaqt uchun `current_time` vositasidan \
foydalaning - taxmin qilmang.
- Yangi yoki tez o'zgaruvchan ma'lumotlar (yangiliklar, narxlar, ob-havo) uchun \
`web_search` dan foydalaning va manbani ko'rsating.
- Fayllar faqat ishchi papkada; yozishdan oldin foydalanuvchi ruxsat beradi. \
Agar ruxsat berilmasa, buni hurmat qiling.
- Javoblar aniq va qisqa bo'lsin; kerak bo'lsagina ro'yxat ishlating.
"""


class Agent:
    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        *,
        web_search: bool = True,
        exclude_tools: tuple[str, ...] = (),
    ):
        self.client = client or anthropic.Anthropic()
        self.messages: list[Any] = []  # suhbat tarixi - faqat oxiriga qo'shiladi
        self.tools: list[dict[str, Any]] = [t for t in TOOLS if t["name"] not in exclude_tools]
        if web_search:
            self.tools.append(WEB_SEARCH_TOOL)

    def _call(self):
        return self.client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=self.tools,
            messages=self.messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            cache_control={"type": "ephemeral"},  # tarixni keshlab, narxni kamaytiradi
            # Model so'rovni rad etsa, server avtomatik zaxira modelga o'tadi.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    def ask(self, user_text: str, on_tool=None) -> str:
        """Foydalanuvchi xabariga javob beradi, kerak bo'lsa vositalarni chaqiradi."""
        start = len(self.messages)
        self.messages.append({"role": "user", "content": user_text})
        try:
            return self._loop(start, on_tool)
        except BaseException:
            # Xato bo'lsa, tugallanmagan navbatni olib tashlab, oldingi suhbatni saqlaymiz.
            del self.messages[start:]
            raise

    def _loop(self, start: int, on_tool) -> str:
        for _ in range(MAX_STEPS):
            response = self._call()

            if response.stop_reason == "refusal":
                # Rad etilgan navbatni tarixdan olib tashlaymiz (faqat oxiri).
                del self.messages[start:]
                return "Kechirasiz, bu so'rovga javob bera olmayman."

            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                continue  # server vositasi davom etmoqda

            if response.stop_reason != "tool_use":
                text = _text_of(response.content)
                if response.stop_reason == "max_tokens":
                    text += "\n\n[Javob uzunlik chegarasiga yetib kesildi.]"
                return text

            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if on_tool:
                    on_tool(block.name, block.input)
                output, is_error = run_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                })
            # Barcha natijalar bitta xabarda qaytariladi.
            self.messages.append({"role": "user", "content": results})

        return "[Qadamlar chegarasiga yetildi - vazifani kichikroq qismlarga bo'lib bering.]"

    def reset(self) -> None:
        self.messages.clear()


def _text_of(content) -> str:
    return "\n".join(b.text for b in content if b.type == "text").strip()
