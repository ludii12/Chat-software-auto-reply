import json
import base64
import ctypes
import hashlib
import io
import queue
import random
import re
import subprocess
import sys
import threading
import time
import tempfile
import tkinter as tk
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog, ttk

try:
    from PIL import Image, ImageGrab, ImageTk
    import pyperclip
    import win32api
    import win32con
    from pywinauto import Desktop
    from pywinauto.keyboard import send_keys
except ImportError:
    Image = None
    ImageGrab = None
    ImageTk = None
    pyperclip = None
    win32api = None
    win32con = None
    Desktop = None
    send_keys = None


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
RULES_FILE = APP_DIR / "rules.json"
CONFIG_FILE = APP_DIR / "agnes_config.json"
SKILLS_DIR = APP_DIR / "skills"
ASSETS_DIR = APP_DIR / "assets"
LOGO_FILE = ASSETS_DIR / "app_logo.png"
MEMORY_FILE = APP_DIR / "chat_memory.json"
CONTACTS_FILE = APP_DIR / "contacts.json"
THEME_FILE = APP_DIR / "theme.json"
LOG_FILE = APP_DIR / "wechat_auto_reply.log"
PROMISES_FILE = APP_DIR / "promises.json"
DEBUG_DIR = APP_DIR / "debug"
MAX_SKILL_CHARS = 6000
VISION_INTERVAL_SECONDS = 5
LOCAL_SCREENSHOT_POLL_SECONDS = 1.2
INCOMING_IMAGE_DIFF_THRESHOLD = 5.0
SELF_SEND_GRACE_SECONDS = 2.5
REPLY_DELAY_MIN_SECONDS = 5
REPLY_DELAY_MAX_SECONDS = 10
WECHAT_TITLE_RE = re.compile(r".*(微信|WeChat).*", re.IGNORECASE)
NOISE_RE = re.compile(
    r"^(发送|表情|聊天信息|更多|语音聊天|视频聊天|搜索|通讯录|收藏|文件传输助手|WeChat|微信)$"
)
TIME_RE = re.compile(r"^(\d{1,2}:\d{2}|昨天|星期.|周.|20\d{2}[/.-]\d{1,2}[/.-]\d{1,2})")



FONT_FAMILY = "Microsoft YaHei UI"
FONT_SIZE_BASE = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_TITLE = 18
FONT_SIZE_CARD_TITLE = 13
FONT_SIZE_NAV = 10

BG_MAIN = "#f2f3f5"
BG_WHITE = "#ffffff"
BG_SIDEBAR = "#ffffff"
BG_TEXT_AREA = "#f5f6f7"
BORDER_CARD = "#e5e6eb"
BORDER_INPUT = "#dcdfe6"
BORDER_INPUT_FOCUS = "#1E90FF"
HOVER_LIGHT = "#f2f3f5"
BTN_SECONDARY_BG = "#f2f3f5"
BTN_SECONDARY_HOVER = "#e8eaed"
BTN_SECONDARY_PRESS = "#dcdfe6"
TEXT_PRIMARY = "#1d2129"
TEXT_SECONDARY = "#4e5969"
TEXT_MUTED = "#86909c"
SIDEBAR_WIDTH = 200
TOAST_SUCCESS = "#00b42a"
TOAST_ERROR = "#f53f3f"
TOAST_WARNING = "#ff7d00"


def draw_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, btn_type="primary", width=None, height=40, radius=8, font_size=10, **kwargs):
        super().__init__(parent, highlightthickness=0, bd=0, bg=parent.cget("bg"), **kwargs)
        self.text = text
        self.command = command
        self.btn_type = btn_type
        self.radius = radius
        self.btn_height = height
        self.btn_width = width
        self.font_size = font_size
        self._hover = False
        self._press = False
        self.accent = "#1E90FF"
        self.accent_hot = "#1875CC"
        self.accent_press = "#125999"
        self._fixed_width = width is not None
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self["cursor"] = "hand2"
        if self._fixed_width:
            self["width"] = width
            self["height"] = height
        self.bind("<Configure>", self._on_configure)
        self.after(10, self._initial_draw)

    def _initial_draw(self):
        if not self._fixed_width:
            self.update_idletasks()
            w = self._measure_text_width() + 40
            h = self.btn_height
            self["width"] = w
            self["height"] = h
            self.btn_width = w
        self._draw()

    def _measure_text_width(self):
        font = (FONT_FAMILY, self.font_size)
        temp = self.tk
        from tkinter import font as tkfont
        f = tkfont.Font(family=FONT_FAMILY, size=self.font_size)
        return f.measure(self.text)

    def set_accent(self, accent, accent_hot, accent_press):
        self.accent = accent
        self.accent_hot = accent_hot
        self.accent_press = accent_press
        self._draw()

    def _on_configure(self, event):
        if not self._fixed_width and event.width > 10:
            self.btn_width = event.width
        self._draw()

    def _on_enter(self, event):
        self._hover = True
        self._draw()

    def _on_leave(self, event):
        self._hover = False
        self._press = False
        self._draw()

    def _on_press(self, event):
        self._press = True
        self._draw()

    def _on_release(self, event):
        self._press = False
        self._draw()
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        w = self.btn_width or self.winfo_width()
        h = self.btn_height
        if w < 20 or h < 10:
            w = max(w, 60)
            self["width"] = w
        if self.btn_type == "primary":
            if self._press:
                bg = self.accent_press
            elif self._hover:
                bg = self.accent_hot
            else:
                bg = self.accent
            fg = "#ffffff"
        elif self.btn_type == "danger":
            if self._press:
                bg = "#c92d30"
            elif self._hover:
                bg = "#e5484d"
            else:
                bg = "#f53f3f"
            fg = "#ffffff"
        elif self.btn_type == "ghost":
            if self._press:
                bg = "#e8eaed"
            elif self._hover:
                bg = "#f2f3f5"
            else:
                bg = "transparent"
            fg = TEXT_SECONDARY
        else:
            if self._press:
                bg = BTN_SECONDARY_PRESS
            elif self._hover:
                bg = BTN_SECONDARY_HOVER
            else:
                bg = BTN_SECONDARY_BG
            fg = TEXT_PRIMARY
        if bg != "transparent":
            draw_rounded_rect(self, 1, 1, w - 1, h - 1, self.radius, fill=bg, outline="")
        self.create_text(w // 2, h // 2, text=self.text, fill=fg, font=(FONT_FAMILY, self.font_size))


class Card(tk.Frame):
    """简约卡片：边框色外层 + 白色内层，1px 边框，干净可靠。"""
    def __init__(self, parent, padding=24, **kwargs):
        super().__init__(parent, bg=BORDER_CARD, **kwargs)
        white = tk.Frame(self, bg=BG_WHITE)
        white.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        if padding:
            self.body = tk.Frame(white, bg=BG_WHITE)
            self.body.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)
        else:
            self.body = white


class ModernEntry(tk.Frame):
    """圆角输入框：边框色Frame包裹tk.Entry，聚焦变色。"""
    def __init__(self, parent, textvariable=None, show=None, width=None, font_size=10, **kwargs):
        super().__init__(parent, bg=BORDER_INPUT, **kwargs)
        self._focused = False
        self.accent = BORDER_INPUT_FOCUS
        entry_bg = BG_WHITE
        self.entry = tk.Entry(
            self, textvariable=textvariable, show=show,
            bd=0, bg=entry_bg, fg=TEXT_PRIMARY, insertbackground="#1E90FF",
            font=(FONT_FAMILY, font_size), relief=tk.FLAT, highlightthickness=0
        )
        if width:
            self.entry["width"] = width
        self.entry.pack(fill=tk.BOTH, expand=True, padx=1, pady=1, ipady=9)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.configure(bg=BORDER_INPUT)
        self._update_bg()

    def set_accent(self, accent):
        self.accent = accent
        self.entry.configure(insertbackground=accent)
        self._update_bg()

    def _on_focus_in(self, event):
        self._focused = True
        self._update_bg()

    def _on_focus_out(self, event):
        self._focused = False
        self._update_bg()

    def _update_bg(self):
        color = self.accent if self._focused else BORDER_INPUT
        self.configure(bg=color)


class ModernCombobox(ttk.Combobox):
    """使用原生ttk.Combobox，可靠兼容Windows。"""
    def __init__(self, parent, textvariable=None, values=None, state="readonly", width=None, font_size=10, **kwargs):
        kw = {}
        if textvariable:
            kw["textvariable"] = textvariable
        if values:
            kw["values"] = values
        kw["state"] = state
        if width:
            kw["width"] = width
        super().__init__(parent, **kw)
        self._values = values or []

    def configure_values(self, values):
        self._values = values or []
        self.configure(values=self._values)

    def set_accent(self, accent):
        pass


