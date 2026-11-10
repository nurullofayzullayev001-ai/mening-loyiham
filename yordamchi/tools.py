"""Agent foydalanadigan vositalar (tools).

Har bir vosita: API uchun JSON sxema + uni bajaradigan Python funksiyasi.
"""

from __future__ import annotations

import ast
import math
import operator
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Agent faqat shu papka ichidagi fayllar bilan ishlaydi.
WORKSPACE = Path(__file__).resolve().parent.parent / "ishchi_papka"
MAX_READ_CHARS = 100_000


class ToolError(Exception):
    """Vosita xatosi - modelga is_error=True bilan qaytariladi."""


# ---------------------------------------------------------------- kalkulyator
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS: dict[str, Callable[..., float]] = {
    name: getattr(math, name)
    for name in (
        "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10",
        "log2", "exp", "floor", "ceil", "factorial", "radians", "degrees",
    )
}
_FUNCS.update({"abs": abs, "round": round})
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ToolError("Daraja ko'rsatkichi juda katta.")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and not node.keywords
    ):
        return _FUNCS[node.func.id](*(_eval_node(a) for a in node.args))
    raise ToolError(f"Ruxsat etilmagan ifoda: {ast.dump(node)[:80]}")


def calculate(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_eval_node(tree.body))
    except ToolError:
        raise
    except Exception as exc:  # SyntaxError, ZeroDivisionError, ValueError...
        raise ToolError(f"Hisoblab bo'lmadi: {exc}") from exc


# ---------------------------------------------------------------------- vaqt
def current_time(timezone: str = "Asia/Tashkent") -> str:
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError as exc:
        raise ToolError(f"Noma'lum vaqt mintaqasi: {timezone}") from exc
    return now.strftime("%Y-%m-%d %H:%M:%S %Z (%A)")


# ------------------------------------------------------------------- fayllar
def _safe_path(relative: str) -> Path:
    WORKSPACE.mkdir(exist_ok=True)
    path = (WORKSPACE / relative).resolve()
    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ToolError("Faqat ishchi_papka ichidagi fayllarga ruxsat bor.")
    return path


def list_files(directory: str = ".") -> str:
    path = _safe_path(directory)
    if not path.is_dir():
        raise ToolError(f"Papka topilmadi: {directory}")
    items = sorted(
        f"{p.relative_to(WORKSPACE)}{'/' if p.is_dir() else ''}"
        for p in path.iterdir()
    )
    return "\n".join(items) if items else "(papka bo'sh)"


def read_file(path: str) -> str:
    file = _safe_path(path)
    if not file.is_file():
        raise ToolError(f"Fayl topilmadi: {path}")
    text = file.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        raise ToolError(
            f"Fayl juda katta ({len(text)} belgi, chegara {MAX_READ_CHARS})."
        )
    return text


def write_file(path: str, content: str) -> str:
    file = _safe_path(path)
    print(f"\n⚠️  Agent '{file.relative_to(WORKSPACE)}' fayliga "
          f"{len(content)} belgi yozmoqchi.")
    answer = input("Ruxsat berasizmi? [h/Y] (h = ha): ").strip().lower()
    if answer not in ("h", "ha", "y", "yes"):
        return "Foydalanuvchi fayl yozishga ruxsat bermadi."
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    return f"Yozildi: {file.relative_to(WORKSPACE)} ({len(content)} belgi)"


# ------------------------------------------------------------ ro'yxatga olish
def _schema(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


TOOLS: list[dict[str, Any]] = [
    {
        "name": "calculate",
        "description": (
            "Matematik ifodani aniq hisoblaydi. + - * / // % ** amallari, "
            "sqrt, sin, cos, log, exp, factorial, abs, round funksiyalari va "
            "pi, e konstantalari qo'llab-quvvatlanadi. Har qanday hisob-kitob "
            "uchun taxmin qilish o'rniga shu vositadan foydalaning."
        ),
        "input_schema": _schema(
            {"expression": {"type": "string", "description": "Masalan: 2**10 + sqrt(16)"}},
            ["expression"],
        ),
        "strict": True,
    },
    {
        "name": "current_time",
        "description": "Berilgan vaqt mintaqasidagi hozirgi sana va vaqtni qaytaradi.",
        "input_schema": _schema(
            {"timezone": {"type": "string", "description": "IANA nomi, masalan Asia/Tashkent"}},
            ["timezone"],
        ),
        "strict": True,
    },
    {
        "name": "list_files",
        "description": "Ishchi papkadagi fayl va papkalar ro'yxatini ko'rsatadi.",
        "input_schema": _schema(
            {"directory": {"type": "string", "description": "Nisbiy yo'l; ildiz uchun '.'"}},
            ["directory"],
        ),
        "strict": True,
    },
    {
        "name": "read_file",
        "description": "Ishchi papkadagi matnli faylni o'qiydi.",
        "input_schema": _schema(
            {"path": {"type": "string", "description": "Nisbiy fayl yo'li"}},
            ["path"],
        ),
        "strict": True,
    },
    {
        "name": "write_file",
        "description": (
            "Ishchi papkaga faylni yozadi (mavjud bo'lsa, ustidan yozadi). "
            "Bajarishdan oldin foydalanuvchidan ruxsat so'raladi."
        ),
        "input_schema": _schema(
            {
                "path": {"type": "string", "description": "Nisbiy fayl yo'li"},
                "content": {"type": "string", "description": "Faylning to'liq matni"},
            },
            ["path", "content"],
        ),
        "strict": True,
    },
]

HANDLERS: dict[str, Callable[..., str]] = {
    "calculate": calculate,
    "current_time": current_time,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
}

# Anthropic serverida ishlaydigan veb-qidiruv (bizda kod kerak emas).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


def run_tool(name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
    """Vositani bajaradi. (natija, xatomi) qaytaradi."""
    handler = HANDLERS.get(name)
    if handler is None:
        return f"Noma'lum vosita: {name}", True
    try:
        return handler(**tool_input), False
    except ToolError as exc:
        return str(exc), True
    except TypeError as exc:  # noto'g'ri argumentlar
        return f"Noto'g'ri argumentlar: {exc}", True