class ModernDialog(tk.Toplevel):
    def __init__(self, parent, title, message, buttons=None, input_prompt=None, initialvalue=None, width=420):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_WHITE)
        self.resizable(False, False)
        self._parent = parent
        self.result = None
        self._input_var = tk.StringVar(value=initialvalue or "")
        self._build(title, message, buttons, input_prompt, width)
        self.center_on_parent()
        self.transient(parent)
        self.grab_set()
        self.focus_set()

    def _build(self, title, message, buttons, input_prompt, width):
        outer = tk.Frame(self, bg=BORDER_CARD)
        outer.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        frame = tk.Frame(outer, bg=BG_WHITE)
        frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        content = tk.Frame(frame, bg=BG_WHITE)
        content.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        title_bar = tk.Frame(content, bg=BG_WHITE)
        title_bar.pack(fill=tk.X, pady=(0, 16))
        tk.Label(
            title_bar, text=title, bg=BG_WHITE, fg=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13, "bold"), anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        close_lbl = tk.Label(title_bar, text="✕", bg=BG_WHITE, fg=TEXT_MUTED,
                              font=(FONT_FAMILY, 11), cursor="hand2", padx=4)
        close_lbl.pack(side=tk.RIGHT)
        close_lbl.bind("<Button-1>", lambda e: self._on_cancel())
        close_lbl.bind("<Enter>", lambda e: close_lbl.configure(fg=TEXT_PRIMARY))
        close_lbl.bind("<Leave>", lambda e: close_lbl.configure(fg=TEXT_MUTED))
        for w in (title_bar,):
            for child in w.winfo_children():
                if child != close_lbl:
                    child.bind("<ButtonPress-1>", self._start_drag)
                    child.bind("<B1-Motion>", self._on_drag)
        title_bar.bind("<ButtonPress-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._on_drag)

        if message:
            tk.Label(
                content, text=message, bg=BG_WHITE, fg=TEXT_SECONDARY,
                font=(FONT_FAMILY, 10), wraplength=width - 80, justify=tk.LEFT
            ).pack(fill=tk.X, pady=(0, 8))
        if input_prompt:
            tk.Label(
                content, text=input_prompt, bg=BG_WHITE, fg=TEXT_SECONDARY,
                font=(FONT_FAMILY, 9)
            ).pack(anchor=tk.W, pady=(8, 6))
            entry_frame = ModernEntry(content, textvariable=self._input_var, font_size=10)
            entry_frame.pack(fill=tk.X, pady=(0, 20), ipady=4)
            self._input_entry = entry_frame.entry
            self._input_entry.bind("<Return>", lambda e: self._on_ok())
            self._input_entry.bind("<Escape>", lambda e: self._on_cancel())

        btn_row = tk.Frame(content, bg=BG_WHITE)
        btn_row.pack(fill=tk.X, pady=(16, 0) if not input_prompt else (4, 0))
        buttons = buttons or [("确定", "ok", "primary"), ("取消", "cancel", "secondary")]
        right_btns = tk.Frame(btn_row, bg=BG_WHITE)
        right_btns.pack(side=tk.RIGHT)
        for text, value, btype in reversed(buttons):
            btn = RoundedButton(right_btns, text=text, btn_type=btype,
                                command=lambda v=value: self._on_button(v),
                                height=36, font_size=9)
            btn.pack(side=tk.RIGHT, padx=(10, 0))

    def center_on_parent(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self._parent.winfo_width()
        ph = self._parent.winfo_height()
        px = self._parent.winfo_rootx()
        py = self._parent.winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _on_button(self, value):
        self.result = value
        if value == "ok" or value is True:
            if hasattr(self, '_input_var'):
                self.input_value = self._input_var.get()
            self.destroy()
        else:
            self.destroy()

    def _on_ok(self):
        self._on_button("ok")

    def _on_cancel(self):
        self.result = "cancel"
        self.destroy()


class ToastManager:
    _instance = None

    def __init__(self, root):
        self.root = root
        self.toasts = []

    @classmethod
    def get(cls, root=None):
        if cls._instance is None and root is not None:
            cls._instance = cls(root)
        return cls._instance

    def show(self, message, level="success", duration=3000):
        toast = tk.Frame(self.root, bg=BG_MAIN)
        canvas = tk.Canvas(toast, bg=BG_MAIN, highlightthickness=0, bd=0, height=44)
        canvas.pack(fill=tk.X, expand=True, padx=8, pady=4)
        colors = {
            "success": TOAST_SUCCESS,
            "error": TOAST_ERROR,
            "warning": TOAST_WARNING,
            "info": "#1E90FF",
        }
        bg = colors.get(level, TOAST_SUCCESS)

        def _draw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 50:
                w = 300
            draw_rounded_rect(canvas, 2, 2, w - 2, h - 2, 22, fill=bg, outline="")
            canvas.create_text(w // 2, h // 2, text=message, fill="#ffffff", font=(FONT_FAMILY, 9))

        canvas.bind("<Configure>", _draw)
        _draw()
        toast.place(relx=0.5, y=10, anchor=tk.N)
        toast.lift()
        self.root.after(duration, lambda: self._remove(toast))
        self.toasts.append(toast)
        self._reposition()

    def _remove(self, toast):
        try:
            toast.destroy()
        except Exception:
            pass
        if toast in self.toasts:
            self.toasts.remove(toast)
        self._reposition()

    def _reposition(self):
        y = 10
        for t in self.toasts:
            try:
                t.place_configure(y=y)
                y += 52
            except Exception:
                pass



@dataclass
class ReplyRule:
    keywords: list
    reply: str


class RuleBook:
    def __init__(self, path: Path):
        self.path = path
        self.default_reply = ""
        self.cooldown = 8
        self.rules = []
        self.load()

    def load(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.default_reply = data.get("default_reply", "")
        self.cooldown = int(data.get("reply_cooldown_seconds", 8))
        self.rules = [
            ReplyRule(item.get("keywords", []), item.get("reply", ""))
            for item in data.get("rules", [])
        ]

    def match(self, text: str) -> str:
        folded = text.lower()
        for rule in self.rules:
            if any(str(keyword).lower() in folded for keyword in rule.keywords):
                return rule.reply
        return self.default_reply


class AgnesConfig:
    def __init__(self, path: Path):
        self.path = path
        self.enabled = False
        self.base_url = "https://apihub.agnes-ai.com/v1"
        self.model = "agnes-2.0-flash"
        self.api_key = ""
        self.temperature = 0.6
        self.max_tokens = 160
        self.input_click_x = None
        self.input_click_y = None
        self.chat_box_x1 = None
        self.chat_box_y1 = None
        self.chat_box_x2 = None
        self.chat_box_y2 = None
        self.incoming_side = "left"
        self.system_prompt = (
            "你是一个聊天助手。目标是像真人一样自然接话、延续聊天，而不是机械客服。"
            "可以借鉴已安装 Skill 的表达方式和知识框架，但不要说自己是 Skill 里的真人或角色。"
            "不要说自己是任何特定角色或真人。不要编造事实；"
            "不要动不动说在忙、稍后回复或人工处理。能正常聊天就正常聊。"
            "回复要短、像真人聊天，通常一句话，尽量 15 到 45 个中文字符。"
            "不要总结、不要讲大道理、不要客服腔、不要输出列表。"
            "不要强行暧昧、不要油腻土味、不要突然转移话题。"
        )
        self.active_skill_hint = ""
        self.active_skill = ""
        self.load()

    def load(self):
        if not self.path.exists():
            self.save()
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.enabled = bool(data.get("enabled", self.enabled))
        self.base_url = str(data.get("base_url", self.base_url)).rstrip("/")
        self.model = str(data.get("model", self.model))
        self.api_key = str(data.get("api_key", self.api_key))
        self.temperature = float(data.get("temperature", self.temperature))
        self.max_tokens = int(data.get("max_tokens", self.max_tokens))
        self.input_click_x = data.get("input_click_x", self.input_click_x)
        self.input_click_y = data.get("input_click_y", self.input_click_y)
        self.chat_box_x1 = data.get("chat_box_x1", self.chat_box_x1)
        self.chat_box_y1 = data.get("chat_box_y1", self.chat_box_y1)
        self.chat_box_x2 = data.get("chat_box_x2", self.chat_box_x2)
        self.chat_box_y2 = data.get("chat_box_y2", self.chat_box_y2)
        self.incoming_side = str(data.get("incoming_side", self.incoming_side))
        self.system_prompt = str(data.get("system_prompt", self.system_prompt))
        self.active_skill_hint = str(data.get("active_skill_hint", ""))
        self.active_skill = str(data.get("active_skill", ""))

    def save(self):
        data = {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "model": self.model,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "input_click_x": self.input_click_x,
            "input_click_y": self.input_click_y,
            "chat_box_x1": self.chat_box_x1,
            "chat_box_y1": self.chat_box_y1,
            "chat_box_x2": self.chat_box_x2,
            "chat_box_y2": self.chat_box_y2,
            "incoming_side": self.incoming_side,
            "system_prompt": self.system_prompt,
            "active_skill_hint": self.active_skill_hint,
            "active_skill": self.active_skill,
        }
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class SkillManager:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def installed_skills(self):
        paths = sorted(self.skills_dir.glob("*/SKILL.md"))
        return [path.parent.name for path in paths]

    def load_skill_prompt(self, skill_name=None):
        """加载 skill prompt。如果指定 skill_name，只加载该 skill；否则加载全部。"""
        if skill_name:
            skill_paths = [self.skills_dir / skill_name / "SKILL.md"]
        else:
            skill_paths = sorted(self.skills_dir.glob("*/SKILL.md"))
        chunks = []
        for path in skill_paths:
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8-sig").strip()
            if text:
                ref_texts = []
                for ref_path in sorted(path.parent.glob("references/**/*.md")):
                    try:
                        ref_text = ref_path.read_text(encoding="utf-8").strip()
                    except UnicodeDecodeError:
                        ref_text = ref_path.read_text(encoding="utf-8-sig").strip()
                    if ref_text:
                        rel = ref_path.relative_to(path.parent)
                        ref_texts.append(f"## Reference: {rel}\n{ref_text}")

                full_text = text
                if ref_texts:
                    full_text = f"{full_text}\n\n# Skill References\n\n" + "\n\n".join(ref_texts)
                if len(full_text) > MAX_SKILL_CHARS:
                    full_text = full_text[:MAX_SKILL_CHARS] + "\n\n[Skill 内容过长，已截断。]"
                chunks.append(f"# Skill: {path.parent.name}\n{full_text}")
        return "\n\n".join(chunks)


class ThemeManager:
    """主题色管理。背景统一纯白，主题色用于按钮、选中态、强调元素。

    数据结构（theme.json）：
    {"accent": "#1E90FF"}
    """

    PRESETS = [
        ("海蓝", "#1E90FF"),
        ("向日葵橙", "#FF6B00"),
        ("翠绿", "#21B36B"),
        ("樱粉", "#FF5C8A"),
        ("靛紫", "#6366F1"),
        ("石墨灰", "#475569"),
        ("中国红", "#E5484D"),
    ]

    DEFAULT_ACCENT = "#1E90FF"

    def __init__(self, path: Path):
        self.path = path
        self.accent = self.DEFAULT_ACCENT
        self.load()

    def load(self):
        if not self.path.exists():
            self.save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.accent = str(data.get("accent", self.DEFAULT_ACCENT)) or self.DEFAULT_ACCENT
        except Exception:
            self.accent = self.DEFAULT_ACCENT

    def save(self):
        self.path.write_text(
            json.dumps({"accent": self.accent}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set_accent(self, color):
        color = (color or "").strip()
        if not color:
            return False, "颜色不能为空"
        if not re.match(r"^#?[0-9A-Fa-f]{6}$", color):
            return False, "请输入 6 位 HEX 颜色，例如 #1E90FF"
        if not color.startswith("#"):
            color = "#" + color
        self.accent = color
        self.save()
        return True, f"主题色已更新为 {color}"

    @staticmethod
    def darken(hex_color, factor=0.18):
        """把 HEX 颜色按比例变暗，用于按钮按下态/阴影边。"""
        m = re.match(r"^#?([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})$", hex_color or "")
        if not m:
            return hex_color
        r, g, b = (int(x, 16) for x in m.groups())
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def lighten(hex_color, factor=0.85):
        """把 HEX 颜色和白色混合，得到柔和背景色。"""
        m = re.match(r"^#?([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})$", hex_color or "")
        if not m:
            return hex_color
        r, g, b = (int(x, 16) for x in m.groups())
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{r:02X}{g:02X}{b:02X}"

    def palette(self):
        """根据当前 accent 派生一组配色。"""
        accent = self.accent
        return {
            "accent": accent,
            "accent_hot": self.darken(accent, 0.20),
            "accent_press": self.darken(accent, 0.32),
            "accent_soft": self.lighten(accent, 0.86),
            "accent_line": self.darken(accent, 0.10),
        }


class PromiseManager:
    """承诺备忘管理：记录对联系人承诺过的事情。

    数据结构（promises.json）：
    {
      "promises": [
        {
          "id": "p1",
          "contact": "朋友",
          "content": "11点去吃饭",
          "deadline": "11:00",
          "created_at": "2026-07-06 19:00:00",
          "done": false,
          "done_at": ""
        },
        ...
      ]
    }
    """

    def __init__(self, path: Path):
        self.path = path
        self.promises = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.promises = []
            self.save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.promises = list(data.get("promises", []))
        except Exception:
            self.promises = []

    def save(self):
        data = {"promises": self.promises}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _new_id():
        return "p" + uuid.uuid4().hex[:8]

    @staticmethod
    def _now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def all_promises(self, include_done=True):
        if include_done:
            return list(self.promises)
        return [p for p in self.promises if not p.get("done")]

    def add_promise(self, contact, content, deadline=""):
        contact = (contact or "").strip()
        content = (content or "").strip()
        if not content:
            return False, "承诺内容不能为空"
        item = {
            "id": self._new_id(),
            "contact": contact,
            "content": content,
            "deadline": (deadline or "").strip(),
            "created_at": self._now(),
            "done": False,
            "done_at": "",
        }
        self.promises.append(item)
        self.save()
        name_part = f"[{contact}] " if contact else ""
        return True, f"已添加承诺：{name_part}{content}"

    def mark_done(self, promise_id):
        for p in self.promises:
            if p.get("id") == promise_id:
                if p.get("done"):
                    return False, "该承诺已完成"
                p["done"] = True
                p["done_at"] = self._now()
                self.save()
                return True, "已标记完成"
        return False, "承诺不存在"

    def mark_undone(self, promise_id):
        for p in self.promises:
            if p.get("id") == promise_id:
                p["done"] = False
                p["done_at"] = ""
                self.save()
                return True, "已取消完成"
        return False, "承诺不存在"

    def delete_promise(self, promise_id):
        before = len(self.promises)
        self.promises = [p for p in self.promises if p.get("id") != promise_id]
        if len(self.promises) == before:
            return False, "承诺不存在"
        self.save()
        return True, "已删除"


class ContactManager:
    """联系人分类管理：每个分类关联一个 skill，分类下可以有多个具体名字。

    数据结构（contacts.json）：
    {
      "categories": [
        {"name": "领导", "skill": "reply-to-leader", "contacts": ["张总", "王总"]},
        ...
      ]
    }
    """

    DEFAULT_CATEGORIES = [
        {"name": "领导", "skill": "reply-to-leader", "contacts": []},
        {"name": "对象", "skill": "chat-with-partner", "contacts": []},
        {"name": "暧昧对象", "skill": "chat-with-crush", "contacts": []},
        {"name": "朋友", "skill": "chat-with-friends", "contacts": []},
        {"name": "路人", "skill": "chat-with-strangers", "contacts": []},
    ]

    def __init__(self, path: Path, skills_dir: Path):
        self.path = path
        self.skills_dir = skills_dir
        self.categories = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.categories = [dict(c) for c in self.DEFAULT_CATEGORIES]
            self.save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.categories = list(data.get("categories", []))
        except Exception:
            self.categories = [dict(c) for c in self.DEFAULT_CATEGORIES]
        if not self.categories:
            self.categories = [dict(c) for c in self.DEFAULT_CATEGORIES]

    def save(self):
        data = {"categories": self.categories}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def category_names(self):
        return [c.get("name", "") for c in self.categories if c.get("name")]

    def find_category(self, name):
        for c in self.categories:
            if c.get("name") == name:
                return c
        return None

    def add_category(self, name, skill=""):
        name = (name or "").strip()
        if not name:
            return False, "分类名不能为空"
        if self.find_category(name):
            return False, "分类已存在"
        self.categories.append({"name": name, "skill": skill or "", "contacts": []})
        self.save()
        return True, f"已添加分类：{name}"

    def rename_category(self, old, new):
        new = (new or "").strip()
        c = self.find_category(old)
        if not c:
            return False, "原分类不存在"
        if not new:
            return False, "新名字不能为空"
        if new != old and self.find_category(new):
            return False, "名字已存在"
        c["name"] = new
        self.save()
        return True, f"已重命名：{old} -> {new}"

    def delete_category(self, name):
        c = self.find_category(name)
        if not c:
            return False, "分类不存在"
        self.categories = [x for x in self.categories if x.get("name") != name]
        self.save()
        return True, f"已删除分类：{name}"

    def set_category_skill(self, name, skill):
        c = self.find_category(name)
        if not c:
            return False, "分类不存在"
        c["skill"] = skill or ""
        self.save()
        return True, f"已设置 {name} 使用 skill：{skill or '无'}"

    def get_category_skill(self, name):
        c = self.find_category(name)
        return c.get("skill", "") if c else ""

    def contacts_of(self, name):
        c = self.find_category(name)
        if not c:
            return []
        return list(c.get("contacts", []))

    def add_contact(self, category, contact):
        contact = (contact or "").strip()
        if not contact:
            return False, "名字不能为空"
        c = self.find_category(category)
        if not c:
            return False, "分类不存在"
        contacts = c.setdefault("contacts", [])
        if contact in contacts:
            return False, "名字已存在"
        contacts.append(contact)
        self.save()
        return True, f"已添加：{category} - {contact}"

    def delete_contact(self, category, contact):
        c = self.find_category(category)
        if not c:
            return False, "分类不存在"
        contacts = c.setdefault("contacts", [])
        if contact not in contacts:
            return False, "名字不存在"
        contacts.remove(contact)
        self.save()
        return True, f"已删除：{category} - {contact}"


class ChatMemory:
    """按联系人隔离的聊天记忆。

    存储结构：
    {
      "contacts": {
        "<contact_key>": {
          "replied_targets": {...},
          "self_replies": [...],
          "context": [...]
        },
        ...
      },
      "current": "<contact_key>"
    }

    向后兼容：如果旧文件是平铺结构（直接有 replied_targets 等顶层字段），
    会自动迁移到 "_legacy" 联系人下。
    """

    LEGACY_KEY = "_legacy"

    def __init__(self, path: Path):
        self.path = path
        self.contacts = {}
        self.current = self.LEGACY_KEY
        self.load()

    def load(self):
        if not self.path.exists():
            self.save()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if "contacts" in data:
            self.contacts = dict(data.get("contacts", {}))
            self.current = data.get("current", self.LEGACY_KEY) or self.LEGACY_KEY
        else:
            # 旧格式迁移
            legacy = {
                "replied_targets": dict(data.get("replied_targets", {})),
                "self_replies": list(data.get("self_replies", []))[-200:],
                "context": list(data.get("context", []))[-80:],
            }
            self.contacts = {self.LEGACY_KEY: legacy}
            self.current = self.LEGACY_KEY
        if self.current not in self.contacts:
            self.contacts[self.current] = {
                "replied_targets": {},
                "self_replies": [],
                "context": [],
            }
        self.save()

    def save(self):
        data = {"contacts": self.contacts, "current": self.current}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def switch_contact(self, contact_key):
        """切换当前联系人。如果不存在，自动创建空记忆。"""
        contact_key = contact_key or self.LEGACY_KEY
        if contact_key not in self.contacts:
            self.contacts[contact_key] = {
                "replied_targets": {},
                "self_replies": [],
                "context": [],
            }
        self.current = contact_key
        self.save()

    def delete_contact_memory(self, contact_key):
        """删除指定联系人的所有记忆。"""
        if not contact_key:
            return
        if contact_key in self.contacts:
            del self.contacts[contact_key]
            if self.current == contact_key:
                self.current = self.LEGACY_KEY
                if self.current not in self.contacts:
                    self.contacts[self.current] = {
                        "replied_targets": {},
                        "self_replies": [],
                        "context": [],
                    }
            self.save()

    @property
    def replied_targets(self):
        return self.contacts.setdefault(self.current, {"replied_targets": {}, "self_replies": [], "context": []}).setdefault("replied_targets", {})

    @property
    def self_replies(self):
        return self.contacts.setdefault(self.current, {"replied_targets": {}, "self_replies": [], "context": []}).setdefault("self_replies", [])

    @property
    def context(self):
        return self.contacts.setdefault(self.current, {"replied_targets": {}, "self_replies": [], "context": []}).setdefault("context", [])

    @context.setter
    def context(self, value):
        self.contacts.setdefault(self.current, {"replied_targets": {}, "self_replies": [], "context": []})["context"] = list(value)

    @staticmethod
    def normalize(text):
        return " ".join(str(text).split()).strip()

    @classmethod
    def canonical(cls, text):
        normalized = cls.normalize(text).lower()
        return re.sub(r"[\s，。！？、,.!?;；:：\"'“”‘’（）()\[\]【】<>《》]+", "", normalized)

    @classmethod
    def key(cls, text):
        normalized = cls.canonical(text)
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest() if normalized else ""

    def has_replied_target(self, text):
        key = self.key(text)
        if key and key in self.replied_targets:
            return True
        current = self.canonical(text)
        if not current:
            return False
        for item in self.replied_targets.values():
            old = self.canonical(item.get("text", ""))
            if not old:
                continue
            if current == old:
                return True
            if len(current) >= 6 and (current in old or old in current):
                return True
        return False

    def remember_replied_target(self, text):
        normalized = self.normalize(text)
        key = self.key(normalized)
        if not key:
            return
        self.replied_targets[key] = {"text": normalized, "time": time.time()}
        for line in str(text).splitlines():
            line = self.normalize(line)
            line_key = self.key(line)
            if line_key:
                self.replied_targets[line_key] = {"text": line, "time": time.time()}
        if len(self.replied_targets) > 500:
            newest = sorted(self.replied_targets.items(), key=lambda item: item[1].get("time", 0))[-400:]
            self.replied_targets.clear()
            self.replied_targets.update(newest)
        self.save()

    def remember_self_reply(self, text):
        normalized = self.normalize(text)
        if not normalized:
            return
        self.self_replies.append({"text": normalized, "time": time.time()})
        if len(self.self_replies) > 200:
            del self.self_replies[:-200]
        self.save()

    def looks_like_self_reply(self, text):
        normalized = self.canonical(text)
        if not normalized:
            return False
        for item in self.self_replies[-80:]:
            reply = self.canonical(item.get("text", ""))
            if not reply:
                continue
            if normalized == reply:
                return True
            if len(normalized) >= 8 and (normalized in reply or reply in normalized):
                return True
        return False

    def add_context(self, speaker, text):
        normalized = self.normalize(text)
        if not normalized:
            return
        line = f"{speaker}: {normalized}"
        if self.context and self.context[-1] == line:
            return
        self.context.append(line)
        self.context = self.context[-80:]
        self.save()


class AgnesClient:
    def __init__(self, config: AgnesConfig, skills: SkillManager):
        self.config = config
        self.skills = skills

    def chat(self, user_message: str, context=None) -> str:
        if not self.config.api_key:
            raise RuntimeError("Agnes API Key 为空，请先在界面里填写并保存。")

        skill_prompt = self.skills.load_skill_prompt(getattr(self.config, "active_skill", "") or "") if getattr(self.config, "active_skill", "") else ""
        system_prompt = self.config.system_prompt
        if skill_prompt:
            system_prompt = (
                f"{system_prompt}\n\n"
                "重要约束：使用 Skill 只代表吸收风格、话术结构和知识库，不允许自称为 Skill 中的人物；"
                "不要说自己是任何特定角色或真人，也不要让对方误以为真人在回复。\n\n"
                f"下面是已安装的本地 Skill，请遵守：\n\n{skill_prompt}\n\n"
                "最终约束：以上 Skill 只作为知识库和表达风格参考。回复时不要角色扮演真人，"
                '不要使用"我是XX"等身份表达。'
            )
        # 注入当前对象关联的 skill 强提示
        hint = getattr(self.config, "active_skill_hint", "") or ""
        if hint:
            system_prompt = f"{system_prompt}{hint}"

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            context_text = "\n".join(context[-20:])
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "下面是长期聊天记忆，只能用于理解关系、称呼、代词、偏好和话题延续。"
                        "绝对不要逐条回复记忆里的旧消息。回复目标必须是用户本次传入的最新消息：\n"
                        f"{context_text}"
                    ),
                }
            )
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Agnes 请求失败：HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接 Agnes API：{exc.reason}") from exc

        try:
            return clean_reply(data["choices"][0]["message"]["content"].strip())
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Agnes 返回格式异常：{data}") from exc

    def extract_promise(self, reply: str, incoming_message: str = "") -> dict:
        """从刚生成的回复中提取承诺。返回 dict：
        {"has_promise": bool, "content": str, "deadline": str}
        提取失败或无承诺时 has_promise=False。"""
        if not self.config.api_key or not reply:
            return {"has_promise": False, "content": "", "deadline": ""}
        prompt = (
            "下面是你刚才给对方发送的一条回复。请判断这条回复里是否包含对未来的承诺/约定"
            "（比如答应几点去做某事、几点前完成、几点见面、待会儿回、明天处理等）。\n"
            "只提取由“我（回复者）”主动承诺要去做的事情，不要提取对方要求我做的事、也不要提取寒暄。\n"
            "如果有承诺，返回严格的 JSON：\n"
            '{"has_promise": true, "content": "承诺要做的事情（简短一句话，主语省略，例如：去吃饭）", "deadline": "截止/约定时间，如 11:00、明天下午、今晚、2小时内；没有就空字符串"}\n'
            "如果没有承诺，返回：{\"has_promise\": false, \"content\": \"\", \"deadline\": \"\"}\n"
            "只返回 JSON，不要任何解释。\n\n"
            f"对方发来的消息：{incoming_message or '（无）'}\n"
            f"我方的回复：{reply}"
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "你是一个严格的 JSON 提取器，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 120,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
        except Exception:
            return {"has_promise": False, "content": "", "deadline": ""}

        # 兼容 ```json ... ``` 包裹
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            obj = json.loads(text)
        except Exception:
            # 尝试提取第一个 {...}
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                except Exception:
                    return {"has_promise": False, "content": "", "deadline": ""}
            else:
                return {"has_promise": False, "content": "", "deadline": ""}
        if not isinstance(obj, dict):
            return {"has_promise": False, "content": "", "deadline": ""}
        if not obj.get("has_promise"):
            return {"has_promise": False, "content": "", "deadline": ""}
        return {
            "has_promise": True,
            "content": str(obj.get("content", "")).strip(),
            "deadline": str(obj.get("deadline", "")).strip(),
        }

    def chat_with_image(self, prompt: str, image_data_url: str, context=None) -> str:
        if not self.config.api_key:
            raise RuntimeError("Agnes API Key 为空，请先在界面里填写并保存。")

        skill_prompt = self.skills.load_skill_prompt()
        system_prompt = (
            f"{self.config.system_prompt}\n\n"
            "你会看到一张聊天记录区域截图。回复目标必须是对方那一侧最底部的最新 1 到 3 条消息。"
            "不要回复截图中更上方的旧消息。"
            "聊天里通常一侧是对方，一侧是自己；必须严格按用户说明的对方所在侧来判断。"
            "如果最新可见内容来自自己这一侧，必须输出空字符串，不要自己回复自己。"
            "不要输出 OCR 过程，不要解释，不要说自己是任何特定角色或真人。"
        )
        if skill_prompt:
            system_prompt += (
                "\n\n以下 Skill 只作为知识库和表达风格参考，不能角色扮演真人：\n\n"
                f"{skill_prompt}\n\n最终约束：不要自称 Skill 中的人物。"
            )

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "长期聊天记忆如下，只能用于理解关系、称呼、代词、偏好和话题延续。"
                        "不要因为记忆改去回复旧话题：\n" + "\n".join(context[-20:])
                    ),
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        )

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=80) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Agnes 视觉请求失败：HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接 Agnes API：{exc.reason}") from exc

        try:
            return clean_reply(data["choices"][0]["message"]["content"].strip())
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Agnes 视觉返回格式异常：{data}") from exc


def paste_text_to_current_input(text: str, press_enter: bool = True):
    if not text:
        raise RuntimeError("发送内容为空。")
    if pyperclip is None or send_keys is None:
        raise RuntimeError("缺少剪贴板或键盘模拟依赖。")

    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = ""

    pyperclip.copy(text)
    time.sleep(0.1)
    send_keys("^v")
    time.sleep(0.1)
    if press_enter:
        send_keys("{ENTER}")

    try:
        if old_clipboard:
            pyperclip.copy(old_clipboard)
    except Exception:
        pass


def get_cursor_position():
    if win32api is None:
        raise RuntimeError("缺少 win32api，无法读取鼠标位置。")
    x, y = win32api.GetCursorPos()
    return int(x), int(y)


def click_screen_position(x, y):
    if win32api is None or win32con is None:
        raise RuntimeError("缺少 win32api，无法点击固定坐标。")
    win32api.SetCursorPos((int(x), int(y)))
    time.sleep(0.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.12)


def paste_text_to_position(text: str, x, y, press_enter: bool = True):
    click_screen_position(x, y)
    paste_text_to_current_input(text, press_enter=press_enter)


def screenshot_region_as_data_url(region):
    if ImageGrab is None:
        raise RuntimeError("缺少 Pillow/ImageGrab，无法截图。")
    if not region:
        raise RuntimeError("聊天记录框未校准，无法截图识别。")
    x1, y1, x2, y2 = [int(v) for v in region]
    image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def clean_reply(reply, max_chars=70):
    text = " ".join(str(reply or "").split())
    if not text:
        return ""
    prefixes = ("回复：", "建议回复：", "可以回：", "你可以回：", "答：")
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    text = re.sub(r"^[#>*\-\d.、\s]+", "", text)
    text = text.replace("（只输出回复内容）", "").strip()
    if len(text) <= max_chars:
        return text
    cut_points = [text.find(mark) for mark in "。！？!?"]
    cut_points = [idx + 1 for idx in cut_points if 12 <= idx < max_chars]
    if cut_points:
        return text[:cut_points[0]].strip()
    return text[:max_chars].rstrip("，,、；;：:")


def screenshot_region_image(region):
    if ImageGrab is None:
        raise RuntimeError("缺少 Pillow/ImageGrab，无法截图。")
    if not region:
        raise RuntimeError("聊天记录框未校准，无法截图。")
    x1, y1, x2, y2 = [int(v) for v in region]
    return ImageGrab.grab(bbox=(x1, y1, x2, y2))


def incoming_side_region(region, incoming_side):
    if not region:
        return None
    x1, y1, x2, y2 = [int(v) for v in region]
    midpoint = (x1 + x2) // 2
    if incoming_side == "right":
        return midpoint, y1, x2, y2
    return x1, y1, midpoint, y2


def screenshot_fingerprint(region):
    image = screenshot_region_image(region).convert("L").resize((48, 96))
    return list(image.getdata())


def fingerprint_diff(a, b):
    if not a or not b or len(a) != len(b):
        return 999.0
    total = sum(abs(x - y) for x, y in zip(a, b))
    return total / len(a)


def chat_bubble_probe(region, incoming_side):
    image = screenshot_region_image(region).convert("RGB")
    width, height = image.size
    midpoint = width // 2
    outgoing_side = "left" if incoming_side == "right" else "right"
    outgoing_bottom = _detect_latest_outgoing_bottom(image, outgoing_side, midpoint)
    incoming_bottom, incoming_rows = _detect_incoming_content_below(image, incoming_side, midpoint, outgoing_bottom)
    return {
        "incoming_bottom": incoming_bottom,
        "outgoing_bottom": outgoing_bottom,
        "incoming_count": incoming_rows,
        "outgoing_count": 1 if outgoing_bottom is not None else 0,
        "has_new_incoming_below_outgoing": (
            incoming_bottom is not None
            and outgoing_bottom is not None
            and incoming_bottom > outgoing_bottom + 8
        ),
    }


def _detect_latest_outgoing_bottom(image, side, midpoint):
    width, height = image.size
    if side == "right":
        x_start, x_end = midpoint, width
    else:
        x_start, x_end = 0, midpoint
    row_hits = []
    step = 3
    min_pixels = 10
    for y in range(0, height, step):
        hits = 0
        for x in range(x_start, x_end, step):
            r, g, b = image.getpixel((x, y))
            if _looks_like_wechat_green_bubble(r, g, b):
                hits += 1
        if hits >= min_pixels:
            row_hits.append(y)
    return max(row_hits) if row_hits else None


def _detect_incoming_content_below(image, side, midpoint, outgoing_bottom):
    if outgoing_bottom is None:
        return None, 0
    width, height = image.size
    if side == "right":
        x_start, x_end = midpoint, width
    else:
        x_start, x_end = 0, midpoint
    start_y = min(height - 1, int(outgoing_bottom) + 8)
    row_hits = []
    step = 3
    for y in range(start_y, height, step):
        dark_hits = 0
        for x in range(x_start, x_end, step):
            r, g, b = image.getpixel((x, y))
            if _looks_like_text_pixel(r, g, b):
                dark_hits += 1
        if dark_hits >= 3:
            row_hits.append(y)
    if len(row_hits) < 4:
        return None, len(row_hits)
    return max(row_hits), len(row_hits)


def _looks_like_wechat_green_bubble(r, g, b):
    # 微信我方气泡是绿色 #95EC69 附近，放宽阈值避免不同主题/版本漏判
    return g > 160 and r < 210 and b < 210 and g - r > 15 and g - b > 10


def _looks_like_text_pixel(r, g, b):
    return r < 95 and g < 95 and b < 95


WINDOWS_OCR_SCRIPT = r"""
param([string]$Path)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
function Await($AsyncOperation, [Type]$ResultType) {
    $methods = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1
    }
    $method = $methods | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($AsyncOperation))
    $task.Wait() | Out-Null
    $task.Result
}
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$lang = [Windows.Globalization.Language]::new('zh-Hans-CN')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
if ($null -eq $engine) { throw 'Windows OCR engine unavailable' }
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$result.Lines | ForEach-Object { $_.Text }
"""


def windows_ocr_image(image):
    if Image is None:
        raise RuntimeError("缺少 Pillow，无法本地 OCR。")
    temp_dir = Path(tempfile.gettempdir()) / "wechat_auto_reply_ocr"
    temp_dir.mkdir(parents=True, exist_ok=True)
    script_path = temp_dir / "windows_ocr.ps1"
    image_path = temp_dir / f"ocr_{int(time.time() * 1000)}.png"
    script_path.write_text(WINDOWS_OCR_SCRIPT, encoding="utf-8")
    image.save(image_path)
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(image_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=12,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(detail or "Windows OCR 执行失败。")
        return result.stdout
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass


def clean_ocr_lines(text):
    lines = []
    seen = set()
    for raw in str(text).splitlines():
        line = ChatMemory.normalize(raw)
        line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", line)
        line = line.replace("亻尔", "你")
        line = line.replace("亻门", "们")
        line = line.strip(" -_·•|[]【】")
        if not line:
            continue
        key = ChatMemory.canonical(line)
        if not key or key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return lines


RAPID_OCR_ENGINE = None
RAPID_OCR_ERROR = ""
RAPID_OCR_HELPER = r"""
import json
import sys
from pathlib import Path
from PIL import Image
import numpy as np

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    from rapidocr import RapidOCR

image_path = Path(sys.argv[1])
ocr = RapidOCR()
result, _ = ocr(np.array(Image.open(image_path).convert("RGB")))
texts = []
for item in result or []:
    try:
        text = item[1]
    except Exception:
        continue
    if text:
        texts.append(str(text))
print(json.dumps(texts, ensure_ascii=False))
"""


def rapid_ocr_image(image):
    boxes = rapid_ocr_image_with_boxes(image)
    return "\n".join(t for t, _ in boxes)


def rapid_ocr_image_with_boxes(image):
    """返回 [(text, (x_min, y_min, x_max, y_max)), ...]，按 y 升序。"""
    global RAPID_OCR_ENGINE, RAPID_OCR_ERROR
    if Image is None:
        raise RuntimeError("缺少 Pillow，无法本地 OCR。")
    if RAPID_OCR_ERROR:
        return external_rapid_ocr_image_with_boxes(image)
    try:
        if RAPID_OCR_ENGINE is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except Exception:
                from rapidocr import RapidOCR

            RAPID_OCR_ENGINE = RapidOCR()
        import numpy as np

        result, _ = RAPID_OCR_ENGINE(np.array(image.convert("RGB")))
    except Exception as exc:
        RAPID_OCR_ERROR = f"RapidOCR 不可用：{exc}"
        return external_rapid_ocr_image_with_boxes(image)

    items = []
    for entry in result or []:
        try:
            box, text = entry[0], entry[1]
            if not text:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            items.append((str(text), (min(xs), min(ys), max(xs), max(ys))))
        except Exception:
            continue
    items.sort(key=lambda it: (it[1][1], it[1][0]))
    return items


def external_rapid_ocr_image_with_boxes(image):
    import tempfile

    img_path = Path(tempfile.gettempdir()) / "rapid_ocr_helper_input.png"
    image.convert("RGB").save(img_path)
    helper_path = Path(tempfile.gettempdir()) / "rapid_ocr_helper_boxes.py"
    helper_code = RAPID_OCR_HELPER_BOXES
    helper_path.write_text(helper_code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, str(helper_path), str(img_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    except Exception as exc:
        raise RuntimeError(f"外部 RapidOCR 调用失败：{exc}")
    if proc.returncode != 0:
        raise RuntimeError(f"外部 RapidOCR 失败：{proc.stderr[:500]}")
    import json

    try:
        data = json.loads(proc.stdout or "[]")
    except Exception:
        data = []
    items = []
    for entry in data:
        try:
            text = entry.get("text")
            box = entry.get("box")
            if not text or not box:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            items.append((str(text), (min(xs), min(ys), max(xs), max(ys))))
        except Exception:
            continue
    items.sort(key=lambda it: (it[1][1], it[1][0]))
    return items


RAPID_OCR_HELPER_BOXES = r"""
import json
import sys
from pathlib import Path
from PIL import Image
import numpy as np

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    from rapidocr import RapidOCR

image_path = Path(sys.argv[1])
ocr = RapidOCR()
result, _ = ocr(np.array(Image.open(image_path).convert("RGB")))
out = []
for item in result or []:
    try:
        box, text = item[0], item[1]
        if not text:
            continue
        out.append({"text": str(text), "box": [[float(p[0]), float(p[1])] for p in box]})
    except Exception:
        continue
print(json.dumps(out, ensure_ascii=False))
"""


def external_rapid_ocr_image(image):
    temp_dir = Path(tempfile.gettempdir()) / "wechat_auto_reply_ocr"
    temp_dir.mkdir(parents=True, exist_ok=True)
    script_path = temp_dir / "rapid_ocr_helper.py"
    image_path = temp_dir / f"rapid_{int(time.time() * 1000)}.png"
    script_path.write_text(RAPID_OCR_HELPER, encoding="utf-8")
    image.save(image_path)
    try:
        result = subprocess.run(
            [sys.executable if not getattr(sys, "frozen", False) else "python", str(script_path), str(image_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=45,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            if (
                "No module named 'rapidocr_onnxruntime'" in detail
                or 'No module named "rapidocr_onnxruntime"' in detail
                or "No module named 'rapidocr'" in detail
                or 'No module named "rapidocr"' in detail
            ):
                detail = "未安装 RapidOCR，请运行 install_rapidocr.bat"
            raise RuntimeError(detail or "外部 RapidOCR 执行失败。")
        texts = json.loads((result.stdout or "[]").strip() or "[]")
        return "\n".join(str(item) for item in texts if item)
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass


def local_ocr_image(image):
    # 使用 RapidOCR（基于 PaddleOCR PP-OCRv4 模型的 ONNX 轻量版，中文识别准确）
    text = rapid_ocr_image(image)
    return text, "RapidOCR"


def local_ocr_incoming_below(region, incoming_side):
    """OCR 聊天区域，按每行水平中心点距离左右边缘的远近判断归属。

    用户语义：离哪边近就是哪边发的。
    - 对方在左：cx < width - cx（即 cx < width/2）算对方
    - 对方在右：cx > width - cx（即 cx > width/2）算对方
    只返回对方侧的行，自动剔除我方气泡内容。
    """
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    image = screenshot_region_image(region).convert("RGB")
    image.save(DEBUG_DIR / "last_chat_region.png")
    width, height = image.size
    probe = chat_bubble_probe(region, incoming_side)
    outgoing_bottom = probe.get("outgoing_bottom")

    # 放大 2 倍提升 OCR 精度
    big = image.resize((width * 2, height * 2), Image.LANCZOS)
    items = rapid_ocr_image_with_boxes(big)
    # 把坐标还原到原图坐标系
    items = [(t, (b[0] / 2, b[1] / 2, b[2] / 2, b[3] / 2)) for t, b in items]

    # 保存原始 OCR 结果用于调试
    raw_text = "\n".join(t for t, _ in items)
    (DEBUG_DIR / "last_ocr_raw.txt").write_text(raw_text, encoding="utf-8")

    # 按水平中心点判断每行归属
    incoming_items = []
    outgoing_items = []
    for text, (x1, y1, x2, y2) in items:
        cx = (x1 + x2) / 2
        dist_left = cx
        dist_right = width - cx
        is_incoming = (dist_left < dist_right) if incoming_side == "left" else (dist_right < dist_left)
        if is_incoming:
            incoming_items.append((text, (x1, y1, x2, y2)))
        else:
            outgoing_items.append((text, (x1, y1, x2, y2)))

    # 保存调试用的裁剪图：标记了归属的整图
    try:
        debug_img = image.copy()
        from PIL import ImageDraw
        draw = ImageDraw.Draw(debug_img)
        for text, (x1, y1, x2, y2) in incoming_items:
            draw.rectangle([x1, y1, x2, y2], outline=(0, 200, 0), width=2)
        for text, (x1, y1, x2, y2) in outgoing_items:
            draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=2)
        debug_img.save(DEBUG_DIR / "last_ocr_crop.png")
    except Exception:
        image.crop((0, 0, width, height)).save(DEBUG_DIR / "last_ocr_crop.png")

    # 优先：只取绿色气泡下方的对方侧行（如果有绿色气泡）
    if outgoing_bottom is not None:
        threshold_y = int(outgoing_bottom) + 4
        below = [t for t, b in incoming_items if b[1] >= threshold_y]
        if below:
            lines = clean_ocr_lines("\n".join(below))
            if lines:
                detail = f"RapidOCR，绿色气泡底部={outgoing_bottom}，按坐标分边后取对方侧下方{len(below)}行"
                return lines, detail

    # 兜底：没有绿色气泡或下方没对方行，返回所有对方侧行（按 y 升序，取末尾若干条）
    if incoming_items:
        all_incoming = [t for t, _ in incoming_items]
        lines = clean_ocr_lines("\n".join(all_incoming))
        if lines:
            detail = f"RapidOCR，按坐标分边后对方侧共{len(all_incoming)}行，绿色气泡底部={outgoing_bottom}"
            return lines, detail

    lines = []
    detail = f"对方侧无可见内容（按坐标分边），绿色气泡底部={outgoing_bottom}"
    return lines, detail


class WeChatAutomation:
    def __init__(self):
        if Desktop is None:
            raise RuntimeError("缺少依赖，请先运行：python -m pip install -r requirements.txt")
        self.window = None
        self.sent_replies = set()
        self.last_seen_texts = []
        self.last_seen_items = []

    def connect(self):
        desktop = Desktop(backend="uia")
        windows = desktop.windows()
        for win in windows:
            title = win.window_text() or ""
            if WECHAT_TITLE_RE.match(title) and win.is_visible():
                self.window = win
                return title
        raise RuntimeError("没有找到已打开的电脑聊天窗口。请先登录并打开聊天软件。")

    def ensure_window(self):
        if self.window is None:
            self.connect()
        try:
            if not self.window.exists(timeout=1):
                self.connect()
        except Exception:
            self.connect()
        return self.window

    def latest_message(self, region=None, incoming_side="left"):
        unique = self.visible_messages(region=region, incoming_side=incoming_side)
        for text in reversed(unique):
            if text not in self.sent_replies:
                return text
        return ""

    def visible_messages(self, region=None, incoming_side="left"):
        items = self.message_items(region=region, incoming_side=incoming_side)
        unique = []
        seen = set()
        for item in items:
            if item["side"] != "incoming":
                continue
            text = item["text"]
            if text not in seen:
                unique.append(text)
                seen.add(text)
        self.last_seen_texts = unique
        return unique

    def message_items(self, region=None, incoming_side="left"):
        win = self.ensure_window()
        items = []
        for control_type in ("Text", "ListItem"):
            try:
                for item in win.descendants(control_type=control_type):
                    text = (item.window_text() or "").strip()
                    if self._looks_like_message(text) and self._is_in_region(item, region):
                        meta = self._message_meta(item, region, incoming_side)
                        if meta:
                            meta["text"] = text
                            items.append(meta)
            except Exception:
                continue

        unique = []
        seen = set()
        for item in sorted(items, key=lambda row: (row["cy"], row["cx"], row["text"])):
            key = (item["text"], item["side"], round(item["cy"], 1))
            if key in seen:
                continue
            unique.append(item)
            seen.add(key)
        self.last_seen_items = unique
        return unique

    def send_reply(self, reply: str):
        win = self.ensure_window()
        win.set_focus()
        time.sleep(0.2)
        self._focus_input_box(win)

        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste() if pyperclip else ""
        except Exception:
            old_clipboard = ""

        pyperclip.copy(reply)
        time.sleep(0.1)
        send_keys("^v")
        time.sleep(0.1)
        send_keys("{ENTER}")
        self.sent_replies.add(reply)

        try:
            if old_clipboard:
                pyperclip.copy(old_clipboard)
        except Exception:
            pass

    def _focus_input_box(self, win):
        edit_controls = []
        try:
            edit_controls = win.descendants(control_type="Edit")
        except Exception:
            edit_controls = []

        for item in reversed(edit_controls):
            try:
                rect = item.rectangle()
                if rect.width() > 80 and rect.height() > 20:
                    item.click_input()
                    time.sleep(0.15)
                    return
            except Exception:
                continue

        try:
            rect = win.rectangle()
            win.click_input(coords=(max(120, rect.width() // 2), max(120, rect.height() - 80)))
            time.sleep(0.15)
        except Exception:
            pass

    def diagnostic_dump(self, limit=250):
        win = self.ensure_window()
        rows = [f"窗口标题: {win.window_text()}"]
        for index, item in enumerate(win.descendants()):
            if index >= limit:
                rows.append(f"... 已截断，只显示前 {limit} 个控件")
                break
            try:
                rows.append(
                    f"{index:03d} | {item.friendly_class_name():18s} | "
                    f"{item.element_info.control_type:12s} | {item.window_text()!r}"
                )
            except Exception:
                continue
        return "\n".join(rows)

    @staticmethod
    def _is_in_region(item, region):
        if not region:
            return True
        x1, y1, x2, y2 = region
        try:
            rect = item.rectangle()
            cx = (rect.left + rect.right) / 2
            cy = (rect.top + rect.bottom) / 2
            return x1 <= cx <= x2 and y1 <= cy <= y2
        except Exception:
            return False

    @staticmethod
    def _is_on_incoming_side(item, region, incoming_side):
        if not region:
            return True
        x1, _y1, x2, _y2 = region
        midpoint = (x1 + x2) / 2
        try:
            rect = item.rectangle()
            cx = (rect.left + rect.right) / 2
            if incoming_side == "right":
                return cx >= midpoint
            return cx <= midpoint
        except Exception:
            return False

    @staticmethod
    def _message_meta(item, region, incoming_side):
        try:
            rect = item.rectangle()
            cx = (rect.left + rect.right) / 2
            cy = (rect.top + rect.bottom) / 2
        except Exception:
            return None
        side = "incoming"
        if region:
            x1, _y1, x2, _y2 = region
            midpoint = (x1 + x2) / 2
            is_incoming = cx >= midpoint if incoming_side == "right" else cx <= midpoint
            side = "incoming" if is_incoming else "outgoing"
        return {"cx": cx, "cy": cy, "side": side}

    @staticmethod
    def _looks_like_message(text: str):
        if not text:
            return False
        if len(text) > 500:
            return False
        if NOISE_RE.match(text):
            return False
        if TIME_RE.match(text):
            return False
        if text.startswith("[") and text.endswith("]"):
            return False
        return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Agnes 聊天回复助手")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self.configure(bg=BG_MAIN)
        self._setup_ttk_style()
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 3
        self.geometry(f"+{x}+{y}")

        self.rulebook = RuleBook(RULES_FILE)
        self.agnes_config = AgnesConfig(CONFIG_FILE)
        self.skills = SkillManager(SKILLS_DIR)
        self.theme = ThemeManager(THEME_FILE)
        self.theme_color_var = tk.StringVar(value=self.theme.accent)
        self.contacts = ContactManager(CONTACTS_FILE, SKILLS_DIR)
        self.promises = PromiseManager(PROMISES_FILE)
        self.memory = ChatMemory(MEMORY_FILE)
        self.agnes = AgnesClient(self.agnes_config, self.skills)
        self.wechat = None
        self.worker = None
        self.stop_event = threading.Event()
        self.events = queue.Queue()
        self.last_message = ""
        self.last_reply_at = {}
        self.last_vision_at = 0
        self.last_incoming_fingerprint = None
        self.last_self_reply_at = 0

        self.dry_run = tk.BooleanVar(value=True)
        self.use_agnes = tk.BooleanVar(value=self.agnes_config.enabled)
        self.status_text = tk.StringVar(value="未连接")
        self.run_state_var = tk.StringVar(value="已停止")
        self.delay_state_var = tk.StringVar(value="延迟：5-10 秒随机")
        self.last_action_var = tk.StringVar(value="最近：等待启动")
        self.api_key_var = tk.StringVar(value=self.agnes_config.api_key)
        self.base_url_var = tk.StringVar(value=self.agnes_config.base_url)
        self.model_var = tk.StringVar(value=self.agnes_config.model)
        self.target_note_var = tk.StringVar(value="")
        self.locked_target_var = tk.StringVar(value="未锁定，禁止自动发送")
        self.contact_category_var = tk.StringVar(value="")
        self.contact_name_var = tk.StringVar(value="")
        self.contact_skill_var = tk.StringVar(value="")
        self.input_position_var = tk.StringVar(value=self._input_position_summary())
        self.chat_box_var = tk.StringVar(value=self._chat_box_summary())
        self.incoming_side_var = tk.StringVar(value=self.agnes_config.incoming_side)
        self.target_locked = False
        self.chat_context = list(self.memory.context[-30:])
        self.recent_self_replies = []
        self.last_skipped_target = ""
        self.has_sent_in_current_chat = False
        self.last_local_gate_log_at = 0

        self._setup_colors()
        self._build_ui()
        self.toast = ToastManager.get(self)
        self.after(150, self._drain_events)

    def _setup_colors(self):
        self.colors = {
            "bg": BG_MAIN,
            "sidebar": BG_WHITE,
            "panel": BG_WHITE,
            "ink": TEXT_PRIMARY,
            "ink_soft": TEXT_SECONDARY,
            "muted": TEXT_MUTED,
            "line": "#e8e9eb",
            "line_strong": "#e5e6eb",
            "hover": HOVER_LIGHT,
            "pressed": "#e5e6eb",
        }
        self.colors.update(self.theme.palette())

    def _refresh_theme_colors(self):
        self.colors.update(self.theme.palette())
        c = self.colors
        for widget in self.winfo_children():
            self._refresh_widget_accent(widget)
        if hasattr(self, 'theme_preview_label'):
            self.theme_preview_label.configure(bg=c["accent"])
        for attr in ('status_pill_outer', 'status_pill_inner', 'status_run_label', 'status_action_label'):
            if hasattr(self, attr):
                w = getattr(self, attr)
                if attr == 'status_pill_outer':
                    w.configure(bg=BORDER_CARD)
                else:
                    if attr == 'status_run_label':
                        w.configure(bg=c["accent_soft"], fg=c["accent_hot"])
                    elif attr == 'status_action_label':
                        w.configure(bg=c["accent_soft"], fg=TEXT_MUTED)
                    else:
                        w.configure(bg=c["accent_soft"])
        try:
            self._refresh_nav_colors()
        except Exception:
            pass

    def _refresh_widget_accent(self, widget):
        try:
            if isinstance(widget, RoundedButton):
                widget.set_accent(self.colors["accent"], self.colors["accent_hot"], self.colors["accent_press"])
            elif isinstance(widget, (ModernEntry, ModernCombobox)):
                widget.set_accent(self.colors["accent"])
            for child in widget.winfo_children():
                self._refresh_widget_accent(child)
        except Exception:
            pass

    def show_toast(self, message, level="success"):
        if self.toast:
            self.toast.show(message, level=level)

    def ask_string(self, title, prompt, initialvalue="", parent=None):
        dlg = ModernDialog(parent or self, title=title, message=None, input_prompt=prompt, initialvalue=initialvalue,
                          buttons=[("确定", "ok", "primary"), ("取消", "cancel", "secondary")])
        self.wait_window(dlg)
        if dlg.result == "ok":
            return getattr(dlg, 'input_value', None)
        return None

    def ask_ok_cancel(self, title, message, parent=None):
        dlg = ModernDialog(parent or self, title=title, message=message,
                          buttons=[("确定", "ok", "primary"), ("取消", "cancel", "secondary")])
        self.wait_window(dlg)
        return dlg.result == "ok"

    def show_info(self, title, message, level="info"):
        dlg = ModernDialog(self, title=title, message=message, buttons=[("确定", "ok", "primary")])
        self.wait_window(dlg)

    def _build_ui(self):
        def make_text(parent, height):
            outer = tk.Frame(parent, bg=BORDER_CARD, bd=0, highlightthickness=0)
            inner = tk.Frame(outer, bg=BG_TEXT_AREA, bd=0, highlightthickness=0)
            inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
            sb = tk.Scrollbar(inner, orient=tk.VERTICAL, bg=BG_TEXT_AREA, troughcolor=BG_TEXT_AREA,
                              activebackground="#c0c4cc", highlightthickness=0, bd=0, width=10)
            box = tk.Text(
                inner,
                height=height,
                wrap=tk.WORD,
                relief=tk.FLAT,
                borderwidth=0,
                padx=14,
                pady=12,
                bg=BG_TEXT_AREA,
                fg=TEXT_PRIMARY,
                insertbackground=self.colors["accent"],
                selectbackground=self.colors["accent_soft"],
                selectforeground=TEXT_PRIMARY,
                font=(FONT_FAMILY, FONT_SIZE_BASE),
                highlightthickness=0,
                spacing1=2,
                spacing3=2,
                yscrollcommand=sb.set,
            )
            sb.configure(command=box.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=0)
            box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0, pady=0)
            def _focus_in(e):
                outer.configure(bg=self.colors["accent"])
            def _focus_out(e):
                outer.configure(bg=BORDER_CARD)
            box.bind("<FocusIn>", _focus_in)
            box.bind("<FocusOut>", _focus_out)
            sb.bind("<FocusIn>", _focus_in)
            # Proxy methods
            for _m in ("get", "delete", "insert", "see", "index", "search",
                       "yview", "yview_moveto", "yview_scroll",
                       "xview", "config", "configure",
                       "bind", "unbind", "tag_config", "tag_add", "tag_remove",
                       "mark_set", "scan_dragto", "scan_mark",
                       "edit_modified", "edit_reset", "bbox", "dlineinfo"):
                try:
                    setattr(outer, _m, getattr(box, _m))
                except AttributeError:
                    pass
            outer.text = box
            outer.scrollbar = sb
            return outer

        root = tk.Frame(self, bg=BG_MAIN)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        sidebar_wrap = tk.Frame(root, bg=BG_SIDEBAR, highlightthickness=0)
        sidebar_wrap.grid(row=0, column=0, sticky=tk.NS)
        sep = tk.Frame(sidebar_wrap, bg=BORDER_CARD, width=1)
        sep.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar = tk.Frame(sidebar_wrap, width=SIDEBAR_WIDTH, bg=BG_SIDEBAR, padx=16, pady=28)
        sidebar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sidebar.pack_propagate(False)
        sidebar_wrap.configure(width=SIDEBAR_WIDTH + 1)

        self.logo_image = self._load_logo_image(40)
        brand_row = tk.Frame(sidebar, bg=BG_SIDEBAR)
        brand_row.pack(fill=tk.X, pady=(0, 28), side=tk.TOP)
        if self.logo_image:
            mark = tk.Label(brand_row, image=self.logo_image, bg=BG_SIDEBAR, bd=0)
        else:
            mark = tk.Label(
                brand_row, text="A", width=2, height=1,
                bg=self.colors["accent"], fg="#ffffff",
                font=(FONT_FAMILY, 14, "bold"),
            )
        mark.pack(side=tk.LEFT)
        brand_text = tk.Frame(brand_row, bg=BG_SIDEBAR)
        brand_text.pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(brand_text, text="Agnes", bg=BG_SIDEBAR, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 16, "bold")).pack(anchor=tk.W)
        tk.Label(brand_text, text="聊天自动回复", bg=BG_SIDEBAR, fg=TEXT_MUTED, font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(anchor=tk.W, pady=(2, 0))

        sidebar_bottom = tk.Frame(sidebar, bg=BG_SIDEBAR)
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X)

        sep2 = tk.Frame(sidebar_bottom, bg=BORDER_CARD, height=1)
        sep2.pack(fill=tk.X, pady=(0, 16))

        self.status_pill_outer = tk.Frame(sidebar_bottom, bg=BORDER_CARD)
        self.status_pill_outer.pack(fill=tk.X, pady=(0, 12))
        self.status_pill_inner = tk.Frame(self.status_pill_outer, bg=self.colors["accent_soft"])
        self.status_pill_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.status_run_label = tk.Label(self.status_pill_inner, textvariable=self.run_state_var,
                                         bg=self.colors["accent_soft"], fg=self.colors["accent_hot"],
                                         anchor="w", font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"), padx=12, pady=6)
        self.status_run_label.pack(fill=tk.X)
        self.status_action_label = tk.Label(self.status_pill_inner, textvariable=self.last_action_var,
                                            bg=self.colors["accent_soft"], fg=TEXT_MUTED,
                                            anchor="w", justify=tk.LEFT, wraplength=160,
                                            font=(FONT_FAMILY, FONT_SIZE_SMALL), padx=12, pady=4)
        self.status_action_label.pack(fill=tk.X)

        btn_connect = RoundedButton(sidebar_bottom, text="连接聊天", btn_type="primary", command=self.connect_wechat, height=42, font_size=FONT_SIZE_BASE)
        btn_connect.pack(fill=tk.X, pady=(0, 8))
        btn_theme = RoundedButton(sidebar_bottom, text="主题外观", btn_type="secondary", command=self._show_theme_dialog, height=38, font_size=FONT_SIZE_BASE)
        btn_theme.pack(fill=tk.X)

        self.nav_canvases = {}
        self.nav_labels = {}
        nav_items = [
            ("reply", "回复工作台"),
            ("calibrate", "校准发送"),
            ("promises", "承诺备忘"),
            ("settings", "Agnes 设置"),
            ("tutorial", "使用教程"),
            ("logs", "运行日志"),
            ("sponsor", "赞赏支持"),
        ]
        self.nav_items_info = {}
        nav_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        nav_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        for key, label in nav_items:
            row = tk.Frame(nav_frame, bg=BG_SIDEBAR, height=44)
            row.pack(fill=tk.X, pady=1)
            row.pack_propagate(False)
            bar = tk.Frame(row, bg=BG_SIDEBAR, width=3)
            bar.pack(side=tk.LEFT, fill=tk.Y)
            lbl = tk.Label(row, text="  " + label, anchor="w", padx=12,
                          bg=BG_SIDEBAR, fg=TEXT_SECONDARY,
                          font=(FONT_FAMILY, FONT_SIZE_NAV), cursor="hand2")
            lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for w in (row, lbl, bar):
                w.bind("<Button-1>", lambda e, name=key: self._show_page(name))
                w.bind("<Enter>", lambda e, k=key: self._nav_hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self._nav_hover(k, False))
            self.nav_items_info[key] = (row, lbl, bar)
        self.nav_canvases = {}
        self.nav_labels = {k: v[1] for k, v in self.nav_items_info.items()}

        content = tk.Frame(root, bg=BG_MAIN, padx=40, pady=32)
        content.grid(row=0, column=1, sticky=tk.NSEW)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        header = tk.Frame(content, bg=BG_MAIN)
        header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 28))
        header.columnconfigure(0, weight=1)
        self.page_title_label = tk.Label(header, text="回复工作台", bg=BG_MAIN, fg=TEXT_PRIMARY,
                                         font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), anchor=tk.W)
        self.page_title_label.grid(row=0, column=0, sticky=tk.W)
        self.page_subtitle_label = tk.Label(header, text="只回复最新收到的消息，记忆只做上下文", bg=BG_MAIN,
                                            fg=TEXT_MUTED, font=(FONT_FAMILY, FONT_SIZE_SMALL), anchor=tk.W)
        self.page_subtitle_label.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        header_actions = tk.Frame(header, bg=BG_MAIN)
        header_actions.grid(row=0, column=1, rowspan=2, sticky=tk.E)
        RoundedButton(header_actions, text="重载 Skill", btn_type="secondary", command=self.reload_rules, width=100, height=36, font_size=FONT_SIZE_SMALL).pack(side=tk.LEFT, padx=(0, 8))
        RoundedButton(header_actions, text="开始", btn_type="primary", command=self.start, width=80, height=36, font_size=FONT_SIZE_BASE).pack(side=tk.LEFT, padx=(0, 8))
        RoundedButton(header_actions, text="停止", btn_type="secondary", command=self.stop, width=80, height=36, font_size=FONT_SIZE_BASE).pack(side=tk.LEFT)

        self.page_host = tk.Frame(content, bg=BG_MAIN)
        self.page_host.grid(row=1, column=0, sticky=tk.NSEW)
        self.page_host.columnconfigure(0, weight=1)
        self.page_host.rowconfigure(0, weight=1)
        self.pages = {}

        reply_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        calibrate_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        promises_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        settings_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        tutorial_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        logs_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        sponsor_tab = tk.Frame(self.page_host, bg=BG_MAIN)
        for page in (reply_tab, calibrate_tab, promises_tab, settings_tab, tutorial_tab, logs_tab, sponsor_tab):
            page.grid(row=0, column=0, sticky=tk.NSEW)
            page.columnconfigure(0, weight=1)
            page.rowconfigure(1, weight=1)
        self.pages = {
            "reply": reply_tab,
            "calibrate": calibrate_tab,
            "promises": promises_tab,
            "settings": settings_tab,
            "tutorial": tutorial_tab,
            "logs": logs_tab,
            "sponsor": sponsor_tab,
        }

        self._build_promises_page(promises_tab)
        self._build_sponsor_page(sponsor_tab)

        quick_card = Card(reply_tab, padding=20)
        quick_card.grid(row=0, column=0, sticky=tk.EW, pady=(0, 20))
        quick_body = quick_card.body
        cb_kw = dict(bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, FONT_SIZE_BASE),
                     selectcolor=BG_WHITE, activebackground=BG_WHITE, activeforeground=TEXT_PRIMARY,
                     bd=0, highlightthickness=0)
        tk.Checkbutton(quick_body, text="只预览，不发送", variable=self.dry_run, **cb_kw).grid(row=0, column=0, sticky=tk.W, padx=(0, 24))
        tk.Checkbutton(quick_body, text="Agnes 生成回复", variable=self.use_agnes, **cb_kw).grid(row=0, column=1, sticky=tk.W, padx=(0, 24))
        tk.Label(quick_body, text="建议先预览，确认稳定后再取消预览发送。", bg=BG_WHITE,
                 fg=TEXT_MUTED, font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=0, column=2, sticky=tk.W)

        manual_card = Card(reply_tab)
        manual_card.grid(row=1, column=0, sticky=tk.NSEW)
        tk.Label(manual_card.body, text="手动回复", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, FONT_SIZE_CARD_TITLE, "bold")).pack(anchor=tk.W, pady=(0, 6))
        tk.Label(manual_card.body, text="复制消息或截图识别后生成一句自然回复", bg=BG_WHITE,
                 fg=TEXT_MUTED, font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(anchor=tk.W, pady=(0, 20))

        manual_actions = tk.Frame(manual_card.body, bg=BG_WHITE)
        manual_actions.pack(side=tk.BOTTOM, fill=tk.X, pady=(14, 0))
        RoundedButton(manual_actions, text="从剪贴板读取", btn_type="secondary", command=self.load_message_from_clipboard, width=100, height=34).pack(side=tk.LEFT)
        RoundedButton(manual_actions, text="快速生成", btn_type="primary", command=self.generate_manual_reply, width=88, height=34).pack(side=tk.LEFT, padx=8)
        RoundedButton(manual_actions, text="截图识别", btn_type="secondary", command=self.generate_reply_from_screenshot, width=88, height=34).pack(side=tk.LEFT)
        RoundedButton(manual_actions, text="OCR测试", btn_type="secondary", command=self.test_local_ocr, width=88, height=34).pack(side=tk.LEFT, padx=(8, 0))
        RoundedButton(manual_actions, text="复制", btn_type="secondary", command=self.copy_manual_reply, width=60, height=34).pack(side=tk.LEFT, padx=8)
        RoundedButton(manual_actions, text="发送到聊天", btn_type="primary", command=self.countdown_send_manual_reply, width=100, height=34).pack(side=tk.RIGHT)

        manual_inner = tk.Frame(manual_card.body, bg=BG_WHITE)
        manual_inner.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        manual_inner.columnconfigure(0, weight=1)
        manual_inner.columnconfigure(1, weight=1)
        manual_inner.rowconfigure(1, weight=1)

        tk.Label(manual_inner, text="对方最新消息", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=(0, 10))
        tk.Label(manual_inner, text="建议回复", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=0, column=1, sticky=tk.W, padx=(8, 0), pady=(0, 10))
        self.manual_message_box = make_text(manual_inner, 10)
        self.manual_message_box.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 10))
        self.manual_reply_box = make_text(manual_inner, 10)
        self.manual_reply_box.grid(row=1, column=1, sticky=tk.NSEW, padx=(10, 0))

        target_card = Card(calibrate_tab)
        target_card.grid(row=0, column=0, sticky=tk.EW, pady=(0, 16))
        tk.Label(target_card.body, text="校准与发送", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "bold")).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(target_card.body, text="先选择对象类型和名字，再锁定，最后允许自动发送", bg=BG_WHITE,
                 fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(0, 16))
        target_body = tk.Frame(target_card.body, bg=BG_WHITE)
        target_body.pack(fill=tk.BOTH, expand=True)

        tk.Label(target_body, text="对象分类", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 12))
        self.category_combo = ModernCombobox(target_body, textvariable=self.contact_category_var, values=self.contacts.category_names(), state="readonly")
        self.category_combo.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10), pady=(0, 12))
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_changed)
        RoundedButton(target_body, text="添加分类", btn_type="secondary", command=self._add_category_dialog, width=80).grid(
            row=0, column=2, sticky=tk.EW, padx=(0, 8), pady=(0, 12)
        )
        RoundedButton(target_body, text="管理名字", btn_type="secondary", command=self._manage_contacts_dialog, width=80).grid(
            row=0, column=3, sticky=tk.EW, pady=(0, 12)
        )

        tk.Label(target_body, text="具体名字", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 12))
        self.name_combo = ModernCombobox(target_body, textvariable=self.contact_name_var, values=[], state="readonly")
        self.name_combo.grid(row=1, column=1, sticky=tk.EW, padx=(0, 10), pady=(0, 12))
        RoundedButton(target_body, text="添加名字", btn_type="secondary", command=self._add_contact_dialog, width=80).grid(
            row=1, column=2, sticky=tk.EW, padx=(0, 8), pady=(0, 12)
        )
        RoundedButton(target_body, text="删除名字", btn_type="secondary", command=self._delete_contact_dialog, width=80).grid(
            row=1, column=3, sticky=tk.EW, pady=(0, 12)
        )

        tk.Label(target_body, text="使用 Skill", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 12))
        self.skill_combo = ModernCombobox(target_body, textvariable=self.contact_skill_var, values=self.skills.installed_skills(), state="readonly")
        self.skill_combo.grid(row=2, column=1, sticky=tk.EW, padx=(0, 10), pady=(0, 12))
        RoundedButton(target_body, text="保存关联", btn_type="secondary", command=self._save_association, width=168).grid(
            row=2, column=2, columnspan=2, sticky=tk.EW, pady=(0, 12)
        )

        RoundedButton(target_body, text="锁定", btn_type="primary", command=self._lock_target, width=200).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, padx=(0, 10), pady=(0, 12)
        )
        RoundedButton(target_body, text="解除", btn_type="secondary", command=self._unlock_target, width=168).grid(
            row=3, column=2, columnspan=2, sticky=tk.EW, pady=(0, 12)
        )

        tk.Label(target_body, textvariable=self.locked_target_var, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9), wraplength=600, justify=tk.LEFT).grid(
            row=4, column=0, columnspan=4, sticky=tk.W, pady=(0, 16)
        )
        RoundedButton(target_body, text="校准输入框", btn_type="secondary", command=self.capture_input_position, width=100).grid(
            row=5, column=0, sticky=tk.EW, padx=(0, 10), pady=(0, 10)
        )
        RoundedButton(target_body, text="3秒后校准", btn_type="secondary", command=self.countdown_capture_input_position, width=92).grid(
            row=5, column=1, sticky=tk.W, padx=(0, 10), pady=(0, 10)
        )
        tk.Label(target_body, textvariable=self.input_position_var, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).grid(
            row=5, column=2, columnspan=2, sticky=tk.W, pady=(0, 10)
        )
        RoundedButton(target_body, text="框选聊天框", btn_type="primary", command=self.capture_chat_box_by_drag, width=100).grid(
            row=6, column=0, sticky=tk.EW, padx=(0, 10), pady=(0, 10)
        )
        RoundedButton(target_body, text="左上角", btn_type="secondary", command=lambda: self.capture_chat_box_corner("tl"), width=92).grid(
            row=6, column=1, sticky=tk.EW, padx=(0, 10), pady=(0, 10)
        )
        RoundedButton(target_body, text="右下角", btn_type="secondary", command=lambda: self.capture_chat_box_corner("br"), width=80).grid(
            row=6, column=2, sticky=tk.EW, padx=(0, 10), pady=(0, 10)
        )
        tk.Label(target_body, textvariable=self.chat_box_var, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).grid(
            row=7, column=0, columnspan=4, sticky=tk.W, pady=(0, 12)
        )
        tk.Label(target_body, text="对方消息位置", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=8, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 8))
        side_frame = tk.Frame(target_body, bg=BG_WHITE)
        side_frame.grid(row=8, column=1, columnspan=3, sticky=tk.W, pady=(0, 8))
        tk.Radiobutton(side_frame, text="左侧（默认）", variable=self.incoming_side_var, value="left",
                       command=self.save_incoming_side, bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9),
                       selectcolor=BG_WHITE, activebackground=BG_WHITE).pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(side_frame, text="右侧", variable=self.incoming_side_var, value="right",
                       command=self.save_incoming_side, bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9),
                       selectcolor=BG_WHITE, activebackground=BG_WHITE).pack(side=tk.LEFT)

        cats = self.contacts.category_names()
        if cats:
            self.contact_category_var.set(cats[0])
            self.on_category_changed()
        target_body.columnconfigure(1, weight=1)

        actions_card = Card(calibrate_tab, padding=18)
        actions_card.grid(row=1, column=0, sticky=tk.EW)
        actions_body = actions_card.body
        RoundedButton(actions_body, text="读取最新消息", btn_type="secondary", command=self.peek_latest_message, width=100).pack(side=tk.LEFT)
        RoundedButton(actions_body, text="测试发送", btn_type="primary", command=self._test_send, width=88).pack(side=tk.LEFT, padx=8)
        RoundedButton(actions_body, text="3秒后测试", btn_type="secondary", command=self._test_send_delayed, width=88).pack(side=tk.LEFT)
        RoundedButton(actions_body, text="诊断控件", btn_type="secondary", command=self._diagnose_controls, width=88).pack(side=tk.RIGHT)

        agnes_card = Card(settings_tab)
        agnes_card.grid(row=0, column=0, sticky=tk.EW, pady=(0, 16))
        tk.Label(agnes_card.body, text="Agnes 与 Skill", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "bold")).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(agnes_card.body, text="配置保存后立即生效", bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(0, 16))
        agnes_body = tk.Frame(agnes_card.body, bg=BG_WHITE)
        agnes_body.pack(fill=tk.X)

        tk.Label(agnes_body, text="Base URL", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 12))
        self.base_url_entry = ModernEntry(agnes_body, textvariable=self.base_url_var)
        self.base_url_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 12), pady=(0, 12))
        tk.Label(agnes_body, text="模型", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=0, column=2, sticky=tk.W, padx=(0, 10), pady=(0, 12))
        self.model_entry = ModernEntry(agnes_body, textvariable=self.model_var)
        self.model_entry.grid(row=0, column=3, sticky=tk.EW, pady=(0, 12))

        tk.Label(agnes_body, text="API Key", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 12))
        self.api_key_entry = ModernEntry(agnes_body, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(0, 12), pady=(0, 12))
        RoundedButton(agnes_body, text="保存配置", btn_type="primary", command=self.save_agnes_config, width=88).grid(
            row=1, column=3, sticky=tk.EW, pady=(0, 12)
        )
        RoundedButton(agnes_body, text="测试 Agnes", btn_type="secondary", command=self.test_agnes, width=88).grid(
            row=2, column=3, sticky=tk.EW
        )
        self.skills_text = tk.StringVar(value=self._skills_summary())
        tk.Label(agnes_body, textvariable=self.skills_text, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9), wraplength=600, justify=tk.LEFT).grid(
            row=2, column=0, columnspan=3, sticky=tk.W
        )
        agnes_body.columnconfigure(1, weight=1)
        agnes_body.columnconfigure(3, weight=1)

        theme_card = Card(settings_tab)
        theme_card.grid(row=1, column=0, sticky=tk.EW, pady=(0, 16))
        tk.Label(theme_card.body, text="主题外观", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "bold")).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(theme_card.body, text="背景统一纯白，主题色用于按钮、选中态和强调元素", bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(0, 16))
        theme_body = theme_card.body

        swatch_holder = tk.Frame(theme_body, bg=BG_WHITE)
        swatch_holder.pack(fill=tk.X, pady=(0, 10))
        for i, (name, color) in enumerate(self.theme.PRESETS):
            row = i // 7
            col = i % 7
            cell = tk.Frame(swatch_holder, bg=BG_WHITE, width=48, height=52)
            cell.grid(row=row, column=col, padx=4, pady=4)
            cell.grid_propagate(False)
            current = self.theme.accent.lower() == color.lower()
            scv = tk.Canvas(cell, bg=BG_WHITE, highlightthickness=2 if current else 0,
                                       highlightbackground=self.colors["accent"] if current else BG_WHITE, bd=0, cursor="hand2")
            scv.place(x=6, y=4, width=36, height=36)
            def make_swatch_cmd(c, cv):
                def _cmd(e=None):
                    self.apply_theme(c)
                return _cmd
            def make_swatch_draw(c, cv):
                def _draw(e=None):
                    cv.delete("all")
                    draw_rounded_rect(cv, 2, 2, 34, 34, 8, fill=c, outline="")
                return _draw
            draw_fn = make_swatch_draw(color, scv)
            cmd_fn = make_swatch_cmd(color, scv)
            scv.bind("<Configure>", lambda e, d=draw_fn: d())
            scv.bind("<Button-1>", cmd_fn)
            tk.Label(cell, text=name, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 8)).place(x=0, y=42, width=48, height=14)

        bottom_row = tk.Frame(theme_body, bg=BG_WHITE)
        bottom_row.pack(fill=tk.X)
        self.theme_preview_label = tk.Label(bottom_row, text="  当前  ", bg=self.theme.accent, fg="#ffffff",
                                            font=(FONT_FAMILY, 9, "bold"), padx=10, pady=5)
        self.theme_preview_label.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(bottom_row, textvariable=self.theme_color_var, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(side=tk.LEFT, padx=(0, 12))
        RoundedButton(bottom_row, text="更多选项", btn_type="secondary", command=self._show_theme_dialog, width=88).pack(side=tk.LEFT)

        log_hint_card = Card(settings_tab)
        log_hint_card.grid(row=2, column=0, sticky=tk.EW)
        tk.Label(log_hint_card.body, text="记忆与日志", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "bold")).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(log_hint_card.body, text="聊天记忆保存在 chat_memory.json，运行日志保存在 wechat_auto_reply.log", bg=BG_WHITE,
                 fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(8, 0))
        tk.Label(log_hint_card.body, text="记忆只作为上下文，不会让 Agnes 回复旧消息；已回复过的最新消息会被跳过。", bg=BG_WHITE,
                 fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(4, 0))

        tutorial_card = Card(tutorial_tab, padding=0)
        tutorial_card.grid(row=0, column=0, sticky=tk.NSEW)
        # 用滚动区域承载长教程，直接放在 Card 的 body 里
        tut_body = tutorial_card.body
        tut_body.pack(fill=tk.BOTH, expand=True)
        tut_canvas = tk.Canvas(tut_body, bg=BG_WHITE, highlightthickness=0, bd=0)
        tut_scroll = ttk.Scrollbar(tut_body, orient=tk.VERTICAL, command=tut_canvas.yview)
        tut_inner = tk.Frame(tut_canvas, bg=BG_WHITE)
        tut_inner.bind("<Configure>",
                       lambda e: tut_canvas.configure(scrollregion=tut_canvas.bbox("all")))
        tut_window = tut_canvas.create_window((0, 0), window=tut_inner, anchor="nw")
        tut_canvas.configure(yscrollcommand=tut_scroll.set)
        tut_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tut_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # 让 inner frame 宽度跟随 canvas 变化，文字自适应换行
        def _tut_resize(e):
            tut_canvas.itemconfigure(tut_window, width=tut_canvas.winfo_width())
        tut_canvas.bind("<Configure>", _tut_resize)
        # 鼠标滚轮
        def _tut_wheel(e):
            tut_canvas.yview_scroll(int(-e.delta / 120), "units")
        tut_canvas.bind("<Enter>", lambda e: tut_canvas.bind_all("<MouseWheel>", _tut_wheel))
        tut_canvas.bind("<Leave>", lambda e: tut_canvas.unbind_all("<MouseWheel>"))
        tut_inner.columnconfigure(0, weight=1)

        def _tut_label(parent, text, font_tuple, fg_color, pady=(0, 8), wraplength=None):
            kw = dict(bg=BG_WHITE, fg=fg_color, font=font_tuple, anchor="w", justify=tk.LEFT)
            if wraplength:
                kw["wraplength"] = wraplength
            lbl = tk.Label(parent, text=text, **kw)
            lbl.pack(anchor=tk.W, fill=tk.X, pady=pady)
            return lbl

        def _tut_section(title_text, subtitle_text=None):
            """章节标题。"""
            tk.Frame(tut_inner, bg=BG_WHITE, height=8).pack(fill=tk.X)
            _tut_label(tut_inner, title_text, (FONT_FAMILY, 13, "bold"), TEXT_PRIMARY, pady=(16, 4))
            if subtitle_text:
                _tut_label(tut_inner, subtitle_text, (FONT_FAMILY, 9), TEXT_MUTED, pady=(0, 10))

        def _tut_steps(steps):
            """渲染带编号徽章的步骤卡片。"""
            for number, title, body in steps:
                step = tk.Frame(tut_inner, bg="#f7f8fa", padx=14, pady=12)
                step.pack(fill=tk.X, pady=(0, 10))
                badge_cv = tk.Canvas(step, bg="#f7f8fa", width=32, height=32, highlightthickness=0, bd=0)
                badge_cv.pack(side=tk.LEFT, padx=(0, 14))
                def make_badge_draw(cv, n):
                    def _draw(e=None):
                        cv.delete("all")
                        draw_rounded_rect(cv, 1, 1, 31, 31, 16, fill=self.colors["accent"], outline="")
                        cv.create_text(16, 16, text=n, fill="#ffffff", font=(FONT_FAMILY, 10, "bold"))
                    return _draw
                draw_badge = make_badge_draw(badge_cv, number)
                badge_cv.bind("<Configure>", lambda e, d=draw_badge: d())
                copy = tk.Frame(step, bg="#f7f8fa")
                copy.pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Label(copy, text=title, bg="#f7f8fa", fg=TEXT_PRIMARY,
                         font=(FONT_FAMILY, 10, "bold"), anchor="w", justify=tk.LEFT).pack(anchor=tk.W)
                tk.Label(copy, text=body, bg="#f7f8fa", fg=TEXT_MUTED,
                         font=(FONT_FAMILY, 9), anchor="w", justify=tk.LEFT, wraplength=560).pack(anchor=tk.W, pady=(3, 0))

        def _tut_bullet(items, color_dot="#1E90FF"):
            """渲染项目符号列表。每个 item 可以是 str 或 (title, body)。"""
            for it in items:
                row = tk.Frame(tut_inner, bg=BG_WHITE)
                row.pack(fill=tk.X, pady=(0, 4))
                tk.Label(row, text="•", bg=BG_WHITE, fg=color_dot,
                         font=(FONT_FAMILY, 10, "bold")).pack(side=tk.LEFT, padx=(4, 8))
                if isinstance(it, tuple):
                    title, body = it
                    text_full = f"{title}：{body}" if title else body
                else:
                    text_full = it
                tk.Label(row, text=text_full, bg=BG_WHITE, fg=TEXT_PRIMARY,
                         font=(FONT_FAMILY, 9), anchor="w", justify=tk.LEFT,
                         wraplength=560).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def _tut_code(text):
            """渲染代码/路径块。"""
            block = tk.Frame(tut_inner, bg="#1d2129", padx=12, pady=10)
            block.pack(fill=tk.X, pady=(0, 10))
            tk.Label(block, text=text, bg="#1d2129", fg="#e5e6eb",
                     font=("Consolas", 9), anchor="w", justify=tk.LEFT).pack(anchor=tk.W)

        # ===== 教程内容 =====
        _tut_label(tut_inner, "使用教程", (FONT_FAMILY, 15, "bold"), TEXT_PRIMARY, pady=(0, 4))
        _tut_label(tut_inner, "从初次配置到 Skill 自定义，完整指南", (FONT_FAMILY, 9), TEXT_MUTED, pady=(0, 12))

        # 第一章：快速上手
        _tut_section("一、快速上手（首次使用）", "按顺序完成这 6 步，即可开始自动回复")
        _tut_steps([
            ("1", "获取 Agnes API 密钥", "前往 Agnes 官网或控制台注册账号，创建并复制你的 API 密钥（sk- 开头）。Agnes 是提供大模型对话能力的服务，本软件通过它生成自然回复。"),
            ("2", "绑定 Agnes 密钥", "打开左侧菜单\"Agnes 设置\"，粘贴 API 密钥到对应输入框，确认模型（默认 agnes-2.0-flash）和 Base URL（默认 https://apihub.agnes-ai.com/v1），点击保存。可点\"测试连接\"验证密钥是否可用。"),
            ("3", "校准聊天区域", "打开\"校准发送\"页面。先点\"定位输入框\"，到聊天窗口点击聊天输入框；再点\"定位聊天框四角\"，依次点击聊天记录显示区域的四个角。校准是为了让软件准确识别对方消息和发送位置。"),
            ("4", "配置聊天对象", "在\"校准发送\"页面下方：① 选择对象分类（如领导、朋友）② 选择或添加具体名字 ③ 点击\"锁定对象\"。锁定后软件会自动加载该分类对应的 Skill，并切换到该联系人的独立记忆。"),
            ("5", "开启自动回复", "回到\"回复工作台\"：① 确认勾选\"Agnes 生成回复\" ② 首次使用建议勾选\"只预览，不发送\"先看效果 ③ 测试满意后取消预览，软件会真正发送。"),
            ("6", "连接聊天并运行", "点击左下角\"连接聊天\"按钮，确认状态显示已连接。再点击右上角\"开始\"按钮启动自动回复。软件会持续监听对方消息并自动回复。点\"停止\"可随时暂停。"),
        ])

        # 第二章：核心功能说明
        _tut_section("二、核心功能说明", "理解这些机制，用起来更顺手")
        _tut_bullet([
            ("只回复最新消息", "切换聊天对象后，软件会预扫描当前屏幕已有消息并标记为已处理，只回复切换后新出现的消息，不会回复历史记录。"),
            ("独立记忆", "每个聊天对象有独立的对话记忆（最近 30 条），切换对象时自动加载。记忆只用于辅助理解上下文，不会让 AI 主动回复旧话题。"),
            ("承诺备忘", "AI 生成回复后，会自动判断回复里是否包含承诺（如\"11点去吃饭\"\"明天给你发\"），有承诺就自动保存到\"承诺备忘\"菜单。也可以手动添加。"),
            ("预览模式", "勾选\"只预览，不发送\"后，软件会生成回复但不发送，仅显示在日志里。适合调试 Skill 效果。"),
            ("回复延迟", "软件会在 5-10 秒随机延迟后发送回复，模拟真人打字节奏，避免秒回显得机械。"),
        ])

        # 第三章：Skill 系统
        _tut_section("三、Skill 系统（话术风格）", "Skill 决定 AI 回复的语气和风格，可自定义")

        _tut_label(tut_inner, "什么是 Skill", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_bullet([
            "Skill 是一份 Markdown 格式的话术规范文件，告诉 AI 在和不同对象聊天时该用什么语气、遵循什么规则。",
            "软件内置了 6 个 Skill：reply-to-leader（领导）、chat-with-partner（对象）、chat-with-crush（暧昧对象）、chat-with-friends（朋友）、chat-with-strangers（路人）、wechat_reply_assistant（默认）。",
            "每个聊天对象分类关联一个 Skill，锁定对象时自动加载，不会互相污染。",
        ])

        _tut_label(tut_inner, "Skill 文件位置", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_label(tut_inner, "Skill 文件存放在 exe 同目录的 skills/ 文件夹下，每个 Skill 是一个子文件夹：",
                   (FONT_FAMILY, 9), TEXT_MUTED, pady=(0, 6))
        _tut_code("WeChatAutoReply.exe 同目录/\n├── skills/\n│   ├── reply-to-leader/\n│   │   └── SKILL.md\n│   ├── chat-with-friends/\n│   │   └── SKILL.md\n│   └── 你的新skill名/\n│       └── SKILL.md\n├── agnes_config.json\n└── ...")

        _tut_label(tut_inner, "SKILL.md 格式规范", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_label(tut_inner, "SKILL.md 必须用 UTF-8 编码保存，文件名固定为 SKILL.md，内容结构如下：",
                   (FONT_FAMILY, 9), TEXT_MUTED, pady=(0, 6))
        _tut_code("---\nname: skill英文名（与文件夹名一致）\ndescription: |\n  这个 skill 用来干嘛。\n  适用场景：xxx。\n  核心原则：xxx。\n  触发场景：对方语气/称呼/话题符合什么特征时用这个。\n---\n\n# 话术规范标题\n\n## 核心原则\n1. 规则一\n2. 规则二\n\n## 常见场景回复模板\n### 1. 场景一\n- \"回复示例1\"\n- \"回复示例2\"\n\n## 语气细节\n- 短句、口语化、不用书面语\n- 句末用\"的\"\"了\"，不用\"哦\"\"呢\"\n\n## 禁忌\n- 不做什么、不说什么")

        _tut_label(tut_inner, "添加新 Skill", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_bullet([
            "在 skills/ 目录下新建文件夹，名字用英文+连字符（如 chat-with-boss、reply-to-teacher）",
            "文件夹内创建 SKILL.md，按上面格式编写内容，保存为 UTF-8 编码",
            "重启 WeChatAutoReply.exe",
            "在\"Agnes 设置\"页面，把某个对象分类的 Skill 改成新加的（或新增分类时直接指定）",
            "锁定该分类的聊天对象，新 Skill 立即生效",
        ])

        _tut_label(tut_inner, "替换/修改已有 Skill", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_bullet([
            "直接编辑对应文件夹里的 SKILL.md 内容（如 skills/reply-to-leader/SKILL.md）",
            "保存后，在软件\"Agnes 设置\"页面点\"重载 Skill\"按钮，或重启 exe",
            "新内容立即应用于后续回复，已发送的回复不受影响",
        ])

        _tut_label(tut_inner, "删除 Skill", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_bullet([
            "直接删除对应的 skill 文件夹（如删除 skills/chat-with-crush/ 整个文件夹）",
            "重启 exe 后该 Skill 不再可选",
            "若已有分类仍指向已删除的 Skill，锁定对象时会自动回退到默认 Skill",
        ])

        _tut_label(tut_inner, "编写 Skill 的建议", (FONT_FAMILY, 10, "bold"), TEXT_PRIMARY, pady=(8, 2))
        _tut_bullet([
            "规则要具体：不要写\"自然回复\"，要写\"回复 15-45 字、短句、不用感叹号堆砌\"",
            "给回复模板：列出 3-5 个常见场景的标准回复，AI 会模仿",
            "明确禁忌：写清楚不能说什么（如不卖萌、不拍马屁、不越界）",
            "字数控制：SKILL.md 总长度建议不超过 6000 字，过长会截断",
            "单一职责：每个 Skill 只针对一种关系，不要混（如领导和暧昧对象绝不能共用）",
        ])

        # 第四章：承诺备忘
        _tut_section("四、承诺备忘", "记录承诺过的事情，自动提取")
        _tut_bullet([
            ("自动提取", "AI 生成回复后，后台会异步调用一次 LLM 判断回复里是否含承诺（如\"我11点准时到\"\"明天给你发\"）。有承诺就自动保存，联系人是当前锁定的对象。"),
            ("手动添加", "在\"承诺备忘\"页面，填写联系人、截止时间、承诺内容，点\"添加承诺\"。"),
            ("标记完成", "完成的事情点\"标记完成\"，会记录完成时间。可随时\"撤销完成\"。"),
            ("筛选查看", "右上角下拉框可切换\"未完成/全部/已完成\"。"),
            ("持久化", "承诺保存在 promises.json，重启软件不丢失。"),
        ])

        # 第五章：常见问题
        _tut_section("五、常见问题", "遇到问题先看这里")
        _tut_bullet([
            ("回复发不出去", "检查：① 是否锁定对象 ② 输入框位置是否校准 ③ 是否勾选\"只预览，不发送\" ④ 聊天窗口是否在前台"),
            ("回复语气不对", "检查\"Agnes 设置\"里该分类关联的 Skill 是否正确。可在设置页\"重载 Skill\"刷新。"),
            ("切换对象后回复历史消息", "已修复：切换时会预扫描屏幕消息标记为已处理。若仍出现，确认聊天记录框四角校准准确。"),
            ("OCR 识别不准", "确认聊天记录框四角校准范围准确包含所有消息。可在\"运行日志\"页查看识别结果。"),
            ("API 报错", "检查 API Key 是否正确、是否欠费。在\"Agnes 设置\"点\"测试连接\"验证。"),
            ("软件卡死", "本版本已修复主题对话框卡死问题。若仍卡死，可在任务管理器结束进程后重启。"),
        ])

        # 底部留白
        tk.Frame(tut_inner, bg=BG_WHITE, height=20).pack(fill=tk.X)

        log_card = Card(logs_tab)
        log_card.grid(row=0, column=0, sticky=tk.NSEW)
        tk.Label(log_card.body, text="运行日志", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "bold")).pack(anchor=tk.W, pady=(0, 4))
        self.log_box = make_text(log_card.body, 16)
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        tk.Label(log_card.body, text="首次使用：校准聊天框和输入框 -> 锁定对象 -> 测试发送 -> 再开启自动回复。",
                 bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(12, 0))

        self._show_page("reply")
        self._refresh_theme_colors()

    # ---------- 承诺备忘 ----------
    def _build_sponsor_page(self, parent):
        """构建赞赏支持页面（纯文字，可复制）。
        赞赏内容请编辑下方 SPONSOR_* 区域，重启软件生效。
        """
        # ===== 赞赏内容编辑区（你可以自由修改这里） =====
        SPONSOR_TITLE = "支持作者"
        SPONSOR_INTRO = "如果这个软件帮到了你，欢迎请作者喝杯咖啡 ☕"
        # 赞赏项列表：(标签, 可复制内容)
        SPONSOR_ITEMS = [
            ("BNB链USTD赞赏", "0x114dedcd39a5411fFCB5C97302e29999b7fc4050"),
            ("TRX链USTD赞赏", "TU9u89t3uDPtFvDSgXcQVDdN1BmpcnVhPg"),
            ("SOL链USTD赞赏", "BgE8ogciLA6h1zJWVZksUqYdATU7LrGoDETRxjvL7coj"),
            ("备注", "任意金额都是鼓励，感谢支持！"),
        ]
        # ===== 编辑区结束 =====

        # 居中容器
        center = tk.Frame(parent, bg=BG_MAIN)
        center.grid(row=0, column=0, sticky=tk.NSEW)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)

        card_wrap = tk.Frame(center, bg=BG_MAIN)
        card_wrap.grid(row=0, column=0)
        card = Card(card_wrap, padding=32)
        card.pack()
        body = card.body
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=0)

        # 标题
        tk.Label(body, text=SPONSOR_TITLE, bg=BG_WHITE, fg=TEXT_PRIMARY,
                 font=(FONT_FAMILY, 18, "bold")).grid(row=0, column=0, columnspan=3,
                                                       pady=(0, 8))
        # 简介
        tk.Label(body, text=SPONSOR_INTRO, bg=BG_WHITE, fg=TEXT_SECONDARY,
                 font=(FONT_FAMILY, 10), anchor="n", justify=tk.CENTER,
                 wraplength=420).grid(row=1, column=0, columnspan=3, pady=(0, 20))

        # 赞赏项：每项一个标签 + 可复制的只读 Entry + 复制按钮
        def _make_copy_handler(text_to_copy, btn):
            """生成复制回调：复制到剪贴板 + 按钮短暂反馈。"""
            def _handler():
                try:
                    self.clipboard_clear()
                    self.clipboard_append(text_to_copy)
                    self.update()
                    original_text = btn.text
                    btn.text = "已复制 ✓"
                    btn._draw()
                    self.after(1200, lambda: (setattr(btn, "text", original_text), btn._draw()))
                    self.show_toast("已复制到剪贴板", "success")
                except Exception as exc:
                    self.log(f"复制到剪贴板失败：{exc}")
                    self.show_toast("复制失败", "error")
            return _handler

        for idx, (label_text, value_text) in enumerate(SPONSOR_ITEMS):
            row = idx + 2
            tk.Label(body, text=label_text, bg=BG_WHITE, fg=TEXT_MUTED,
                     font=(FONT_FAMILY, 10, "bold"), anchor="e").grid(
                row=row, column=0, sticky=tk.E, padx=(0, 12), pady=(0, 12))
            entry_var = tk.StringVar(value=value_text)
            entry = tk.Entry(body, textvariable=entry_var, state="readonly",
                             bg=BG_WHITE, fg=TEXT_PRIMARY, readonlybackground=BG_WHITE,
                             font=(FONT_FAMILY, 10), bd=1, relief=tk.SOLID,
                             highlightthickness=1, highlightcolor=BORDER_INPUT_FOCUS,
                             highlightbackground=BORDER_INPUT, insertontime=0)
            entry.grid(row=row, column=1, sticky=tk.EW, pady=(0, 12), ipady=4)
            # 点击全选方便 Ctrl+C
            entry.bind("<Button-1>", lambda e, w=entry: (w.focus_set(), w.select_range(0, tk.END)))
            # 复制按钮（先创建占位 command，再绑定真实 handler）
            copy_btn = RoundedButton(
                body, text="复制", btn_type="secondary",
                command=lambda: None, width=64, height=30, font_size=FONT_SIZE_SMALL)
            copy_btn.command = _make_copy_handler(value_text, copy_btn)
            copy_btn.grid(row=row, column=2, padx=(8, 0), pady=(0, 12))

        # 复制提示
        tk.Label(body, text="点击文字框可全选，或点右侧复制按钮", bg=BG_WHITE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, 9)).grid(row=len(SPONSOR_ITEMS) + 2, column=0,
                                              columnspan=3, pady=(8, 0))

    def _build_promises_page(self, parent):
        """构建承诺备忘页面：顶部添加表单 + 下方列表。"""
        # 添加表单卡片
        add_card = Card(parent, padding=20)
        add_card.grid(row=0, column=0, sticky=tk.EW, pady=(0, 20))
        add_body = add_card.body
        add_body.columnconfigure(1, weight=1)

        tk.Label(add_body, text="新建承诺", bg=BG_WHITE, fg=TEXT_PRIMARY,
                 font=(FONT_FAMILY, FONT_SIZE_BASE + 1, "bold")).grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 12))

        tk.Label(add_body, text="联系人/对象", bg=BG_WHITE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=1, column=0, sticky=tk.W, padx=(0, 8))
        self.promise_contact_var = tk.StringVar()
        contact_entry = ModernEntry(add_body, textvariable=self.promise_contact_var, width=14, font_size=FONT_SIZE_BASE)
        contact_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 16))

        tk.Label(add_body, text="截止时间", bg=BG_WHITE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=1, column=2, sticky=tk.W, padx=(0, 8))
        self.promise_deadline_var = tk.StringVar()
        deadline_entry = ModernEntry(add_body, textvariable=self.promise_deadline_var, width=10, font_size=FONT_SIZE_BASE)
        deadline_entry.grid(row=1, column=3, sticky=tk.W, padx=(0, 16))

        tk.Label(add_body, text="承诺内容", bg=BG_WHITE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=2, column=0, sticky=tk.W, padx=(0, 8), pady=(10, 0))
        self.promise_content_var = tk.StringVar()
        content_entry = ModernEntry(add_body, textvariable=self.promise_content_var, font_size=FONT_SIZE_BASE)
        content_entry.grid(row=2, column=1, columnspan=3, sticky=tk.EW, padx=(0, 16), pady=(10, 0))

        RoundedButton(add_body, text="添加承诺", btn_type="primary", command=self._promise_add,
                      width=92, height=34, font_size=FONT_SIZE_BASE).grid(row=2, column=4, sticky=tk.W, padx=(0, 0), pady=(10, 0))

        tk.Label(add_body, text="示例：朋友 | 11:00 | 去吃饭；张总 | 12:00 | 修复好 bug", bg=BG_WHITE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, FONT_SIZE_SMALL)).grid(row=3, column=0, columnspan=6, sticky=tk.W, pady=(10, 0))

        # 列表卡片
        list_card = Card(parent, padding=20)
        list_card.grid(row=1, column=0, sticky=tk.NSEW)
        list_body = list_card.body
        list_body.columnconfigure(0, weight=1)
        list_body.rowconfigure(1, weight=1)

        header_row = tk.Frame(list_body, bg=BG_WHITE)
        header_row.grid(row=0, column=0, sticky=tk.EW, pady=(0, 12))
        tk.Label(header_row, text="承诺列表", bg=BG_WHITE, fg=TEXT_PRIMARY,
                 font=(FONT_FAMILY, FONT_SIZE_BASE + 1, "bold")).pack(side=tk.LEFT)
        self.promise_filter_var = tk.StringVar(value="未完成")
        filter_box = ttk.Combobox(header_row, textvariable=self.promise_filter_var,
                                  values=["未完成", "全部", "已完成"], state="readonly", width=8)
        filter_box.pack(side=tk.RIGHT)
        filter_box.bind("<<ComboboxSelected>>", lambda e: self._promise_refresh())

        # 列表容器（滚动）
        list_wrap = tk.Frame(list_body, bg=BG_WHITE)
        list_wrap.grid(row=1, column=0, sticky=tk.NSEW)
        list_wrap.columnconfigure(0, weight=1)

        self.promise_list_canvas = tk.Canvas(list_wrap, bg=BG_WHITE, highlightthickness=0, bd=0)
        self.promise_list_scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.promise_list_canvas.yview)
        self.promise_list_inner = tk.Frame(self.promise_list_canvas, bg=BG_WHITE)
        self.promise_list_inner.bind("<Configure>",
                                     lambda e: self.promise_list_canvas.configure(scrollregion=self.promise_list_canvas.bbox("all")))
        self.promise_list_canvas.create_window((0, 0), window=self.promise_list_inner, anchor="nw")
        self.promise_list_canvas.configure(yscrollcommand=self.promise_list_scroll.set)
        self.promise_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.promise_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.promise_list_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(True))
        self.promise_list_canvas.bind("<Leave>", lambda e: self._bind_mousewheel(False))
        self.promise_list_inner.columnconfigure(0, weight=1)

        # 空提示
        self.promise_empty_label = tk.Label(self.promise_list_inner, text="还没有承诺记录，添加一条吧。", bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, FONT_SIZE_BASE))
        self.promise_empty_label.grid(row=0, column=0, sticky=tk.W, pady=8)

        self._promise_row_index = 1
        self._promise_refresh()

    def _bind_mousewheel(self, bind):
        if bind:
            self.promise_list_canvas.bind_all("<MouseWheel>",
                                              lambda e: self.promise_list_canvas.yview_scroll(int(-e.delta / 120), "units"))
        else:
            self.promise_list_canvas.unbind_all("<MouseWheel>")

    def _promise_refresh(self):
        # 清空旧条目（保留空提示）
        for child in list(self.promise_list_inner.winfo_children()):
            if child is self.promise_empty_label:
                continue
            child.destroy()

        filt = self.promise_filter_var.get()
        all_promises = self.promises.all_promises(include_done=True)
        if filt == "未完成":
            shown = [p for p in all_promises if not p.get("done")]
        elif filt == "已完成":
            shown = [p for p in all_promises if p.get("done")]
        else:
            shown = all_promises

        # 倒序显示，最新在前
        shown = list(reversed(shown))

        if not shown:
            self.promise_empty_label.grid(row=0, column=0, sticky=tk.W, pady=8)
        else:
            self.promise_empty_label.grid_forget()

        for idx, p in enumerate(shown, start=1):
            self._promise_render_row(p, idx)

    def _promise_render_row(self, p, idx):
        row = tk.Frame(self.promise_list_inner, bg=BG_WHITE)
        row.grid(row=idx, column=0, sticky=tk.EW, pady=(0, 8))
        row.columnconfigure(1, weight=1)

        # 左侧状态色条
        done = bool(p.get("done"))
        status_color = "#22c55e" if done else "#f59e0b"
        tk.Frame(row, bg=status_color, width=4).grid(row=0, column=0, sticky=tk.NS)

        info = tk.Frame(row, bg=BG_WHITE)
        info.grid(row=0, column=1, sticky=tk.EW, padx=(10, 8))
        info.columnconfigure(0, weight=1)

        contact = p.get("contact", "")
        content = p.get("content", "")
        deadline = p.get("deadline", "")
        title_text = content
        if contact:
            title_text = f"[{contact}] {content}"
        if done:
            title_text = "✓ " + title_text
        title_lbl = tk.Label(info, text=title_text, bg=BG_WHITE, fg=TEXT_PRIMARY,
                             font=(FONT_FAMILY, FONT_SIZE_BASE), anchor="w", justify=tk.LEFT, wraplength=520)
        title_lbl.grid(row=0, column=0, sticky=tk.W)
        if done:
            title_lbl.configure(fg=TEXT_MUTED)

        meta_parts = []
        if deadline:
            meta_parts.append(f"截止 {deadline}")
        meta_parts.append("已创建 " + p.get("created_at", "")[:16])
        if done and p.get("done_at"):
            meta_parts.append("完成于 " + p.get("done_at", "")[:16])
        tk.Label(info, text="  ·  ".join(meta_parts), bg=BG_WHITE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, FONT_SIZE_SMALL), anchor="w", justify=tk.LEFT).grid(row=1, column=0, sticky=tk.W, pady=(2, 0))

        actions = tk.Frame(row, bg=BG_WHITE)
        actions.grid(row=0, column=2, sticky=tk.E, padx=(8, 0))
        toggle_text = "撤销完成" if done else "标记完成"
        RoundedButton(actions, text=toggle_text, btn_type="secondary",
                      command=lambda pid=p.get("id"): self._promise_toggle(pid),
                      width=72, height=28, font_size=FONT_SIZE_SMALL).pack(side=tk.LEFT, padx=(0, 6))
        RoundedButton(actions, text="删除", btn_type="secondary",
                      command=lambda pid=p.get("id"): self._promise_delete(pid),
                      width=48, height=28, font_size=FONT_SIZE_SMALL).pack(side=tk.LEFT)

    def _promise_add(self):
        contact = self.promise_contact_var.get().strip()
        content = self.promise_content_var.get().strip()
        deadline = self.promise_deadline_var.get().strip()
        if not content:
            messagebox.showwarning("提示", "请填写承诺内容", parent=self)
            return
        ok, msg = self.promises.add_promise(contact, content, deadline)
        if ok:
            self.promise_contact_var.set("")
            self.promise_content_var.set("")
            self.promise_deadline_var.set("")
            self._promise_refresh()
        else:
            messagebox.showwarning("提示", msg, parent=self)

    def _promise_toggle(self, pid):
        # 找到该项判断当前状态
        for p in self.promises.promises:
            if p.get("id") == pid:
                if p.get("done"):
                    self.promises.mark_undone(pid)
                else:
                    self.promises.mark_done(pid)
                break
        self._promise_refresh()

    def _promise_delete(self, pid):
        if not messagebox.askyesno("确认", "确定删除这条承诺吗？", parent=self):
            return
        self.promises.delete_promise(pid)
        self._promise_refresh()

    def _show_page(self, name):
        page = getattr(self, "pages", {}).get(name)
        if page is None:
            return
        titles = {
            "reply": ("回复工作台", "只回复最新收到的消息，记忆只做上下文"),
            "calibrate": ("校准发送", "锁定对象、校准输入框和聊天记录框"),
            "promises": ("承诺备忘", "记录对朋友、领导等承诺过的事情"),
            "settings": ("Agnes 设置", "配置模型、API Key 和本地 Skill"),
            "tutorial": ("使用教程", "首次使用请按步骤完成设置"),
            "logs": ("运行日志", "查看运行过程，日志会永久保存"),
            "sponsor": ("赞赏支持", "如果这个软件帮到了你，可以请作者喝杯咖啡"),
        }
        title, subtitle = titles.get(name, ("Agnes 聊天助手", ""))
        try:
            self.page_title_label.configure(text=title)
            self.page_subtitle_label.configure(text=subtitle)
        except Exception:
            pass
        page.tkraise()
        self._refresh_nav_colors(active=name)

    def _nav_hover(self, key, hovering):
        info = self.nav_items_info.get(key)
        if not info:
            return
        is_active = getattr(self, "_current_page", None) == key
        if is_active:
            return
        row, lbl, bar = info
        bg = HOVER_LIGHT if hovering else BG_SIDEBAR
        row.configure(bg=bg)
        lbl.configure(bg=bg, fg=TEXT_PRIMARY if hovering else TEXT_SECONDARY)
        bar.configure(bg=bg)

    def _refresh_nav_colors(self, active=None):
        if active is None:
            active = getattr(self, "_current_page", None)
        c = self.colors
        for key, (row, lbl, bar) in self.nav_items_info.items():
            is_active = key == active
            if is_active:
                bg = c["accent_soft"]
                row.configure(bg=bg)
                lbl.configure(bg=bg, fg=c["accent_hot"], font=(FONT_FAMILY, FONT_SIZE_NAV, "bold"))
                bar.configure(bg=c["accent"])
            else:
                row.configure(bg=BG_SIDEBAR)
                lbl.configure(bg=BG_SIDEBAR, fg=TEXT_SECONDARY, font=(FONT_FAMILY, FONT_SIZE_NAV, "normal"))
                bar.configure(bg=BG_SIDEBAR)
        self._current_page = active

    def apply_theme(self, color):
        ok, msg = self.theme.set_accent(color)
        if not ok:
            self.show_toast(msg, "warning")
            return False, msg
        self.colors.update(self.theme.palette())
        self._refresh_theme_colors()
        try:
            self.theme_color_var.set(self.theme.accent)
        except Exception:
            pass
        self.show_toast(f"主题色已切换：{self.theme.accent}", "success")
        self.log(f"主题色已切换：{self.theme.accent}")
        return True, msg

    def _show_theme_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("主题外观")
        dialog.configure(bg=BG_WHITE)
        dialog.geometry("400x440")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        content = tk.Frame(dialog, bg=BG_WHITE, padx=24, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        title_bar = tk.Frame(content, bg=BG_WHITE)
        title_bar.pack(fill=tk.X, pady=(0, 12))
        tk.Label(title_bar, text="主题外观", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 12, "bold")).pack(side=tk.LEFT)
        close_lbl = tk.Label(title_bar, text="×", bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 14, "bold"), cursor="hand2")
        close_lbl.pack(side=tk.RIGHT)
        close_lbl.bind("<Button-1>", lambda e: dialog.destroy())
        close_lbl.bind("<Enter>", lambda e: close_lbl.configure(fg=TEXT_PRIMARY))
        close_lbl.bind("<Leave>", lambda e: close_lbl.configure(fg=TEXT_MUTED))

        tk.Label(content, text="背景统一纯白，主题色用于按钮、选中态和强调元素", bg=BG_WHITE,
                 fg=TEXT_MUTED, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(0, 14))

        swatch_frame = tk.Frame(content, bg=BG_WHITE)
        swatch_frame.pack(fill=tk.X, pady=(0, 14))
        for i, (name, color) in enumerate(self.theme.PRESETS):
            r = i // 4
            cl = i % 4
            cell = tk.Frame(swatch_frame, bg=BG_WHITE, width=72, height=60)
            cell.grid(row=r, column=cl, padx=4, pady=4)
            cell.grid_propagate(False)
            scv = tk.Canvas(cell, bg=BG_WHITE, highlightthickness=0, bd=0, cursor="hand2")
            scv.place(x=10, y=4, width=52, height=40)
            def make_theme_swatch(c, cvs):
                def _draw(e=None):
                    cvs.delete("all")
                    draw_rounded_rect(cvs, 2, 2, 50, 38, 8, fill=c, outline="")
                def _cmd(e=None):
                    self.apply_theme(c)
                return _draw, _cmd
            dfn, cfn = make_theme_swatch(color, scv)
            scv.bind("<Configure>", lambda e, d=dfn: d())
            scv.bind("<Button-1>", cfn)
            tk.Label(cell, text=name, bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 8)).place(x=0, y=44, width=72, height=14)

        custom_frame = tk.Frame(content, bg=BG_WHITE)
        custom_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(custom_frame, text="自定义 HEX", bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).pack(side=tk.LEFT, padx=(0, 8))
        hex_var = tk.StringVar(value=self.theme.accent)
        hex_entry = ModernEntry(custom_frame, textvariable=hex_var)
        hex_entry.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        preview = tk.Canvas(custom_frame, bg=BG_WHITE, width=28, height=28, highlightthickness=1, highlightbackground=BORDER_INPUT, bd=0)
        preview.pack(side=tk.LEFT, padx=(0, 8))
        def draw_preview(e=None):
            preview.delete("all")
            v = hex_var.get().strip()
            if re.match(r"^#?[0-9A-Fa-f]{6}$", v):
                c = v if v.startswith("#") else "#" + v
                draw_rounded_rect(preview, 2, 2, 26, 26, 6, fill=c, outline="")
        hex_var.trace_add("write", lambda *a: draw_preview())
        preview.bind("<Configure>", draw_preview)

        def apply_custom():
            ok, msg = self.apply_theme(hex_var.get())
            if ok:
                draw_preview()
            else:
                self.show_toast(msg, "warning")

        btn_row = tk.Frame(content, bg=BG_WHITE)
        btn_row.pack(fill=tk.X, pady=(16, 0))
        RoundedButton(btn_row, text="关闭", btn_type="secondary", command=dialog.destroy, width=72, height=34).pack(side=tk.RIGHT)
        RoundedButton(btn_row, text="应用", btn_type="primary", command=apply_custom, width=72, height=34).pack(side=tk.RIGHT, padx=(0, 8))

        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        pw = self.winfo_width()
        ph = self.winfo_height()
        px = self.winfo_rootx()
        py = self.winfo_rooty()
        dialog.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        draw_preview()

    def _add_category_dialog(self):
        dlg = ModernDialog(self, title="添加对象分类", message=None, input_prompt="分类名（如：领导/客户/家人）", initialvalue="",
                          buttons=[("确定", "ok", "primary"), ("取消", "cancel", "secondary")])
        self.wait_window(dlg)
        if dlg.result != "ok":
            return
        name = (getattr(dlg, 'input_value', '') or "").strip()
        if not name:
            self.show_toast("分类名不能为空", "warning")
            return
        ok, msg = self.contacts.add_category(name, "")
        if ok:
            self.category_combo.configure_values(self.contacts.category_names())
            self.contact_category_var.set(name)
            self.on_category_changed()
            self.log(msg)
            self.show_toast(msg, "success")
        else:
            self.show_toast(msg, "warning")

    def _manage_contacts_dialog(self):
        category = self.contact_category_var.get()
        if not category:
            self.show_toast("请先选择一个分类", "warning")
            return
        dialog = tk.Toplevel(self)
        dialog.overrideredirect(True)
        dialog.configure(bg=BG_MAIN)
        dialog.geometry("440x460")
        dialog.transient(self)
        dialog.grab_set()

        cv = tk.Canvas(dialog, bg=BG_MAIN, highlightthickness=0, bd=0)
        cv.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        frame = tk.Frame(cv, bg=BG_WHITE)
        win_id = None

        def on_configure(event):
            nonlocal win_id
            cv.delete("card")
            w = event.width
            h = event.height
            draw_rounded_rect(cv, 16, 16, w - 16, h - 16, 12, fill=BG_WHITE, outline=BORDER_CARD, tags="card")
            cv.tag_lower("card")
            if win_id is None:
                win_id = cv.create_window(w // 2, h // 2, window=frame, anchor=tk.CENTER)
            else:
                cv.coords(win_id, w // 2, h // 2)
            cv.itemconfig(win_id, width=w - 32, height=h - 32)
        cv.bind("<Configure>", on_configure)

        content = tk.Frame(frame, bg=BG_WHITE, padx=24, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        title_bar = tk.Frame(content, bg=BG_WHITE)
        title_bar.pack(fill=tk.X, pady=(0, 12))
        tk.Label(title_bar, text=f"管理名字 - {category}", bg=BG_WHITE, fg=TEXT_PRIMARY, font=(FONT_FAMILY, 12, "bold")).pack(side=tk.LEFT)
        close_lbl = tk.Label(title_bar, text="×", bg=BG_WHITE, fg=TEXT_MUTED, font=(FONT_FAMILY, 14, "bold"), cursor="hand2")
        close_lbl.pack(side=tk.RIGHT)
        close_lbl.bind("<Button-1>", lambda e: dialog.destroy())

        drag_data = {"x": 0, "y": 0}
        def start_drag(e):
            drag_data["x"] = e.x_root - dialog.winfo_x()
            drag_data["y"] = e.y_root - dialog.winfo_y()
        def on_drag(e):
            dialog.geometry(f"+{e.x_root - drag_data['x']}+{e.y_root - drag_data['y']}")
        title_bar.bind("<ButtonPress-1>", start_drag)
        title_bar.bind("<B1-Motion>", on_drag)

        tk.Label(content, text=f"分类：{category}    Skill：{self.contacts.get_category_skill(category) or '未设置'}",
                 bg=BG_WHITE, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9)).pack(anchor=tk.W, pady=(0, 12))

        list_frame = tk.Frame(content, bg=BG_WHITE, highlightthickness=1, highlightbackground=BORDER_INPUT)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        lb = tk.Listbox(list_frame, height=12, font=(FONT_FAMILY, 10), bd=0, bg=BG_WHITE, fg=TEXT_PRIMARY,
                        selectbackground="#f2f3f5", selectforeground=TEXT_PRIMARY, activestyle="none", highlightthickness=0)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_frame = tk.Frame(list_frame, bg=BG_WHITE, width=12)
        sb_frame.pack(side=tk.RIGHT, fill=tk.Y)
        sb = ttk.Scrollbar(sb_frame, orient=tk.VERTICAL, command=lb.yview)
        sb.pack(fill=tk.Y, padx=2)
        lb.configure(yscrollcommand=sb.set)

        def refresh_list():
            lb.delete(0, tk.END)
            for n in self.contacts.contacts_of(category):
                lb.insert(tk.END, n)

        def on_add():
            name = self.ask_string("添加名字", f"在 [{category}] 下添加名字：", parent=dialog)
            if name is None:
                return
            ok, msg = self.contacts.add_contact(category, name)
            if ok:
                self.log(msg)
                refresh_list()
                self.on_category_changed()
                self.show_toast(msg, "success")
            else:
                self.show_toast(msg, "warning")

        def on_delete():
            sel = lb.curselection()
            if not sel:
                self.show_toast("请先选中要删除的名字", "warning")
                return
            name = lb.get(sel[0])
            if not self.ask_ok_cancel("确认删除", f"删除 [{category}] 下的 [{name}]？\n该对象的聊天记忆也会被清除。", parent=dialog):
                return
            ok, msg = self.contacts.delete_contact(category, name)
            if ok:
                self.memory.delete_contact_memory(self._contact_key(category, name))
                self.log(msg + "（含聊天记忆）")
                refresh_list()
                self.on_category_changed()
                self.show_toast(msg, "success")
            else:
                self.show_toast(msg, "warning")

        def on_rename_category():
            new = self.ask_string("重命名分类", f"把分类 [{category}] 改名为：", initialvalue=category, parent=dialog)
            if new is None or new.strip() == category:
                return
            ok, msg = self.contacts.rename_category(category, new.strip())
            if ok:
                self.log(msg)
                dialog.destroy()
                self.show_toast(msg, "success")
                self._manage_contacts_dialog()
            else:
                self.show_toast(msg, "warning")

        def on_delete_category():
            if not self.ask_ok_cancel("确认删除", f"删除整个分类 [{category}]？\n该分类下所有名字和聊天记忆都会被清除。", parent=dialog):
                return
            for n in self.contacts.contacts_of(category):
                self.memory.delete_contact_memory(self._contact_key(category, n))
            ok, msg = self.contacts.delete_category(category)
            if ok:
                self.log(msg + "（含所有名字和聊天记忆）")
                self.category_combo.configure_values(self.contacts.category_names())
                cats = self.contacts.category_names()
                if cats:
                    self.contact_category_var.set(cats[0])
                else:
                    self.contact_category_var.set("")
                self.on_category_changed()
                dialog.destroy()
                self.show_toast(msg, "success")
            else:
                self.show_toast(msg, "warning")

        btn_row = tk.Frame(content, bg=BG_WHITE)
        btn_row.pack(fill=tk.X)
        RoundedButton(btn_row, text="添加名字", btn_type="primary", command=on_add, width=80).pack(side=tk.LEFT)
        RoundedButton(btn_row, text="删除名字", btn_type="secondary", command=on_delete, width=80).pack(side=tk.LEFT, padx=8)
        RoundedButton(btn_row, text="重命名分类", btn_type="secondary", command=on_rename_category, width=92).pack(side=tk.LEFT)
        RoundedButton(btn_row, text="删除分类", btn_type="danger", command=on_delete_category, width=80).pack(side=tk.RIGHT)

        refresh_list()

        def center_dlg():
            dialog.update_idletasks()
            w = dialog.winfo_width()
            h = dialog.winfo_height()
            pw = self.winfo_width()
            ph = self.winfo_height()
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            dialog.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        self.after(50, center_dlg)

    def _add_contact_dialog(self):
        category = self.contact_category_var.get()
        if not category:
            self.show_toast("请先选择一个分类", "warning")
            return
        name = self.ask_string("添加名字", f"在 [{category}] 下添加名字：")
        if name is None:
            return
        ok, msg = self.contacts.add_contact(category, name)
        if ok:
            self.log(msg)
            self.on_category_changed()
            self.contact_name_var.set(name.strip())
            self.show_toast(msg, "success")
        else:
            self.show_toast(msg, "warning")

    def _delete_contact_dialog(self):
        category = self.contact_category_var.get()
        name = self.contact_name_var.get()
        if not category or not name:
            self.show_toast("请先选择要删除的分类和名字", "warning")
            return
        if not self.ask_ok_cancel("确认删除", f"删除 [{category}] 下的 [{name}]？\n该对象的聊天记忆也会被清除。"):
            return
        ok, msg = self.contacts.delete_contact(category, name)
        if ok:
            self.memory.delete_contact_memory(self._contact_key(category, name))
            self.log(msg + "（含聊天记忆）")
            self.on_category_changed()
            self.show_toast(msg, "success")
        else:
            self.show_toast(msg, "warning")

    def _save_association(self):
        category = self.contact_category_var.get()
        if not category:
            self.show_toast("请先选择一个分类", "warning")
            return
        skill = self.contact_skill_var.get().strip()
        ok, msg = self.contacts.set_category_skill(category, skill)
        if ok:
            self.log(msg)
            self.show_toast(msg, "success")
        else:
            self.show_toast(msg, "warning")

    @staticmethod
    def _contact_key(category, name):
        import re as _re
        raw = f"{category}::{name}"
        return _re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]", "_", raw)

    def _lock_target(self):
        try:
            if self.wechat is None:
                self.connect_wechat()
            if self.wechat is None:
                return
            category = self.contact_category_var.get().strip()
            name = self.contact_name_var.get().strip()
            if not category:
                self.show_toast("请先选择对象分类", "warning")
                return
            if not name:
                self.show_toast(f"请先在 [{category}] 下添加并选择具体名字", "warning")
                return
            note = f"{category} - {name}"
            self.target_note_var.set(note)
            self.memory.switch_contact(self._contact_key(category, name))
            self.chat_context = list(self.memory.context[-30:])
            self._apply_active_skill(self.contacts.get_category_skill(category))
            win = self.wechat.ensure_window()
            title = win.window_text() or "聊天窗口"
            self.target_locked = True
            self.has_sent_in_current_chat = False
            self.last_message = ""
            self.last_skipped_target = ""
            self.last_incoming_fingerprint = None
            # 预扫描当前聊天窗口的已有消息，全部标记为已处理，避免切换对象后回复历史消息
            self._mark_existing_messages_as_processed()
            skill_name = self.contacts.get_category_skill(category) or "默认"
            self.locked_target_var.set(f"已锁定：{note}    Skill：{skill_name}    窗口：{title}")
            self.log(f"已锁定发送目标：{note}，使用 Skill：{skill_name}（窗口：{title}）")
            self.show_toast(f"已锁定：{note}", "success")
        except Exception as exc:
            self.log(f"锁定目标失败：{exc}")
            self.show_toast(f"锁定目标失败：{exc}", "error")

    def _apply_active_skill(self, skill_name):
        if not skill_name:
            self.agnes_config.active_skill_hint = ""
            self.agnes_config.active_skill = ""
            return
        hint = (
            f"\n\n【重要】当前聊天对象属于「{skill_name}」场景。"
            f"请严格参考 Skill: {skill_name} 的话术风格回复，忽略其他已安装 Skill 的风格冲突。"
            f"如果 {skill_name} 没有覆盖当前场景，就按通用自然风格回复，不要套用其他 Skill 的人设。"
        )
        self.agnes_config.active_skill_hint = hint
        self.agnes_config.active_skill = skill_name

    def _unlock_target(self):
        self.target_locked = False
        self.locked_target_var.set("未锁定，禁止自动发送")
        self.log("已解除发送目标锁定。")
        self.show_toast("已解除锁定", "info")

    def _load_logo_image(self, size):
        if Image is None or ImageTk is None or not LOGO_FILE.exists():
            return None
        try:
            image = Image.open(LOGO_FILE).convert("RGBA")
            image.thumbnail((size, size), Image.LANCZOS)
            canvas_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            x = (size - image.width) // 2
            y = (size - image.height) // 2
            canvas_img.alpha_composite(image, (x, y))
            photo = ImageTk.PhotoImage(canvas_img)
            try:
                self.iconphoto(True, photo)
            except Exception:
                pass
            return photo
        except Exception:
            return None

    def _setup_ttk_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=BG_WHITE, background=BG_WHITE,
                        foreground=TEXT_PRIMARY, bordercolor=BORDER_INPUT,
                        lightcolor=BORDER_INPUT, darkcolor=BORDER_INPUT,
                        arrowcolor=TEXT_MUTED, focuscolor=BORDER_INPUT_FOCUS,
                        padding=(8, 6))
        style.map("TCombobox",
                  fieldbackground=[("readonly", BG_WHITE)],
                  foreground=[("readonly", TEXT_PRIMARY)],
                  bordercolor=[("focus", BORDER_INPUT_FOCUS)])

    def _apply_window_effects(self):
        pass

    def connect_wechat(self):
        try:
            self.wechat = WeChatAutomation()
            title = self.wechat.connect()
            self.status_text.set(f"已连接：{title}")
            self.log(f"已连接聊天窗口：{title}")
            self.show_toast(f"已连接聊天：{title}", "success")
        except Exception as exc:
            self.wechat = None
            self.status_text.set("连接失败")
            self.log(f"连接失败：{exc}")
            self.show_toast(f"连接失败：{exc}", "error")

    def reload_rules(self):
        try:
            self.rulebook.load()
            self.agnes_config.load()
            self.use_agnes.set(self.agnes_config.enabled)
            self.api_key_var.set(self.agnes_config.api_key)
            self.base_url_var.set(self.agnes_config.base_url)
            self.model_var.set(self.agnes_config.model)
            self.skills_text.set(self._skills_summary())
            self.input_position_var.set(self._input_position_summary())
            self.chat_box_var.set(self._chat_box_summary())
            self.incoming_side_var.set(self.agnes_config.incoming_side)
            self.log("规则已重新加载。")
            self.show_toast("规则已重新加载", "success")
        except Exception as exc:
            self.log(f"规则错误：{exc}")
            self.show_toast(f"规则错误：{exc}", "error")

    def save_incoming_side(self):
        self.agnes_config.incoming_side = self.incoming_side_var.get()
        self.agnes_config.save()
        self.last_incoming_fingerprint = None
        side = "左侧" if self.agnes_config.incoming_side == "left" else "右侧"
        self.log(f"已设置对方消息位置：{side}")

    def on_category_changed(self, event=None):
        category = self.contact_category_var.get()
        names = self.contacts.contacts_of(category) if category else []
        self.name_combo.configure_values(names)
        if names:
            self.contact_name_var.set(names[0])
        else:
            self.contact_name_var.set("")
        skill = self.contacts.get_category_skill(category) if category else ""
        self.contact_skill_var.set(skill)
        self.skill_combo.configure_values(self.skills.installed_skills())

    def save_agnes_config(self):
        try:
            self.agnes_config.enabled = self.use_agnes.get()
            self.agnes_config.base_url = self.base_url_var.get().strip().rstrip("/")
            self.agnes_config.model = self.model_var.get().strip()
            self.agnes_config.api_key = self.api_key_var.get().strip()
            self.agnes_config.save()
            self.log(f"Agnes 配置已保存：{self.agnes_config.model}")
            self.show_toast("Agnes 配置已保存", "success")
        except Exception as exc:
            self.log(f"保存失败：{exc}")
            self.show_toast(f"保存失败：{exc}", "error")

    def capture_input_position(self):
        try:
            x, y = get_cursor_position()
            self.agnes_config.input_click_x = x
            self.agnes_config.input_click_y = y
            self.agnes_config.save()
            self.input_position_var.set(self._input_position_summary())
            self.log(f"已保存聊天输入框点击位置：({x}, {y})")
            self.show_toast(f"输入框位置已保存：({x}, {y})", "success")
        except Exception as exc:
            self.log(f"保存输入框位置失败：{exc}")
            self.show_toast(f"保存输入框位置失败：{exc}", "error")

    def countdown_capture_input_position(self):
        def run():
            try:
                for remaining in (3, 2, 1):
                    self.events.put(
                        (
                            "log",
                            f"校准倒计时 {remaining} 秒：请把鼠标移动到聊天输入框里面，不要点击也可以。",
                        )
                    )
                    time.sleep(1)
                x, y = get_cursor_position()
                self.events.put(("capture_position", (x, y)))
            except Exception as exc:
                self.events.put(("log", f"校准输入框位置失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def capture_chat_box_corner(self, corner):
        try:
            x, y = get_cursor_position()
            self._save_chat_box_corner(corner, x, y)
        except Exception as exc:
            self.log(f"记录聊天框角点失败：{exc}")

    def countdown_capture_chat_box_corner(self):
        next_corner = "tl"
        if self.agnes_config.chat_box_x1 is not None and self.agnes_config.chat_box_y1 is not None:
            next_corner = "br"

        def run():
            try:
                label = "左上角" if next_corner == "tl" else "右下角"
                for remaining in (3, 2, 1):
                    self.events.put(
                        (
                            "log",
                            f"聊天框{label}校准倒计时 {remaining} 秒：请把鼠标移动到聊天记录区域{label}。",
                        )
                    )
                    time.sleep(1)
                x, y = get_cursor_position()
                self.events.put(("capture_chat_corner", (next_corner, x, y)))
            except Exception as exc:
                self.events.put(("log", f"聊天框角点校准失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def capture_chat_box_by_drag(self):
        self.log("请拖拽框选聊天记录区域，松开鼠标保存；按 Esc 取消。")
        overlay = tk.Toplevel(self)
        overlay.title("框选聊天记录区域")
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.28)
        overlay.configure(bg="#000000")
        overlay.focus_force()

        canvas = tk.Canvas(overlay, bg="#000000", highlightthickness=0, cursor="crosshair")
        canvas.pack(fill=tk.BOTH, expand=True)
        hint = canvas.create_text(
            28,
            28,
            anchor=tk.NW,
            fill="#ffffff",
            font=(FONT_FAMILY, 18, "bold"),
            text="按住鼠标拖出聊天记录框，松开保存；Esc 取消",
        )
        state = {"start": None, "rect": None}

        def on_press(event):
            state["start"] = (event.x_root, event.y_root)
            if state["rect"] is not None:
                canvas.delete(state["rect"])
            state["rect"] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#21b36b", width=3)

        def on_drag(event):
            if not state["start"] or state["rect"] is None:
                return
            x1, y1 = state["start"]
            canvas.coords(
                state["rect"],
                x1 - overlay.winfo_rootx(),
                y1 - overlay.winfo_rooty(),
                event.x_root - overlay.winfo_rootx(),
                event.y_root - overlay.winfo_rooty(),
            )

        def on_release(event):
            if not state["start"]:
                overlay.destroy()
                return
            x1, y1 = state["start"]
            x2, y2 = event.x_root, event.y_root
            overlay.destroy()
            if abs(x2 - x1) < 40 or abs(y2 - y1) < 40:
                self.log("框选区域太小，已取消。")
                return
            self._save_chat_box_region(x1, y1, x2, y2)

        def cancel(_event=None):
            overlay.destroy()
            self.log("已取消框选聊天记录框。")

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        overlay.bind("<Escape>", cancel)
        canvas.tag_raise(hint)

    def _save_chat_box_corner(self, corner, x, y):
        if corner == "tl":
            self.agnes_config.chat_box_x1 = int(x)
            self.agnes_config.chat_box_y1 = int(y)
            name = "左上角"
        else:
            self.agnes_config.chat_box_x2 = int(x)
            self.agnes_config.chat_box_y2 = int(y)
            name = "右下角"
        self._normalize_chat_box()
        self.agnes_config.save()
        self.last_incoming_fingerprint = None
        self.chat_box_var.set(self._chat_box_summary())
        self.log(f"已记录聊天记录框{name}：({int(x)}, {int(y)})")
        self.show_toast(f"聊天框{name}已记录", "success")

    def _save_chat_box_region(self, x1, y1, x2, y2):
        self.agnes_config.chat_box_x1 = int(min(x1, x2))
        self.agnes_config.chat_box_y1 = int(min(y1, y2))
        self.agnes_config.chat_box_x2 = int(max(x1, x2))
        self.agnes_config.chat_box_y2 = int(max(y1, y2))
        self._normalize_chat_box()
        self.agnes_config.save()
        self.last_incoming_fingerprint = None
        self.chat_box_var.set(self._chat_box_summary())
        self.log(f"已框选聊天记录框：{self._chat_box_summary()}")
        self.show_toast("聊天记录框已保存", "success")

    def test_agnes(self):
        self.save_agnes_config()

        def run():
            try:
                reply = self.agnes.chat("请用一句话回复：聊天自动回复已接入 Agnes。")
                self.events.put(("log", f"Agnes 测试成功：{reply}"))
                self.events.put(("toast", ("Agnes 测试成功", "success")))
            except Exception as exc:
                self.events.put(("log", f"Agnes 测试失败：{exc}"))
                self.events.put(("toast", (f"Agnes 测试失败：{exc}", "error")))

        threading.Thread(target=run, daemon=True).start()

    def start(self):
        if self.worker and self.worker.is_alive():
            self.log("自动回复已经在运行。")
            self.show_toast("自动回复已在运行", "warning")
            return
        if self.wechat is None:
            self.connect_wechat()
            if self.wechat is None:
                return
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        self.status_text.set("运行中")
        self.run_state_var.set("运行中")
        self.delay_state_var.set(f"延迟：{REPLY_DELAY_MIN_SECONDS}-{REPLY_DELAY_MAX_SECONDS} 秒随机")
        self.last_action_var.set("最近：正在监听新消息")
        self.log("开始监听当前聊天。")
        self.log("自动模式只使用本地截图 + RapidOCR：只识别我方最后一条下方的对方新消息，确认后才请求 Agnes。")
        self.log("请确保本应用、资源管理器或其他窗口不要遮挡已校准的聊天记录框。")
        self.show_toast("已开始监听", "success")

    def stop(self):
        self.stop_event.set()
        self.status_text.set("已停止")
        self.run_state_var.set("已停止")
        self.last_action_var.set("最近：已停止")
        self.log("已停止。")
        self.show_toast("已停止", "info")

    def _diagnose_controls(self):
        try:
            if self.wechat is None:
                self.connect_wechat()
            dump = self.wechat.diagnostic_dump()
            dump_path = APP_DIR / "wechat_controls_dump.txt"
            dump_path.write_text(dump, encoding="utf-8")
            self.log(f"诊断信息已保存：{dump_path}")
            self.show_toast(f"诊断信息已保存：{dump_path.name}", "success")
        except Exception as exc:
            self.log(f"诊断失败：{exc}")
            self.show_toast(f"诊断失败：{exc}", "error")

    def peek_latest_message(self):
        try:
            if self.wechat is None:
                self.connect_wechat()
            if self.wechat is None:
                return
            region = self._chat_box_region()
            messages = self.wechat.visible_messages(region=region, incoming_side=self.agnes_config.incoming_side)
            latest = self.wechat.latest_message(region=region, incoming_side=self.agnes_config.incoming_side)
            self.log(f"可见候选消息数量：{len(messages)}")
            if region:
                side = "左侧" if self.agnes_config.incoming_side == "left" else "右侧"
                self.log(f"已按聊天记录框过滤：{region}，只看对方消息{side}")
            else:
                self.log("未校准聊天记录框：当前仍会读取整个聊天窗口文本。")
            if messages:
                preview = " | ".join(messages[-5:])
                self.log(f"最近候选：{preview}")
            self.log(f"当前识别最新消息：{latest or '未识别到'}")
        except Exception as exc:
            self.log(f"读取最新消息失败：{exc}")

    def _test_send(self):
        try:
            if self.wechat is None:
                self.connect_wechat()
            if self.wechat is None:
                return
            text = "自动回复测试"
            if self.dry_run.get():
                self.log(f"测试发送预览：{text}（当前勾选了只预览，不会真正发送）")
                self.show_toast(f"预览：{text}（不会发送）", "info")
                return
            if not self.target_locked:
                self.log("测试发送已拦截：未锁定当前聊天对象。")
                self.show_toast("未锁定当前聊天对象", "warning")
                return
            if not self._has_input_position():
                self.log("测试发送已拦截：请先校准聊天输入框位置。")
                self.show_toast("请先校准聊天输入框位置", "warning")
                return
            self.log(f"测试发送对象：{self.target_note_var.get().strip()}")
            paste_text_to_position(text, self.agnes_config.input_click_x, self.agnes_config.input_click_y)
            self.log(f"测试发送完成：{text}")
            self.show_toast("测试发送完成", "success")
        except Exception as exc:
            self.log(f"测试发送失败：{exc}")
            self.show_toast(f"测试发送失败：{exc}", "error")

    def _test_send_delayed(self):
        self._countdown_send_text("自动回复测试", "测试发送")

    def load_message_from_clipboard(self):
        try:
            text = pyperclip.paste() if pyperclip else ""
            self.manual_message_box.delete("1.0", tk.END)
            self.manual_message_box.insert(tk.END, text)
            if text.strip():
                self._add_context("对方", text.strip())
            self.log("已从剪贴板读取消息。")
        except Exception as exc:
            self.log(f"读取剪贴板失败：{exc}")

    def generate_manual_reply(self):
        message = self.manual_message_box.get("1.0", tk.END).strip()
        if not message:
            self.log("请先输入或粘贴对方消息。")
            self.show_toast("请先输入或粘贴对方消息", "warning")
            return

        def run():
            try:
                reply = self.make_reply(message)
                target = self._target_from_message_block(message)
                self._add_context("对方", message)
                self._add_context("我", reply)
                if target:
                    self.memory.remember_replied_target(target)
                self.events.put(("manual_reply", reply))
                self.events.put(("log", "已生成回复建议。"))
                # 异步提取回复中的承诺，保存到承诺备忘
                contact = self.target_note_var.get().strip()
                self._extract_and_save_promise_async(reply, message, contact)
            except Exception as exc:
                self.events.put(("log", f"生成回复建议失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def generate_reply_from_screenshot(self):
        region = self._chat_box_region()
        if not region:
            self.log("请先校准聊天记录框，再截图识别。")
            self.show_toast("请先校准聊天记录框", "warning")
            return

        def run():
            try:
                image_data_url = screenshot_region_as_data_url(region)
                prompt = (
                    "请从这张聊天记录截图中只识别对方那一侧最底部最新的 1 到 3 条消息，"
                    f"对方消息在聊天框的{self._incoming_side_name()}，我自己发出的消息在另一侧。"
                    "只允许根据这些最底部的新消息生成回复；不要回复更上面的旧消息。"
                    "如果对方那一侧底部没有新消息，或最新可见消息是我自己发的，不要回复，输出空字符串。"
                    "结合上下文和已安装 Skill，生成一条我可以直接发出的中文回复。"
                    "只输出回复内容，不要输出识别过程。"
                )
                reply = self.agnes.chat_with_image(prompt, image_data_url, context=self.chat_context)
                self._add_context("我", reply)
                self.events.put(("manual_reply", reply))
                self.events.put(("log", "已通过截图识别生成回复建议。"))
            except Exception as exc:
                self.events.put(("log", f"截图识别生成回复失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def test_local_ocr(self):
        region = self._chat_box_region()
        if not region:
            self.log("请先校准聊天记录框，再测试 OCR。")
            self.show_toast("请先校准聊天记录框", "warning")
            return

        def run():
            try:
                lines, engine_name = local_ocr_incoming_below(region, self.agnes_config.incoming_side)
                text = "\n".join(lines).strip()
                if text:
                    self.events.put(("manual_message", text))
                    self.events.put(("log", f"OCR测试成功（{engine_name}）：{text}"))
                else:
                    self.events.put(("log", f"OCR测试未识别到新消息：{engine_name}"))
                self.events.put(("log", f"OCR调试图已保存：{DEBUG_DIR / 'last_ocr_crop.png'}"))
            except Exception as exc:
                self.events.put(("log", f"OCR测试失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def copy_manual_reply(self):
        try:
            reply = self.manual_reply_box.get("1.0", tk.END).strip()
            if not reply:
                self.log("没有可复制的建议回复。")
                return
            pyperclip.copy(reply)
            self.log("建议回复已复制到剪贴板。")
            self.show_toast("已复制到剪贴板", "success")
        except Exception as exc:
            self.log(f"复制失败：{exc}")

    def countdown_send_manual_reply(self):
        reply = self.manual_reply_box.get("1.0", tk.END).strip()
        if not reply:
            self.log("没有可发送的建议回复。")
            self.show_toast("没有可发送的建议回复", "warning")
            return
        if self._has_input_position():
            self._send_text_to_saved_position(reply, "建议回复")
        else:
            self._countdown_send_text(reply, "建议回复")

    def _send_text_to_saved_position(self, text: str, label: str):
        def run():
            try:
                x = self.agnes_config.input_click_x
                y = self.agnes_config.input_click_y
                self.events.put(("log", f"{label}将点击已校准输入框位置 ({x}, {y}) 后发送。"))
                paste_text_to_position(text, x, y, press_enter=True)
                self._remember_self_reply(text)
                self.events.put(("log", f"{label}已发送。"))
            except Exception as exc:
                self.events.put(("log", f"{label}发送失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def _countdown_send_text(self, text: str, label: str):
        def run():
            try:
                for remaining in (3, 2, 1):
                    self.events.put(
                        (
                            "log",
                            f"{label}倒计时 {remaining} 秒：请立刻点击聊天输入框，让光标停在要发送的位置。",
                        )
                    )
                    time.sleep(1)
                paste_text_to_current_input(text, press_enter=True)
                self._remember_self_reply(text)
                self.events.put(("log", f"{label}已发送到当前输入框。"))
            except Exception as exc:
                self.events.put(("log", f"{label}发送失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def _loop(self):
        while not self.stop_event.is_set():
            try:
                region = self._chat_box_region()
                message, target_message = self._latest_incoming_message_block(region)
                skipped_known_message = False
                if target_message and self._should_skip_incoming(target_message):
                    skipped_known_message = True
                    if target_message != self.last_skipped_target:
                        self.last_skipped_target = target_message
                        self.events.put(("log", f"跳过已处理消息：{target_message}"))
                    message = ""
                if message and target_message and ChatMemory.canonical(target_message) != ChatMemory.canonical(self.last_message):
                    self.last_message = target_message
                    self.last_skipped_target = ""
                    self._add_context("对方", message)
                    reply = self.make_reply(message)
                    self._add_context("我", reply)
                    self.memory.remember_replied_target(target_message)
                    now = time.time()
                    last_time = self.last_reply_at.get(target_message, 0)
                    self.events.put(("log", f"收到：{message}"))
                    # 异步提取回复中的承诺，保存到承诺备忘
                    contact = self.target_note_var.get().strip()
                    self._extract_and_save_promise_async(reply, message, contact)

                    if reply and now - last_time >= self.rulebook.cooldown:
                        if self.dry_run.get():
                            self.events.put(("log", f"预览回复：{reply}（只预览，不发送）"))
                        elif not self.target_locked:
                            self.events.put(("log", "已生成回复，但未发送：当前聊天对象未锁定。"))
                        elif not self._has_input_position():
                            self.events.put(("log", "已生成回复，但未发送：聊天输入框位置未校准。"))
                        else:
                            target = self.target_note_var.get().strip()
                            self.events.put(("log", f"准备发送给 {target}：{reply}"))
                            if not self._wait_random_reply_delay():
                                continue
                            paste_text_to_position(
                                reply,
                                self.agnes_config.input_click_x,
                                self.agnes_config.input_click_y,
                                press_enter=True,
                            )
                            self._remember_self_reply(reply)
                            self.events.put(("state", ("运行中", "最近：发送完成，继续监听")))
                            self.events.put(("log", "发送完成。"))
                time.sleep(LOCAL_SCREENSHOT_POLL_SECONDS)
            except Exception as exc:
                self.events.put(("log", f"错误：{exc}"))
                time.sleep(2)

    def make_reply(self, message: str) -> str:
        if self.use_agnes.get():
            try:
                prompt = (
                    "请只回复下面这条最新收到的消息。"
                    "长期记忆/上下文只能辅助理解称呼和话题，不要主动回复旧话题。\n\n"
                    f"{message}"
                )
                return self.agnes.chat(prompt, context=self.chat_context)
            except Exception as exc:
                self.events.put(("log", f"Agnes 失败，改用关键词规则：{exc}"))
        return self.rulebook.match(message)

    def _extract_and_save_promise_async(self, reply, incoming_message="", contact=""):
        """后台异步提取回复里的承诺并保存到承诺备忘。不阻塞回复发送。"""
        if not reply:
            return
        # 仅在使用 Agnes 时提取
        if not self.use_agnes.get():
            return
        if not getattr(self.agnes_config, "api_key", ""):
            return

        def run():
            try:
                result = self.agnes.extract_promise(reply, incoming_message)
                if not result.get("has_promise"):
                    return
                content = result.get("content", "").strip()
                deadline = result.get("deadline", "").strip()
                if not content:
                    return
                ok, msg = self.promises.add_promise(contact, content, deadline)
                if ok:
                    self.events.put(("promise_saved", msg))
            except Exception as exc:
                self.events.put(("log", f"提取承诺失败（不影响回复）：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def _latest_incoming_message_block(self, region):
        if self.wechat is None:
            return "", ""
        ocr_message, ocr_target, ocr_reason = self._latest_incoming_from_local_ocr(region)
        if ocr_message and ocr_target:
            return ocr_message, ocr_target
        if ocr_reason:
            self._log_local_gate(ocr_reason)

        items = self.wechat.message_items(region=region, incoming_side=self.agnes_config.incoming_side)
        outgoing_y = self._latest_outgoing_y(items, region)
        if outgoing_y is None:
            self._log_local_gate("本地没有识别到我方最后一条消息的位置，不请求 Agnes。")
            return "", ""

        clean = []
        for item in items:
            if item.get("side") != "incoming":
                continue
            if outgoing_y is not None and item.get("cy", 0) <= outgoing_y:
                continue
            text = item.get("text", "")
            normalized = ChatMemory.normalize(text)
            if not normalized:
                continue
            if self._looks_like_recent_self_reply(normalized):
                continue
            if self.memory.has_replied_target(normalized):
                continue
            if normalized in clean:
                continue
            clean.append(normalized)
        if not clean:
            self._log_local_gate("本地未发现对方在我方最后一条消息下方发来新消息，不请求 Agnes。")
            return "", ""

        target = clean[-1]
        if self._should_skip_incoming(target):
            return "", target

        latest = clean[-1]
        return latest.strip(), target

    def _latest_incoming_from_local_ocr(self, region):
        if not region:
            return "", "", "聊天记录框未校准，无法本地 OCR。"
        try:
            lines, reason = local_ocr_incoming_below(region, self.agnes_config.incoming_side)
        except Exception as exc:
            return "", "", f"本地 OCR 失败：{exc}"
        if not lines:
            return "", "", f"本地 OCR 未发现新消息：{reason or '没有文字'}。"

        clean = []
        for line in lines:
            normalized = ChatMemory.normalize(line)
            if not normalized:
                continue
            if self._looks_like_recent_self_reply(normalized):
                continue
            if self.memory.has_replied_target(normalized):
                continue
            if normalized in clean:
                continue
            clean.append(normalized)
        if not clean:
            return "", "", "本地 OCR 识别到的内容都已处理，不请求 Agnes。"

        target = clean[-1]
        latest = clean[-1]
        return latest.strip(), target, ""

    def _log_local_gate(self, message):
        now = time.time()
        if now - self.last_local_gate_log_at >= 5:
            self.last_local_gate_log_at = now
            self.events.put(("log", message))

    def _latest_outgoing_y(self, items, region=None):
        outgoing = []
        for item in items:
            text = item.get("text", "")
            if item.get("side") == "outgoing" or self._looks_like_recent_self_reply(text):
                outgoing.append(item)
        if outgoing:
            return max(item.get("cy", 0) for item in outgoing)
        if not region:
            return None
        try:
            probe = chat_bubble_probe(region, self.agnes_config.incoming_side)
        except Exception:
            return None
        bottom = probe.get("outgoing_bottom")
        if bottom is None:
            return None
        return int(region[1]) + int(bottom)

    def _should_skip_incoming(self, text):
        normalized = ChatMemory.normalize(text)
        if not normalized:
            return True
        if self._looks_like_recent_self_reply(normalized):
            return True
        if self.memory.has_replied_target(normalized):
            return True
        return False

    def _mark_existing_messages_as_processed(self):
        """切换聊天对象时调用：把当前屏幕上已有的对方消息全部标记为已处理，
        这样只有之后新出现的消息才会触发回复。"""
        try:
            region = self._chat_box_region()
            if not region:
                return
            # 用 OCR 识别当前屏幕上所有对方消息
            last_seen = ""
            try:
                lines, _ = local_ocr_incoming_below(region, self.agnes_config.incoming_side)
            except Exception:
                lines = []
            count = 0
            for line in lines:
                normalized = ChatMemory.normalize(line)
                if not normalized:
                    continue
                if self._looks_like_recent_self_reply(normalized):
                    continue
                self.memory.remember_replied_target(normalized)
                last_seen = normalized
                count += 1
            # 也用 uia 路径扫一遍（双保险）
            if self.wechat is not None:
                try:
                    items = self.wechat.message_items(region=region, incoming_side=self.agnes_config.incoming_side)
                    # 找到屏幕最底部那条对方消息作为 last_message 候选
                    bottom_item = None
                    for item in items:
                        if item.get("side") != "incoming":
                            continue
                        text = item.get("text", "")
                        normalized = ChatMemory.normalize(text)
                        if not normalized:
                            continue
                        if self._looks_like_recent_self_reply(normalized):
                            continue
                        self.memory.remember_replied_target(normalized)
                        count += 1
                        if bottom_item is None or item.get("cy", 0) >= bottom_item.get("cy", 0):
                            bottom_item = item
                    if bottom_item is not None:
                        last_seen = ChatMemory.normalize(bottom_item.get("text", "")) or last_seen
                except Exception:
                    pass
            # 把最后一条识别到的对方消息设为 last_message，防止 worker 主循环里
            # target_message != self.last_message 的判断对历史消息失效。
            self.last_message = last_seen
            self.last_skipped_target = last_seen
            self.log(f"已标记当前聊天窗口 {count} 条已有消息为已处理，切换后只回复新消息。")
        except Exception as exc:
            self.log(f"预标记已有消息时出错（不影响使用）：{exc}")

    def make_reply_from_screenshot(self, region) -> str:
        image_data_url = screenshot_region_as_data_url(region)
        prompt = (
            "这是一张聊天记录区域截图。请只识别对方那一侧最底部最新的 1 到 3 条消息，"
            f"对方消息在聊天框的{self._incoming_side_name()}，我自己发出的消息在另一侧。"
            "只看对方那一侧的消息。不要把我自己发出的消息当成对方消息。"
            "不要回复更上面的旧消息；不要总结整屏聊天。"
            "如果对方那一侧底部没有新消息，或者最新可见消息是我自己发的，只输出空字符串。"
            "结合聊天上下文生成一条可直接发送的中文回复。只输出回复内容。"
            "如果看不清或没有新消息，只输出空字符串。"
        )
        return self.agnes.chat_with_image(prompt, image_data_url, context=self.chat_context)

    def _incoming_screenshot_changed(self, region):
        side_region = incoming_side_region(region, self.agnes_config.incoming_side)
        current = screenshot_fingerprint(side_region)
        if self.last_incoming_fingerprint is None:
            self.last_incoming_fingerprint = current
            self.events.put(("log", "已建立对方侧截图基线，本次不请求 Agnes。"))
            return False, 0.0
        diff = fingerprint_diff(self.last_incoming_fingerprint, current)
        self.last_incoming_fingerprint = current
        return diff >= INCOMING_IMAGE_DIFF_THRESHOLD, diff

    @staticmethod
    def _usable_reply(reply):
        if not reply:
            return False
        text = reply.strip().strip('"').strip("'")
        if not text:
            return False
        return text not in ("空字符串", "无", "没有新消息", "看不清")

    def _drain_events(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.log(payload)
            elif kind == "state":
                state, action = payload
                if state:
                    self.run_state_var.set(state)
                if action:
                    self.last_action_var.set(action)
            elif kind == "manual_reply":
                self.manual_reply_box.delete("1.0", tk.END)
                self.manual_reply_box.insert(tk.END, payload)
            elif kind == "manual_message":
                self.manual_message_box.delete("1.0", tk.END)
                self.manual_message_box.insert(tk.END, payload)
            elif kind == "capture_position":
                x, y = payload
                self.agnes_config.input_click_x = x
                self.agnes_config.input_click_y = y
                self.agnes_config.save()
                self.input_position_var.set(self._input_position_summary())
                self.log(f"已保存聊天输入框点击位置：({x}, {y})")
                self.show_toast(f"输入框位置已保存：({x}, {y})", "success")
            elif kind == "capture_chat_corner":
                corner, x, y = payload
                self._save_chat_box_corner(corner, x, y)
            elif kind == "toast":
                msg, level = payload
                self.show_toast(msg, level)
            elif kind == "promise_saved":
                self.log("承诺备忘：" + payload)
                self.show_toast(payload, "success")
                # 若承诺页面已构建，则刷新列表
                if hasattr(self, "promise_list_inner"):
                    self._promise_refresh()
        self.after(150, self._drain_events)

    def log(self, text):
        stamp = time.strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{stamp}] {text}\n")
        self.log_box.see(tk.END)
        if text:
            short = str(text).strip()
            if len(short) > 22:
                short = short[:22] + "..."
            self.last_action_var.set(f"最近：{short}")
        try:
            full_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with LOG_FILE.open("a", encoding="utf-8") as file:
                file.write(f"[{full_stamp}] {text}\n")
        except Exception:
            pass

    def _wait_random_reply_delay(self):
        delay = random.uniform(REPLY_DELAY_MIN_SECONDS, REPLY_DELAY_MAX_SECONDS)
        self.events.put(("state", ("等待发送", f"最近：等待 {delay:.1f} 秒后发送")))
        self.events.put(("log", f"已生成回复，将在 {delay:.1f} 秒后发送。"))
        end_at = time.time() + delay
        while time.time() < end_at:
            if self.stop_event.is_set():
                self.events.put(("state", ("已停止", "最近：发送前已停止")))
                return False
            time.sleep(0.2)
        self.events.put(("state", ("发送中", "最近：正在发送回复")))
        return True

    def _skills_summary(self):
        skills = self.skills.installed_skills()
        if not skills:
            return f"Skill 目录：{SKILLS_DIR}，当前未安装 skill。"
        return f"已安装 Skill：{', '.join(skills)}"

    def _input_position_summary(self):
        x = self.agnes_config.input_click_x
        y = self.agnes_config.input_click_y
        if x is None or y is None:
            return "输入框位置：未校准"
        return f"输入框位置：({x}, {y})"

    def _chat_box_summary(self):
        region = self._chat_box_region()
        if not region:
            return "聊天记录框：未完整校准"
        x1, y1, x2, y2 = region
        return f"聊天记录框：左上({x1}, {y1}) 右下({x2}, {y2})"

    def _chat_box_region(self):
        vals = (
            self.agnes_config.chat_box_x1,
            self.agnes_config.chat_box_y1,
            self.agnes_config.chat_box_x2,
            self.agnes_config.chat_box_y2,
        )
        if any(v is None for v in vals):
            return None
        x1, y1, x2, y2 = [int(v) for v in vals]
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def _normalize_chat_box(self):
        region = self._chat_box_region()
        if not region:
            return
        x1, y1, x2, y2 = region
        self.agnes_config.chat_box_x1 = x1
        self.agnes_config.chat_box_y1 = y1
        self.agnes_config.chat_box_x2 = x2
        self.agnes_config.chat_box_y2 = y2

    def _has_input_position(self):
        return self.agnes_config.input_click_x is not None and self.agnes_config.input_click_y is not None

    def _add_context(self, speaker, text):
        text = " ".join(str(text).split())
        if not text:
            return
        line = f"{speaker}: {text}"
        if not self.chat_context or self.chat_context[-1] != line:
            self.chat_context.append(line)
            self.chat_context = self.chat_context[-30:]
        self.memory.add_context(speaker, text)

    def _incoming_side_name(self):
        return "右侧" if self.agnes_config.incoming_side == "right" else "左侧"

    def _remember_self_reply(self, text):
        text = " ".join(str(text).split())
        if not text:
            return
        self.has_sent_in_current_chat = True
        self.last_self_reply_at = time.time()
        self.recent_self_replies.append(text)
        self.recent_self_replies = self.recent_self_replies[-8:]
        self.memory.remember_self_reply(text)
        self._reset_incoming_baseline_after_self_send()
        if self.wechat is not None:
            try:
                self.wechat.sent_replies.add(text)
            except Exception:
                pass

    def _reset_incoming_baseline_after_self_send(self):
        region = self._chat_box_region()
        if not region:
            self.last_incoming_fingerprint = None
            return
        try:
            time.sleep(0.8)
            side_region = incoming_side_region(region, self.agnes_config.incoming_side)
            self.last_incoming_fingerprint = screenshot_fingerprint(side_region)
            self.events.put(("log", "已重置对方侧本地检测基线。"))
        except Exception as exc:
            self.last_incoming_fingerprint = None
            self.events.put(("log", f"重置对方侧检测基线失败：{exc}"))

    def _looks_like_recent_self_reply(self, text):
        normalized = " ".join(str(text).split())
        if not normalized:
            return False
        if self.memory.looks_like_self_reply(normalized):
            return True
        for reply in self.recent_self_replies[-8:]:
            if normalized == reply:
                return True
            if len(normalized) >= 8 and (normalized in reply or reply in normalized):
                return True
        return False

    @staticmethod
    def _target_from_message_block(message):
        lines = [ChatMemory.normalize(line) for line in str(message).splitlines()]
        lines = [line for line in lines if line]
        return lines[-1] if lines else ChatMemory.normalize(message)


if __name__ == "__main__":
    App().mainloop()
