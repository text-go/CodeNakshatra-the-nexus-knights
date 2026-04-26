import os
import re
import time
import platform
import datetime
import subprocess
import sys
import webbrowser
import psutil
import io
import shutil
import threading
import math
import random
import string
import socket
import hashlib
import base64
import json
import pickle
import urllib.parse
import zipfile
import csv
import uuid
import difflib
import calendar
from typing import List

# ── LOAD .env FILE ────────────────────────────────────────────────────────────
# This reads MISTRAL_API_KEY and other secrets from the .env file
from dotenv import load_dotenv
load_dotenv()

# ── MISTRAL AI — The chat brain ───────────────────────────────────────────────
# pip install mistralai
try:
    from mistralai import Mistral
    MISTRAL_OK = True
except Exception as e:
    print(f"[DEKU] Mistral AI import failed: {e}")
    MISTRAL_OK = False

# ── NUMPY (for math operations) ───────────────────────────────────────────────
try:
    import numpy as np
    NP_OK = True
except Exception:
    NP_OK = False

# ── AUDIO (for voice input/output) ────────────────────────────────────────────
try:
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
    AUDIO_OK = True
except Exception:
    AUDIO_OK = False

# ── PYAUTOGUI (for controlling mouse/keyboard) ────────────────────────────────
try:
    import pyautogui
    GUI_OK = True
except Exception:
    GUI_OK = False

# ── TEXT-TO-SPEECH (so DEKU can talk) ────────────────────────────────────────
try:
    import pyttsx3
    TTS_OK = True
except Exception:
    TTS_OK = False

# ── SPEECH RECOGNITION (so DEKU can hear you) ────────────────────────────────
try:
    import speech_recognition as sr
    SR_OK = True
except Exception:
    SR_OK = False

# ── LANGCHAIN TOOLS (for @tool decorator and DuckDuckGo search) ──────────────
try:
    from langchain_community.tools import DuckDuckGoSearchRun
    from langchain_core.tools import tool
    LC_OK = True
except Exception as e:
    print(f"[DEKU] LangChain import failed: {e}")
    LC_OK= False
    # Dummy decorator so the rest of the file doesn't crash
    def tool(func):
        return func

# ── HUGGING FACE (for AI image generation) ────────────────────────────────────
try:
    from huggingface_hub import InferenceClient
    HF_CLIENT_OK = True
except Exception:
    HF_CLIENT_OK = False

# ── RAG (memory system — optional, app works without it) ─────────────────────
RAG_DENSE  = False
RAG_SPARSE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    RAG_SPARSE = True
except Exception:
    pass

try:
    # Suppress Windows DLL errors at import time
    if platform.system() == "Windows":
        import ctypes
        _old_mode = ctypes.windll.kernel32.SetErrorMode(0x8001)
    from sentence_transformers import SentenceTransformer as _ST
    if platform.system() == "Windows":
        ctypes.windll.kernel32.SetErrorMode(_old_mode)
    _test_enc = _ST("all-MiniLM-L6-v2")
    RAG_DENSE = True
    _SENTENCE_TRANSFORMER_CLS = _ST
except Exception:
    _SENTENCE_TRANSFORMER_CLS = None

# ── RICH (for beautiful terminal output) ──────────────────────────────────────
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich import box

console = Console()

# ══════════════════════════════════════════════════════════════════════════════
#  COLOR PALETTE — Used throughout for consistent styling
# ══════════════════════════════════════════════════════════════════════════════
C_GREEN  = "bold bright_green"
C_CYAN   = "bold cyan"
C_GOLD   = "bold yellow"
C_PINK   = "bold bright_magenta"
C_DIM    = "dim cyan"
C_WHITE  = "bold white"
C_RED    = "bold red"
C_HACK   = "bold green"
C_ORANGE = "bold bright_red"

def _c(style, text):
    """Wrap text in Rich color tags."""
    return f"[{style}]{text}[/{style}]"

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — reads values from .env file
# ══════════════════════════════════════════════════════════════════════════════

# Mistral AI API key — get free at: https://console.mistral.ai
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# Mistral model to use
# Options: mistral-large-latest, mistral-small-latest, open-mixtral-8x7b
MISTRAL_MODEL   = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

# HuggingFace token for image generation
HF_IMAGE_TOKEN  = os.getenv("HF_IMAGE_TOKEN", "")

# Your name — DEKU will use this to greet you
USER_NAME       = os.getenv("USER_NAME", "Lalit")

# Wake word for voice mode
WAKE_WORD       = os.getenv("bhai", "deku")

# Image generation model
IMAGE_MODEL     = "black-forest-labs/FLUX.1-schnell"

# Path to save RAG memory database
RAG_DB_PATH     = "deku_rag_db.pkl"

# ── Initialize Mistral AI client ──────────────────────────────────────────────
mistral_client = None
if MISTRAL_OK and MISTRAL_API_KEY:
    try:
        mistral_client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as e:
        console.print(_c(C_RED, f"  ✖ Mistral init failed: {e}"))
elif not MISTRAL_API_KEY:
    console.print(_c(C_RED, "  ✖ MISTRAL_API_KEY not set in .env file!"))

# ── Initialize HuggingFace image client ───────────────────────────────────────
client_img = None
if HF_CLIENT_OK and HF_IMAGE_TOKEN:
    try:
        client_img = InferenceClient(api_key=HF_IMAGE_TOKEN)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  BANNER AND UI FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def deku_banner():
    """Print the DEKU startup banner."""
    lines = [
        "",
        _c(C_CYAN,  "  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"),
        _c(C_GREEN, "  ░░   ██████╗ ███████╗██╗  ██╗██╗   ██╗   ░░"),
        _c(C_GREEN, "  ░░   ██╔══██╗██╔════╝██║ ██╔╝██║   ██║    ░░"),
        _c(C_GREEN, "  ░░   ██║  ██║█████╗  █████╔╝ ██║   ██║   ░░"),
        _c(C_GREEN, "  ░░   ██║  ██║██╔══╝  ██╔═██╗ ██║   ██║      ░░"),
        _c(C_GREEN, "  ░░   ██████╔╝███████╗██║  ██╗╚██████╔╝       ░░"),
        _c(C_GREEN, "  ░░   ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝         ░░"),
        _c(C_CYAN,  "  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"),
        _c(C_GOLD,  "  ▌  YOUR BEST AI FRIEND · DEKU · MISTRAL AI · 75 TOOLS  ▐"),
        _c(C_GOLD,  "  ▌  ENGINE: ") + _c(C_GREEN, f"Mistral AI ({MISTRAL_MODEL})") +
        _c(C_GOLD,  "  TTS: ") + _c(C_GREEN if TTS_OK else C_RED, "ON" if TTS_OK else "OFF") + _c(C_GOLD, "  ▐"),
        _c(C_CYAN,  "  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"),
        "",
    ]
    for line in lines:
        console.print(line)
        time.sleep(0.04)

def deku_matrix_flash(n: int = 3):
    """Show a quick Matrix-style animation on boot."""
    chars = "ｦｧｨｩｪｫ0123456789ABCDEF▓░▒"
    for _ in range(n):
        row = "  " + "".join(random.choice(chars) + " " for _ in range(34))
        console.print(_c(C_HACK, row))
        time.sleep(0.06)

def deku_status_table():
    """Show a table with system status and module availability."""
    t = Table(
        title="◈  DEKU v6  ·  SYSTEM DIAGNOSTICS  ◈",
        box=box.DOUBLE_EDGE,
        title_style=C_GREEN,
        header_style=C_CYAN,
        border_style="cyan",
        show_lines=True
    )
    t.add_column("MODULE",   style=C_CYAN,  justify="left",   min_width=26)
    t.add_column("STATUS",   style=C_GREEN, justify="center", min_width=14)
    t.add_column("DETAIL",   style=C_WHITE, justify="left",   min_width=36)

    # Helper: make a progress bar from a percentage
    def bar(pct):
        filled = int(pct // 10)
        return _c(C_GREEN, "█" * filled) + _c(C_DIM, "░" * (10 - filled)) + f"  {pct:.0f}%"

    # Gather system info
    cpu   = psutil.cpu_percent(interval=0.3)
    ram   = psutil.virtual_memory().percent
    bat   = psutil.sensors_battery()
    bat_s = f"{bat.percent:.0f}% {'⚡' if bat.power_plugged else '🔋'}" if bat else "Desktop"
    disk  = psutil.disk_usage('/').percent

    def ok(x):
        return ("◉ ON", C_GREEN) if x else ("◎ OFF", C_RED)

    # Add rows
    key_status = "◉ SET ✔" if MISTRAL_API_KEY else "✖ NOT SET"
    key_color  = C_GREEN if MISTRAL_API_KEY else C_RED
    t.add_row("LLM (Mistral AI)",    f"[{key_color}]{key_status}[/{key_color}]", f"Model: {MISTRAL_MODEL}")
    t.add_row("Tool Matrix",         "◉ 75 LOADED", "Core+Hack+RAG+God+New")
    sts, col = ok(TTS_OK);    t.add_row("Voice TTS",          f"[{col}]{sts}[/{col}]", "pyttsx3")
    sts, col = ok(SR_OK);     t.add_row("Speech Input",       f"[{col}]{sts}[/{col}]", "[S] key to speak")
    sts, col = ok(RAG_DENSE); t.add_row("Dense RAG",          f"[{col}]{sts}[/{col}]", "SentenceTransformers")
    sts, col = ok(RAG_SPARSE);t.add_row("Sparse RAG (TF-IDF)",f"[{col}]{sts}[/{col}]", "scikit-learn")
    t.add_row("CPU",  bar(cpu),  "")
    t.add_row("RAM",  bar(ram),  f"{psutil.virtual_memory().used // 1024**3}GB used")
    t.add_row("Battery", "◉ OK", bat_s)
    t.add_row("Disk", bar(disk), f"{psutil.disk_usage('/').used // 1024**3}GB used")

    console.print(t)

def deku_input_prompt():
    """Print the input prompt line."""
    console.print(f"\n{_c(C_DIM, '╔' + '═' * 62 + '╗')}")
    console.print(
        _c(C_DIM, "║") + "  " +
        _c(C_GREEN, "◈") + " " +
        _c(C_CYAN, "DEKU v6  ▸  Talk to me!") + "  " +
        _c(C_GOLD, "▶") + "  ",
        end=""
    )

def deku_tool_flash(name: str):
    """Announce that a tool is being used."""
    console.print(
        f"\n  {_c(C_GOLD, '⚡')} {_c(C_GREEN, 'TOOL')} "
        f"{_c(C_DIM, '▸▸')} {_c(C_GOLD, name.upper())} "
        f"{_c(C_DIM, '▸▸')} {_c(C_CYAN, 'EXECUTING')}"
    )

def deku_response_panel(text: str):
    """Print DEKU's reply inside a nice bordered panel."""
    border = _c(C_DIM, "║")
    console.print(f"\n{_c(C_DIM, '╔' + '═' * 62 + '╗')}")
    console.print(f"{border}  {_c(C_GREEN, '◉')} {_c(C_CYAN, 'D E K U  v6  ·  MISTRAL AI')}")
    console.print(_c(C_DIM, "╠" + "═" * 62 + "╣"))
    for line in text.strip().splitlines():
        # Escape Rich markup brackets so they print literally
        safe = line.replace("[", "\\[")
        console.print(f"{border}  {_c(C_WHITE, safe)}")
    console.print(_c(C_DIM, "╚" + "═" * 62 + "╝"))

def deku_thinking():
    """Return a spinner progress bar to show while waiting for AI response."""
    return Progress(
        SpinnerColumn(spinner_name="dots12", style=C_GREEN),
        TextColumn(f"{_c(C_CYAN, '◈')} {_c(C_GREEN, 'MISTRAL THINKING')} {_c(C_DIM, '...')}"),
        BarColumn(bar_width=28, style="cyan", complete_style="bright_green"),
        TextColumn(_c(C_GOLD, "HOLD ON BRO")),
        transient=True,
    )

def deku_section(title: str):
    """Print a section divider with a title."""
    console.print(f"\n{_c(C_DIM, '─' * 64)}")
    console.print(f"  {_c(C_GREEN, '◈')} {_c(C_CYAN, title.upper())}")
    console.print(_c(C_DIM, '─' * 64))

# ══════════════════════════════════════════════════════════════════════════════
#  HYBRID RAG ENGINE — DEKU's long-term memory system
#  RAG = Retrieval-Augmented Generation
#  This lets DEKU remember things you teach it, even across sessions
# ══════════════════════════════════════════════════════════════════════════════

class HybridRAGEngine:
    """
    Stores text chunks and retrieves the most relevant ones
    when you ask a question. Like a smart notebook for DEKU.

    Supports two search methods:
    - Dense (uses AI embeddings — more accurate, needs sentence-transformers)
    - Sparse (uses TF-IDF keyword matching — always available)
    """

    def __init__(self, db_path: str = RAG_DB_PATH):
        self.db_path   = db_path
        self.documents: List[dict] = []   # List of stored text chunks
        self.encoder   = None             # Dense embedding model (optional)
        self._tfidf    = None             # TF-IDF vectorizer (sparse)
        self._tfidf_matrix = None         # Pre-computed TF-IDF matrix

        self._load_db()

        # Try to load the dense embedding model
        if RAG_DENSE and _SENTENCE_TRANSFORMER_CLS:
            try:
                self.encoder = _SENTENCE_TRANSFORMER_CLS("all-MiniLM-L6-v2")
            except Exception:
                pass

        console.print(_c(C_GREEN,
            f"  ◉ RAG: {len(self.documents)} chunks | "
            f"Dense={'ON' if self.encoder else 'OFF'} | "
            f"Sparse={'ON' if RAG_SPARSE else 'OFF'}"
        ))

    def _load_db(self):
        """Load saved documents from disk (pickle file)."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "rb") as f:
                    self.documents = pickle.load(f)
            except Exception:
                self.documents = []

    def _save_db(self):
        """Save current documents to disk."""
        try:
            with open(self.db_path, "wb") as f:
                pickle.dump(self.documents, f)
        except Exception:
            pass

    def _chunk(self, text: str, size: int = 300, overlap: int = 50) -> List[str]:
        """
        Split a long text into overlapping chunks.
        Overlap helps preserve context across chunk boundaries.
        """
        words  = text.split()
        chunks = []
        for i in range(0, len(words), size - overlap):
            chunk = " ".join(words[i:i + size])
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

    def _rebuild_tfidf(self):
        """Rebuild the TF-IDF index after adding new documents."""
        if not RAG_SPARSE or not self.documents:
            return
        try:
            texts           = [d["text"] for d in self.documents]
            self._tfidf     = TfidfVectorizer(max_features=5000).fit(texts)
            self._tfidf_matrix = self._tfidf.transform(texts)
        except Exception:
            pass

    def ingest(self, text: str, source: str = "manual") -> int:
        """
        Add new text to DEKU's memory.
        Returns the number of new chunks added.
        """
        chunks = self._chunk(text)
        added  = 0
        for chunk in chunks:
            # Use a hash to avoid duplicate chunks
            doc_id = hashlib.sha256(chunk.encode()).hexdigest()[:12]
            if not any(d["id"] == doc_id for d in self.documents):
                entry = {"id": doc_id, "text": chunk, "source": source, "embedding": None}
                # Compute dense embedding if model is available
                if self.encoder:
                    try:
                        entry["embedding"] = self.encoder.encode([chunk])[0]
                    except Exception:
                        pass
                self.documents.append(entry)
                added += 1
        self._save_db()
        self._rebuild_tfidf()
        return added

    def ingest_file(self, filepath: str) -> int:
        """Load a text/markdown/PDF file into memory."""
        try:
            if filepath.lower().endswith(".pdf"):
                try:
                    import fitz
                    doc  = fitz.open(filepath)
                    text = " ".join(p.get_text() for p in doc)
                except ImportError:
                    return -2   # Signal: need pymupdf
            else:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            return self.ingest(text, source=os.path.basename(filepath))
        except Exception:
            return -1

    def retrieve(self, query: str, top_k: int = 4) -> List[dict]:
        """Find the top-k most relevant chunks for a query."""
        if not self.documents:
            return []

        scores = [0.0] * len(self.documents)

        # Dense scoring (more accurate)
        if self.encoder:
            try:
                q_emb = self.encoder.encode([query])[0]
                for i, doc in enumerate(self.documents):
                    if doc["embedding"] is not None:
                        scores[i] += 0.7 * float(
                            cosine_similarity([q_emb], [doc["embedding"]])[0][0]
                        )
            except Exception:
                pass

        # Sparse scoring (keyword-based fallback)
        if RAG_SPARSE and self._tfidf and self._tfidf_matrix is not None:
            try:
                q_vec = self._tfidf.transform([query])
                sims  = cosine_similarity(q_vec, self._tfidf_matrix)[0]
                for i, s in enumerate(sims):
                    scores[i] += 0.3 * float(s)
            except Exception:
                pass
        elif not self.encoder:
            # Fallback: simple word overlap
            qwords = set(query.lower().split())
            for i, doc in enumerate(self.documents):
                dwords   = set(doc["text"].lower().split())
                scores[i] = len(qwords & dwords) / (len(qwords) + 1)

        ranked = sorted(enumerate(self.documents), key=lambda x: scores[x[0]], reverse=True)
        return [doc for _, doc in ranked[:top_k]]

    def query_with_context(self, query: str, top_k: int = 4) -> str:
        """Return relevant memory chunks as a formatted string."""
        docs = self.retrieve(query, top_k)
        if not docs:
            return ""
        ctx = "\n\n".join(f"[{d['source']}]\n{d['text']}" for d in docs)
        return f"=== DEKU MEMORY ===\n{ctx}\n=================="

    def list_sources(self) -> List[str]:
        """Return all unique source names in memory."""
        return list({d["source"] for d in self.documents})

    def delete_source(self, source: str) -> int:
        """Remove all chunks from a specific source."""
        before         = len(self.documents)
        self.documents = [d for d in self.documents if d["source"] != source]
        self._save_db()
        self._rebuild_tfidf()
        return before - len(self.documents)

    def clear_all(self) -> int:
        """Wipe the entire memory database."""
        n              = len(self.documents)
        self.documents = []
        self._save_db()
        return n


# Create the global RAG engine instance
rag_engine = HybridRAGEngine()

# ══════════════════════════════════════════════════════════════════════════════
#  MISTRAL AI CHAT ENGINE
#  Replaces the old HuggingFace/LangChain LLM — much simpler and faster
# ══════════════════════════════════════════════════════════════════════════════

# Conversation history — stores all past messages so DEKU remembers context
mistral_history: List[dict] = []


def mistral_chat(user_message: str, system_prompt: str = "") -> str:
    """
    Send a message to Mistral AI and get a reply.

    How it works:
    1. Build a list of messages (system + past conversation + new message)
    2. Call Mistral's API
    3. Extract and return the text reply
    4. Save the exchange to history for future context

    Returns a plain string with DEKU's response.
    """
    # Check if client is ready
    if not mistral_client:
        return "Mistral client not initialized. Please set MISTRAL_API_KEY in your .env file."

    # Build the message list to send to Mistral
    messages = []

    # System message — tells Mistral who DEKU is and how to behave
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Add past conversation (last 20 turns to avoid going over token limit)
    messages += mistral_history[-20:]

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    try:
        # Call Mistral API
        response = mistral_client.chat.complete(
            model=MISTRAL_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

        # Extract the text reply from the response object
        reply = response.choices[0].message.content.strip()

        # Save this exchange to history so DEKU remembers it
        mistral_history.append({"role": "user",      "content": user_message})
        mistral_history.append({"role": "assistant", "content": reply})

        return reply

    except Exception as e:
        return f"Mistral error: {e}"


def build_system_prompt() -> str:
    """
    Build the system prompt that defines DEKU's personality and rules.
    This gets sent to Mistral with every message.
    """
    h          = datetime.datetime.now().hour
    greet_time = "morning" if h < 12 else "afternoon" if h < 17 else "evening"

    return f"""
You are DEKU v6 — NOT a generic assistant, but {USER_NAME}'s best AI FRIEND.
Engine: Mistral AI ({MISTRAL_MODEL})
Current time: {datetime.datetime.now():%A, %d %B %Y  %H:%M}
Greeting time: {greet_time}

YOUR PERSONALITY:
- Talk like a close buddy: casual, warm, enthusiastic, honest
- Use phrases like "bro", "dude", "hey", "yo", "got you covered"
- Celebrate with the user, crack light jokes, be genuinely helpful
- Still be sharp, precise, and powerful when it counts

TOOL CALLING FORMAT:
- When you want to use a tool, write EXACTLY this on its own line:
  TOOL:<tool_name>|{{"arg1": "value1", "arg2": "value2"}}
- Example: TOOL:web_search|{{"query": "current weather Delhi"}}
- After getting tool results, summarize them naturally for the user
- Keep replies under 4 sentences unless technical detail is needed

MEMORY: You have {len(rag_engine.documents)} knowledge chunks stored.

AVAILABLE TOOLS:
web_search, generate_image, system_control, coding_master, read_code_file,
system_stats, youtube_search, weather_info, volume_control, brightness_control,
note_taker, currency_converter, motivation_booster, close_window, list_files,
send_email, send_whatsapp, file_manager, set_alarm, calculator, news_headlines,
app_launcher, clipboard_manager, maps_search, password_generator, dictionary_lookup,
stock_price, network_info, kill_process, joke_fact_teller, pomodoro_timer,
port_scanner, ping_traceroute, dns_whois_lookup, hash_generator, base64_tool,
wifi_scanner, steganography, vulnerability_scanner,
rag_ingest_text, rag_ingest_file, rag_query, rag_list_sources, rag_delete_source, rag_clear_all,
auto_coder, system_optimizer, smart_summarizer, multi_search, conversation_export,
screen_reader, schedule_task, language_translator, code_debugger, ip_geolocation,
system_benchmark, regex_tool, file_search, text_to_speech_file, process_manager, knowledge_snapshot,
qr_code_generator, text_diff, zip_manager, csv_analyzer, json_formatter,
random_data_generator, color_converter, timestamp_converter, math_plotter,
word_counter, bulk_rename, dir_tree, env_manager, ping_sweep, ssl_checker,
http_tester, cron_helper, git_summary, ascii_art, memory_dump, todo_manager
"""

# ══════════════════════════════════════════════════════════════════════════════
#  VOICE ENGINE — lets DEKU speak and listen
# ══════════════════════════════════════════════════════════════════════════════

class DekuVoice:
    """
    Handles text-to-speech output.
    - speak(text) → prints to terminal AND speaks aloud if voice mode is ON
    - toggle_voice_output() → turn speaking on/off with [V] key
    """

    def __init__(self):
        self._lock   = threading.Lock()  # Prevent two threads speaking at once
        self._v_mode = False             # Voice output off by default
        self.engine  = None

        if TTS_OK:
            try:
                self.engine = pyttsx3.init()
                self._setup()
            except Exception:
                self.engine = None

    def _setup(self):
        """Configure the TTS voice (prefer female voice, set speed)."""
        if not self.engine:
            return
        try:
            voices = self.engine.getProperty("voices")
            # Try to find a female voice
            for v in voices:
                if any(k in v.name.lower() for k in ("female", "zira", "samantha", "hazel", "aria")):
                    self.engine.setProperty("voice", v.id)
                    break
            else:
                # Fallback: use second voice (usually female on Windows)
                if len(voices) > 1:
                    self.engine.setProperty("voice", voices[1].id)
            self.engine.setProperty("rate",   175)  # Words per minute
            self.engine.setProperty("volume", 1.0)  # Max volume
        except Exception:
            pass

    def _reinit(self):
        """Reinitialize TTS engine if it crashes."""
        if not TTS_OK:
            return
        try:
            self.engine = pyttsx3.init()
            self._setup()
        except Exception:
            self.engine = None

    def toggle_voice_output(self):
        """Turn voice speaking on or off."""
        self._v_mode = not self._v_mode
        status = "ENABLED" if self._v_mode else "DISABLED"
        console.print(f"\n  {_c(C_GOLD, '🔊')} {_c(C_GREEN, f'VOICE OUTPUT: {status}')}")
        if self._v_mode:
            self._say_raw(f"Voice output enabled. Hey {USER_NAME}!")

    @property
    def voice_output_on(self):
        return self._v_mode

    def _say_raw(self, text: str):
        """Speak a string without displaying it."""
        if not self.engine:
            return
        with self._lock:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception:
                self._reinit()

    def speak(self, text: str):
        """
        Display text in the response panel AND speak it aloud
        if voice mode is enabled.
        """
        if not text:
            return
        # Clean up markdown/special chars before speaking
        clean = re.sub(r'[*_#`>\[\]\\]', '', text).strip()
        if not clean:
            return

        # Always display in terminal
        deku_response_panel(clean)

        # Only speak aloud if voice mode is on
        if self._v_mode and self.engine:
            sentences = re.split(r'(?<=[.!?])\s+', clean)
            with self._lock:
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    for attempt in range(3):
                        try:
                            self.engine.say(sentence)
                            self.engine.runAndWait()
                            break
                        except Exception:
                            self._reinit()


# Create the global voice instance
deku_voice = DekuVoice()

# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO CAPTURE — microphone input
# ══════════════════════════════════════════════════════════════════════════════

def capture_audio(duration: int = 5) -> str:
    """
    Record audio from the microphone and convert to text.
    Returns the recognized text as a string, or "" on failure.
    """
    if not AUDIO_OK or not SR_OK:
        console.print(_c(C_RED, "  ✖ Audio libs not available. Install: sounddevice scipy SpeechRecognition"))
        return ""

    console.print(f"  {_c(C_GREEN, '🎙  LISTENING...')} {_c(C_DIM, f'({duration}s)')}")

    try:
        # Record audio as numpy array
        recording = sd.rec(int(duration * 44100), samplerate=44100, channels=1, dtype='int16')
        sd.wait()

        # Convert to WAV format in memory (no temp file needed)
        buf = io.BytesIO()
        wav_write(buf, 44100, recording)
        buf.seek(0)

        # Recognize speech using Google's free API
        recognizer = sr.Recognizer()
        with sr.AudioFile(buf) as source:
            audio = recognizer.record(source)
        result = recognizer.recognize_google(audio).lower()

        console.print(f"  {_c(C_GOLD, '◈ HEARD:')} {_c(C_WHITE, result)}")
        return result

    except Exception as e:
        console.print(f"  {_c(C_RED, f'Audio error: {e}')}")
        return ""

# ══════════════════════════════════════════════════════════════════════════════
#  ████████████████  75 TOOLS  ████████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════

# ── BLOCK 1: CORE TOOLS (15) ──────────────────────────────────────────────────

@tool
def generate_image(prompt: str):
    """Generate an AI image from a text description and save it as PNG."""
    deku_tool_flash("generate_image")
    if not client_img:
        return "Image client not ready. Set HF_IMAGE_TOKEN in .env file."
    try:
        img = client_img.text_to_image(prompt, model=IMAGE_MODEL)
        fn  = f"deku_art_{int(time.time())}.png"
        img.save(fn)
        return f"Image saved: {fn}"
    except Exception as e:
        return f"Image error: {e}"

@tool
def web_search(query: str):
    """Search the internet for real-time information using DuckDuckGo."""
    deku_tool_flash("web_search")
    try:
        return DuckDuckGoSearchRun().run(query)
    except Exception as e:
        return f"Search error: {e}"

@tool
def system_control(command: str):
    """Control the PC — screenshot, notepad, calc, shutdown, restart, lock."""
    deku_tool_flash("system_control")
    cmd = command.lower()
    if not GUI_OK:
        return "pyautogui not available."
    if "screenshot" in cmd:
        p = f"snap_{int(time.time())}.png"
        pyautogui.screenshot().save(p)
        return f"Screenshot saved: {p}"
    if "notepad" in cmd:
        subprocess.Popen("notepad.exe")
        return "Notepad opened."
    if "calc" in cmd:
        subprocess.Popen("calc.exe")
        return "Calculator opened."
    if "task" in cmd:
        subprocess.Popen("taskmgr.exe")
        return "Task Manager opened."
    if "shutdown" in cmd:
        subprocess.Popen(["shutdown", "/s", "/t", "10"])
        return "Shutdown in 10 seconds."
    if "restart" in cmd:
        subprocess.Popen(["shutdown", "/r", "/t", "10"])
        return "Restart in 10 seconds."
    if "lock" in cmd:
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation")
        return "PC locked."
    return "Unknown command. Try: screenshot, notepad, calc, task, shutdown, restart, lock"

@tool
def coding_master(filename: str, content: str):
    """Save code to deku_workspace/<filename>. Creates the folder if needed."""
    deku_tool_flash("coding_master")
    try:
        os.makedirs("deku_workspace", exist_ok=True)
        fp = os.path.join("deku_workspace", filename)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Saved: deku_workspace/{filename}"
    except Exception as e:
        return f"Error: {e}"

@tool
def read_code_file(filename: str):
    """Read a file from deku_workspace and return its contents."""
    deku_tool_flash("read_code_file")
    try:
        with open(os.path.join("deku_workspace", filename), encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "File not found in deku_workspace."

@tool
def system_stats(query: str = "all"):
    """Show CPU, RAM, battery, and disk usage."""
    deku_tool_flash("system_stats")
    cpu   = psutil.cpu_percent(interval=0.5)
    ram   = psutil.virtual_memory()
    bat   = psutil.sensors_battery()
    disk  = psutil.disk_usage('/')
    bat_s = f"{bat.percent:.0f}% ({'Charging' if bat.power_plugged else 'Battery'})" if bat else "Desktop PC"
    return (
        f"CPU: {cpu}%  |  "
        f"RAM: {ram.percent}% ({ram.used // 1024**3}/{ram.total // 1024**3}GB)  |  "
        f"Battery: {bat_s}  |  "
        f"Disk: {disk.percent}%"
    )

@tool
def youtube_search(topic: str):
    """Open YouTube in the browser with a search for the given topic."""
    deku_tool_flash("youtube_search")
    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(topic)}")
    return f"YouTube opened for: {topic}"

@tool
def weather_info(city: str):
    """Get current weather info for any city."""
    deku_tool_flash("weather_info")
    try:
        return DuckDuckGoSearchRun().run(f"current weather {city} today temperature humidity")
    except Exception as e:
        return f"Weather error: {e}"

@tool
def volume_control(action: str):
    """Control system volume. action = up / down / mute."""
    deku_tool_flash("volume_control")
    if not GUI_OK:
        return "pyautogui not available."
    a = action.lower()
    if "up"   in a: [pyautogui.press("volumeup")   for _ in range(5)]; return "Volume up."
    if "down" in a: [pyautogui.press("volumedown") for _ in range(5)]; return "Volume down."
    if "mute" in a: pyautogui.press("volumemute");                      return "Muted."
    return "Use: up / down / mute"

@tool
def brightness_control(level: str):
    """Adjust screen brightness. level = up / down."""
    deku_tool_flash("brightness_control")
    if not GUI_OK:
        return "pyautogui not available."
    if "up" in level.lower():
        pyautogui.press("brightnessup")
        return "Brightness increased."
    pyautogui.press("brightnessdown")
    return "Brightness decreased."

@tool
def note_taker(text: str):
    """Save a note with a timestamp to deku_notes.txt."""
    deku_tool_flash("note_taker")
    with open("deku_notes.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}]  {text}\n")
    return "Note saved to deku_notes.txt!"

@tool
def currency_converter(amount: str, from_cur: str, to_cur: str):
    """Convert currency amounts. Example: amount='100', from_cur='USD', to_cur='INR'."""
    deku_tool_flash("currency_converter")
    try:
        return DuckDuckGoSearchRun().run(f"convert {amount} {from_cur} to {to_cur} today exchange rate")
    except Exception as e:
        return f"Error: {e}"

@tool
def motivation_booster(query: str = "boost"):
    """Get a motivational quote to keep going."""
    deku_tool_flash("motivation_booster")
    try:
        return DuckDuckGoSearchRun().run("best short motivational quote today")
    except Exception as e:
        return f"Error: {e}"

@tool
def close_window(query: str = "close"):
    """Close the currently active window using Alt+F4."""
    deku_tool_flash("close_window")
    if not GUI_OK:
        return "pyautogui not available."
    pyautogui.hotkey("alt", "f4")
    return "Window closed."

@tool
def list_files(directory: str = "."):
    """List up to 25 files in a directory."""
    deku_tool_flash("list_files")
    try:
        files = os.listdir(directory)
        return ("Files: " + ", ".join(files[:25])) if files else "Directory is empty."
    except Exception as e:
        return f"Error: {e}"

# ── BLOCK 2: COMMUNICATION & SYSTEM (8) ───────────────────────────────────────

@tool
def send_email(to: str, subject: str, body: str):
    """Open the default email client with a pre-filled draft."""
    deku_tool_flash("send_email")
    webbrowser.open(
        f"mailto:{to}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
    )
    return f"Email draft opened for: {to}"

@tool
def send_whatsapp(phone: str, message: str):
    """Open WhatsApp Web with a pre-filled message for a phone number."""
    deku_tool_flash("send_whatsapp")
    webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")
    return f"WhatsApp opened for: {phone}"

@tool
def file_manager(action: str, source: str, destination: str = ""):
    """Manage files. action = copy / move / delete / rename."""
    deku_tool_flash("file_manager")
    try:
        a = action.lower()
        if a == "copy":   shutil.copy2(source, destination);  return f"Copied to: {destination}"
        if a == "move":   shutil.move(source, destination);   return f"Moved to: {destination}"
        if a == "delete":
            (os.remove if os.path.isfile(source) else shutil.rmtree)(source)
            return f"Deleted: {source}"
        if a == "rename": os.rename(source, destination);     return f"Renamed to: {destination}"
        return "Use: copy / move / delete / rename"
    except Exception as e:
        return f"Error: {e}"

@tool
def set_alarm(minutes: int, label: str = "DEKU Alarm"):
    """Set a timed voice reminder. Fires after N minutes in the background."""
    deku_tool_flash("set_alarm")
    def _fire():
        time.sleep(minutes * 60)
        console.print(f"\n{_c(C_GOLD, f'⏰  ALARM: {label}')}")
        deku_voice.speak(f"Hey {USER_NAME}! Reminder: {label}")
    threading.Thread(target=_fire, daemon=True).start()
    return f"Alarm set for {minutes} minute(s): {label}"

@tool
def calculator(expression: str):
    """Evaluate math: sqrt, sin, cos, log, pow, pi, e, etc. Example: 'sqrt(144)'."""
    deku_tool_flash("calculator")
    try:
        # Build a safe namespace with math functions
        ns = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        ns.update({"abs": abs, "round": round, "pow": pow})
        result = eval(expression, {"__builtins__": {}}, ns)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Math error: {e}"

@tool
def news_headlines(topic: str = "top news India"):
    """Fetch the latest news headlines for any topic."""
    deku_tool_flash("news_headlines")
    try:
        return DuckDuckGoSearchRun().run(f"latest {topic} news today")
    except Exception as e:
        return f"Error: {e}"

@tool
def app_launcher(app_name: str):
    """Launch installed apps: chrome, firefox, spotify, vlc, vscode, discord, etc."""
    deku_tool_flash("app_launcher")
    APP_MAP = {
        "chrome": "chrome", "firefox": "firefox", "spotify": "spotify", "vlc": "vlc",
        "word": "winword", "excel": "excel", "powerpoint": "powerpnt", "vscode": "code",
        "paint": "mspaint", "discord": "discord", "telegram": "telegram",
        "explorer": "explorer", "cmd": "cmd", "terminal": "cmd", "notepad": "notepad"
    }
    cmd = APP_MAP.get(app_name.lower(), app_name)
    try:
        subprocess.Popen(cmd)
        return f"Launching {app_name}..."
    except Exception as e:
        return f"Failed to launch: {e}"

@tool
def clipboard_manager(action: str, text: str = ""):
    """Manage clipboard. action = copy (saves text) / paste (reads clipboard)."""
    deku_tool_flash("clipboard_manager")
    try:
        import pyperclip
        if action == "copy":
            pyperclip.copy(text)
            return "Copied to clipboard."
        return f"Clipboard contents: {pyperclip.paste()}"
    except ImportError:
        if not GUI_OK:
            return "pyautogui not available."
        if action == "copy":
            pyautogui.hotkey("ctrl", "c")
            return "Copy shortcut sent."
        pyautogui.hotkey("ctrl", "v")
        return "Paste shortcut sent."

# ── BLOCK 3: GENERAL TOOLS (8) ────────────────────────────────────────────────

@tool
def maps_search(location: str):
    """Open Google Maps in the browser for a location."""
    deku_tool_flash("maps_search")
    webbrowser.open(f"https://www.google.com/maps/search/{urllib.parse.quote(location)}")
    return f"Maps opened: {location}"

@tool
def password_generator(length: int = 16, include_symbols: bool = True):
    """Generate a cryptographically secure random password."""
    deku_tool_flash("password_generator")
    chars = string.ascii_letters + string.digits
    if include_symbols:
        chars += "!@#$%^&*()-_=+"
    pwd = "".join(random.SystemRandom().choice(chars) for _ in range(length))
    return f"Password ({length} chars): {pwd}"

@tool
def dictionary_lookup(word: str):
    """Look up the definition of any English word."""
    deku_tool_flash("dictionary_lookup")
    try:
        return DuckDuckGoSearchRun().run(f"definition and meaning of word: {word}")
    except Exception as e:
        return f"Error: {e}"

@tool
def stock_price(symbol: str):
    """Get the current stock price for a company or index (NSE/BSE/Global)."""
    deku_tool_flash("stock_price")
    try:
        return DuckDuckGoSearchRun().run(f"{symbol} stock price today live NSE BSE")
    except Exception as e:
        return f"Error: {e}"

@tool
def network_info(query: str = "all"):
    """Get the machine's hostname, local IP, and network data usage."""
    deku_tool_flash("network_info")
    try:
        host = socket.gethostname()
        ip   = socket.gethostbyname(host)
        net  = psutil.net_io_counters()
        return (
            f"Hostname: {host}  |  IP: {ip}  |  "
            f"Sent: {net.bytes_sent / 1024**2:.1f}MB  |  "
            f"Received: {net.bytes_recv / 1024**2:.1f}MB"
        )
    except Exception as e:
        return f"Error: {e}"

@tool
def kill_process(process_name: str):
    """Force-kill a running process by name (e.g., 'chrome', 'vlc')."""
    deku_tool_flash("kill_process")
    killed = 0
    for p in psutil.process_iter(["name"]):
        if process_name.lower() in (p.info["name"] or "").lower():
            try:
                p.kill()
                killed += 1
            except Exception:
                pass
    return f"Killed {killed} process(es) named: {process_name}" if killed else f"No process found: {process_name}"

@tool
def joke_fact_teller(category: str = "joke"):
    """Tell a funny joke or an interesting fun fact. category = joke / fact."""
    deku_tool_flash("joke_fact_teller")
    query = "tell me a funny short joke" if "joke" in category else "amazing surprising fun fact"
    try:
        return DuckDuckGoSearchRun().run(query)
    except Exception as e:
        return f"Error: {e}"

@tool
def pomodoro_timer(work_minutes: int = 25, break_minutes: int = 5):
    """Start a Pomodoro focus session with voice alerts at the end."""
    deku_tool_flash("pomodoro_timer")
    def _run():
        deku_voice.speak(f"Pomodoro started! Focus for {work_minutes} minutes, {USER_NAME}!")
        time.sleep(work_minutes * 60)
        deku_voice.speak(f"Work session done! Take a {break_minutes} minute break!")
        time.sleep(break_minutes * 60)
        deku_voice.speak("Break over! Time to focus again!")
    threading.Thread(target=_run, daemon=True).start()
    return f"Pomodoro started: {work_minutes}min work + {break_minutes}min break"

# ── BLOCK 4: HACKER TOOLS (8) ────────────────────────────────────────────────
#  IMPORTANT: These are for ethical use only — your own systems!

@tool
def port_scanner(target: str, start_port: int = 1, end_port: int = 1024):
    """Scan open TCP ports on a host. ETHICAL USE ONLY — your own systems."""
    deku_tool_flash("port_scanner [HACK]")
    open_ports = []
    try:
        ip = socket.gethostbyname(target)
        for port in range(start_port, min(end_port + 1, start_port + 200)):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.4)
                if s.connect_ex((ip, port)) == 0:
                    open_ports.append(port)
        if open_ports:
            return f"Open ports on {target}: {open_ports}"
        return f"No open ports found on {target} in range {start_port}-{end_port}."
    except Exception as e:
        return f"Scan error: {e}"

@tool
def ping_traceroute(target: str, mode: str = "ping"):
    """Ping or traceroute a host. mode = ping / traceroute."""
    deku_tool_flash("ping_traceroute [HACK]")
    try:
        if mode == "ping":
            flag   = "-n" if platform.system() == "Windows" else "-c"
            result = subprocess.run(["ping", flag, "4", target], capture_output=True, text=True, timeout=15)
            return result.stdout or result.stderr
        cmd    = ["tracert", target] if platform.system() == "Windows" else ["traceroute", target]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout[:1000] or result.stderr
    except Exception as e:
        return f"Error: {e}"

@tool
def dns_whois_lookup(domain: str):
    """Do DNS lookup and get WHOIS info for a domain."""
    deku_tool_flash("dns_whois [HACK]")
    try:
        ip = socket.gethostbyname(domain)
        try:
            rev = socket.gethostbyaddr(ip)[0]
        except Exception:
            rev = "N/A"
        try:
            whois = DuckDuckGoSearchRun().run(f"WHOIS {domain}")[:300]
        except Exception:
            whois = "N/A"
        return f"Domain: {domain}\nIP: {ip}\nReverse DNS: {rev}\nWHOIS snippet: {whois}"
    except Exception as e:
        return f"Error: {e}"

@tool
def hash_generator(text: str, algorithm: str = "sha256"):
    """Generate a cryptographic hash. algorithm = md5 / sha1 / sha256 / sha512."""
    deku_tool_flash("hash_generator [HACK]")
    try:
        h = hashlib.new(algorithm.lower(), text.encode()).hexdigest()
        return f"[{algorithm.upper()}] {h}"
    except ValueError:
        return "Unknown algorithm. Use: md5, sha1, sha256, sha512"

@tool
def base64_tool(text: str, mode: str = "encode"):
    """Encode or decode Base64 strings. mode = encode / decode."""
    deku_tool_flash("base64_tool [HACK]")
    try:
        if mode == "encode":
            return f"Encoded: {base64.b64encode(text.encode()).decode()}"
        return f"Decoded: {base64.b64decode(text.encode()).decode()}"
    except Exception as e:
        return f"Error: {e}"

@tool
def wifi_scanner(query: str = "scan"):
    """Scan and list nearby Wi-Fi networks with signal strength."""
    deku_tool_flash("wifi_scanner [HACK]")
    try:
        if platform.system() == "Windows":
            r = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, timeout=15
            )
            ssids   = re.findall(r'SSID\s+:\s(.+)',   r.stdout)
            signals = re.findall(r'Signal\s+:\s(.+)', r.stdout)
            if ssids:
                return f"Found {len(ssids)} networks:\n" + "\n".join(
                    f"  {s.strip()} — {sig.strip()}" for s, sig in zip(ssids, signals)
                )
            return "No Wi-Fi networks found or Wi-Fi is off."
        # Linux/Mac
        r = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
            capture_output=True, text=True, timeout=15
        )
        return r.stdout[:800] or "No networks found."
    except Exception as e:
        return f"Error: {e}"

@tool
def steganography(mode: str, image_path: str, message: str = "", output_path: str = "stego_out.png"):
    """Hide or extract a secret message in an image. mode = encode / decode."""
    deku_tool_flash("steganography [HACK]")
    try:
        from PIL import Image
        if mode == "encode":
            img    = Image.open(image_path).convert("RGB")
            pixels = list(img.getdata())
            binary = "".join(format(ord(c), "08b") for c in message) + "1111111111111110"
            if len(binary) > len(pixels) * 3:
                return "Message too long for this image."
            new_pixels, bi = [], 0
            for pixel in pixels:
                r, g, b = pixel
                if bi < len(binary): r = (r & ~1) | int(binary[bi]); bi += 1
                if bi < len(binary): g = (g & ~1) | int(binary[bi]); bi += 1
                if bi < len(binary): b = (b & ~1) | int(binary[bi]); bi += 1
                new_pixels.append((r, g, b))
            out = Image.new("RGB", img.size)
            out.putdata(new_pixels)
            out.save(output_path)
            return f"Message hidden in: {output_path}"
        # Decode
        img  = Image.open(image_path).convert("RGB")
        bits = "".join(str(c & 1) for px in img.getdata() for c in px)
        result = ""
        for i in range(0, len(bits) - 8, 8):
            c = chr(int(bits[i:i + 8], 2))
            if ord(c) == 0:
                break
            result += c
        return f"Hidden message: {result.strip()}" if result.strip() else "No hidden message found."
    except ImportError:
        return "Needs Pillow: pip install Pillow"
    except Exception as e:
        return f"Error: {e}"

@tool
def vulnerability_scanner(target: str):
    """Basic vulnerability check (open risky ports). ETHICAL USE: your own systems only."""
    deku_tool_flash("vuln_scanner [HACK]")
    findings = []
    try:
        ip = socket.gethostbyname(target)
        findings.append(f"Target: {target} ({ip})")
        risky_ports = {
            21: "FTP", 22: "SSH", 23: "Telnet", 80: "HTTP", 443: "HTTPS",
            3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis", 27017: "MongoDB",
            8080: "Alt-HTTP", 3389: "RDP", 5900: "VNC"
        }
        open_r = []
        for port, name in risky_ports.items():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((ip, port)) == 0:
                    open_r.append(f"Port {port} ({name})")
        if open_r:
            findings.append("⚠ Open risky ports found:")
            findings.extend(f"  → {p}" for p in open_r)
        else:
            findings.append("✔ No risky ports detected.")
        flag = "-n" if platform.system() == "Windows" else "-c"
        r    = subprocess.run(["ping", flag, "1", target], capture_output=True, text=True, timeout=5)
        findings.append("✔ Host is reachable." if r.returncode == 0 else "✖ Host unreachable.")
        return "\n".join(findings)
    except Exception as e:
        return f"Error: {e}"

# ── BLOCK 5: RAG MEMORY TOOLS (6) ─────────────────────────────────────────────

@tool
def rag_ingest_text(text: str, source_name: str = "manual"):
    """Feed raw text into DEKU's long-term memory."""
    deku_tool_flash("rag_ingest_text [RAG]")
    n = rag_engine.ingest(text, source=source_name)
    return f"Learned {n} new chunks from '{source_name}'!"

@tool
def rag_ingest_file(filepath: str):
    """Load a .txt, .md, or .pdf file into DEKU's memory."""
    deku_tool_flash("rag_ingest_file [RAG]")
    n = rag_engine.ingest_file(filepath)
    if n == -2: return "Need pymupdf for PDF support: pip install pymupdf"
    if n  < 0:  return f"Could not read file: {filepath}"
    return f"Learned {n} chunks from: {filepath}"

@tool
def rag_query(question: str):
    """Search DEKU's memory for relevant information about a topic."""
    deku_tool_flash("rag_query [RAG]")
    ctx = rag_engine.query_with_context(question, top_k=4)
    return ctx if ctx else "Nothing found in memory. Use rag_ingest_text to teach me!"

@tool
def rag_list_sources(query: str = "all"):
    """List all knowledge sources stored in DEKU's memory."""
    deku_tool_flash("rag_list_sources [RAG]")
    sources = rag_engine.list_sources()
    if sources:
        return f"{len(sources)} sources in memory:\n" + "\n".join(f"  · {s}" for s in sources)
    return "Memory is empty. Teach me something with rag_ingest_text!"

@tool
def rag_delete_source(source_name: str):
    """Remove all chunks from a specific source from DEKU's memory."""
    deku_tool_flash("rag_delete_source [RAG]")
    n = rag_engine.delete_source(source_name)
    return f"Removed {n} chunks from '{source_name}'."

@tool
def rag_clear_all(confirm: str = "no"):
    """Wipe all of DEKU's memory. Pass confirm='yes' to proceed."""
    deku_tool_flash("rag_clear_all [RAG]")
    if confirm.lower() != "yes":
        return "Safety check: pass confirm='yes' to wipe all memory."
    n = rag_engine.clear_all()
    return f"Memory cleared. Removed {n} chunks."

# ── BLOCK 6: GOD-LEVEL TOOLS (16) ─────────────────────────────────────────────

@tool
def auto_coder(task_description: str, language: str = "python"):
    """Generate a code skeleton file from a plain English description."""
    deku_tool_flash("auto_coder [GOD]")
    ext = {"python": "py", "javascript": "js", "html": "html", "bash": "sh"}.get(language, "txt")
    fn  = f"auto_{int(time.time())}.{ext}"
    templates = {
        "python":     f"# DEKU Auto-Code: {task_description}\n\ndef main():\n    # TODO: implement\n    print('DEKU: {task_description}')\n\nif __name__ == '__main__':\n    main()\n",
        "javascript": f"// DEKU Auto-Code: {task_description}\n\nfunction main() {{\n    // TODO: implement\n    console.log('DEKU: {task_description}');\n}}\nmain();\n",
        "html":       f"<!DOCTYPE html>\n<html>\n<head><title>DEKU: {task_description}</title></head>\n<body>\n<h1>{task_description}</h1>\n</body>\n</html>\n",
        "bash":       f"#!/bin/bash\n# DEKU Auto-Code: {task_description}\necho 'Running: {task_description}'\n",
    }
    content = templates.get(language, f"# {task_description}")
    os.makedirs("deku_workspace", exist_ok=True)
    with open(os.path.join("deku_workspace", fn), "w") as f:
        f.write(content)
    return f"Code skeleton saved: deku_workspace/{fn}"

@tool
def system_optimizer(action: str = "report"):
    """System optimizer. action = report (top hogs) / kill_heavy / temp_clean."""
    deku_tool_flash("system_optimizer [GOD]")
    if action == "report":
        procs = sorted(
            psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
            key=lambda p: p.info.get("memory_percent") or 0,
            reverse=True
        )[:8]
        return "Top RAM consumers:\n" + "\n".join(
            f"  {p.info['name']}: RAM={p.info['memory_percent']:.1f}% CPU={p.info['cpu_percent']:.1f}%"
            for p in procs
        )
    if action == "kill_heavy":
        killed = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
            if (p.info.get("cpu_percent") or 0) > 50:
                try:
                    p.kill()
                    killed.append(p.info["name"])
                except Exception:
                    pass
        return f"Killed: {', '.join(killed)}" if killed else "No CPU hogs found."
    if action == "temp_clean":
        temp_dir = os.environ.get("TEMP", "/tmp")
        count = 0
        for f in os.listdir(temp_dir):
            fp = os.path.join(temp_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    count += 1
            except Exception:
                pass
        return f"Cleaned {count} temp files from {temp_dir}."
    return "Use: report / kill_heavy / temp_clean"

@tool
def smart_summarizer(text_or_url: str):
    """Summarize a long text or a URL into key points."""
    deku_tool_flash("smart_summarizer [GOD]")
    if text_or_url.startswith("http"):
        try:
            return DuckDuckGoSearchRun().run(f"summary of {text_or_url}")[:500]
        except Exception as e:
            return f"Error: {e}"
    sentences = re.split(r'(?<=[.!?])\s+', text_or_url)
    n = len(sentences)
    if n < 3:
        return text_or_url
    picks = sentences[:2] + ([sentences[n // 2]] if n > 5 else []) + [sentences[-1]]
    return "Summary:\n" + " ".join(picks)

@tool
def multi_search(query: str, engines: str = "web,news"):
    """Search multiple engines at once. engines = web,news,academic,github,stackoverflow."""
    deku_tool_flash("multi_search [GOD]")
    ddg     = DuckDuckGoSearchRun()
    results = []
    for eng in [e.strip().lower() for e in engines.split(",")]:
        try:
            if   eng == "web":           results.append(f"[WEB]\n{ddg.run(query)[:300]}")
            elif eng == "news":          results.append(f"[NEWS]\n{ddg.run(query + ' latest news')[:300]}")
            elif eng == "academic":      results.append(f"[ACADEMIC]\n{ddg.run(query + ' research paper')[:300]}")
            elif eng == "github":        webbrowser.open(f"https://github.com/search?q={urllib.parse.quote(query)}"); results.append("[GITHUB] Browser opened.")
            elif eng == "stackoverflow": webbrowser.open(f"https://stackoverflow.com/search?q={urllib.parse.quote(query)}"); results.append("[SO] Browser opened.")
        except Exception:
            pass
    return "\n\n".join(results) if results else "No results."

@tool
def conversation_export(format: str = "txt"):
    """Export conversation history to a file. format = txt / json / md."""
    deku_tool_flash("conversation_export [GOD]")
    try:
        ts     = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fn     = f"deku_export_{ts}.{format}"
        notes  = open("deku_notes.txt", encoding="utf-8").read() if os.path.exists("deku_notes.txt") else ""
        hist   = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in mistral_history[-30:])
        if format == "json":
            content = json.dumps({"date": ts, "notes": notes, "history": mistral_history[-30:]}, indent=2)
        else:
            content = f"DEKU v6 Export  {ts}\n\nNOTES:\n{notes}\n\nCHAT HISTORY:\n{hist}"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Exported to: {fn}"
    except Exception as e:
        return f"Export error: {e}"

@tool
def screen_reader(query: str = "read"):
    """Take a screenshot and extract text using OCR (needs pytesseract)."""
    deku_tool_flash("screen_reader [GOD]")
    if not GUI_OK:
        return "pyautogui not available."
    try:
        img = pyautogui.screenshot()
        fn  = f"deku_screen_{int(time.time())}.png"
        img.save(fn)
        try:
            import pytesseract
            return f"Screen text:\n{pytesseract.image_to_string(img)[:600]}"
        except ImportError:
            return f"Screenshot saved: {fn}. Install pytesseract for OCR text extraction."
    except Exception as e:
        return f"Error: {e}"

@tool
def schedule_task(command: str, delay_seconds: int = 60, label: str = "Task"):
    """Schedule a shell command to run after N seconds in the background."""
    deku_tool_flash("schedule_task [GOD]")
    def _run():
        time.sleep(delay_seconds)
        console.print(f"\n{_c(C_GOLD, f'⚡ RUNNING: {label}')}")
        try:
            subprocess.Popen(command, shell=True)
            deku_voice.speak(f"Task complete: {label}")
        except Exception as e:
            console.print(_c(C_RED, f"Task failed: {e}"))
    threading.Thread(target=_run, daemon=True).start()
    return f"'{label}' scheduled to run in {delay_seconds} seconds."

@tool
def language_translator(text: str, target_language: str = "Hindi"):
    """Translate text to any language using web search."""
    deku_tool_flash("language_translator [GOD]")
    try:
        return DuckDuckGoSearchRun().run(f"translate to {target_language}: {text[:150]}")[:400]
    except Exception as e:
        return f"Error: {e}"

@tool
def code_debugger(filename: str):
    """Run a Python file from deku_workspace and capture its output and errors."""
    deku_tool_flash("code_debugger [GOD]")
    fp = os.path.join("deku_workspace", filename)
    try:
        r = subprocess.run([sys.executable, fp], capture_output=True, text=True, timeout=30)
        return f"OUTPUT:\n{r.stdout[:600] or '(none)'}\nERRORS:\n{r.stderr[:300] or '(none)'}"
    except subprocess.TimeoutExpired:
        return "Script timed out after 30 seconds."
    except FileNotFoundError:
        return f"File not found: {fp}"
    except Exception as e:
        return f"Error: {e}"

@tool
def ip_geolocation(ip_address: str):
    """Get location, ISP, and country info for any IP address."""
    deku_tool_flash("ip_geolocation [GOD]")
    try:
        return DuckDuckGoSearchRun().run(f"IP geolocation {ip_address} city country ISP")[:400]
    except Exception as e:
        return f"Error: {e}"

@tool
def system_benchmark(component: str = "cpu"):
    """Benchmark system performance. component = cpu / ram / disk."""
    deku_tool_flash("system_benchmark [GOD]")
    if component == "cpu":
        start = time.time()
        _     = sum(i ** 2 for i in range(500_000))
        t     = time.time() - start
        return f"CPU Score: {1/t*100:.1f}  ({t:.3f}s for 500k squares)"
    if component == "ram":
        start = time.time()
        arr   = [random.random() for _ in range(1_000_000)]
        _     = sum(arr)
        return f"RAM Bench: {time.time() - start:.3f}s for 1 million floats"
    if component == "disk":
        fn    = "_deku_bench.bin"
        start = time.time()
        with open(fn, "wb") as f:
            f.write(os.urandom(10 * 1024 * 1024))
        speed = 10 / (time.time() - start + 0.001)
        os.remove(fn)
        return f"Disk Write Speed: {speed:.1f} MB/s"
    return "Use: cpu / ram / disk"

@tool
def regex_tool(pattern: str, text: str, mode: str = "find"):
    """Apply regex to text. mode = find / replace / validate."""
    deku_tool_flash("regex_tool [GOD]")
    try:
        if mode == "find":
            matches = re.findall(pattern, text)
            return f"Found {len(matches)} matches: {matches[:20]}"
        if mode == "replace":
            parts  = text.split("|", 1)
            result = re.sub(pattern, parts[1] if len(parts) > 1 else "", parts[0])
            return f"Result: {result[:400]}"
        if mode == "validate":
            return f"'{text}' matches '{pattern}': {bool(re.fullmatch(pattern, text))}"
    except re.error as e:
        return f"Regex error: {e}"

@tool
def file_search(search_term: str, directory: str = ".", extensions: str = "txt,py,md,json"):
    """Search for a term inside files recursively."""
    deku_tool_flash("file_search [GOD]")
    exts  = tuple(f".{e.strip()}" for e in extensions.split(","))
    found = []
    try:
        for root, _, files in os.walk(directory):
            for fname in files:
                if fname.endswith(exts):
                    fp = os.path.join(root, fname)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if search_term.lower() in line.lower():
                                    found.append(f"{fp}:{i}: {line.strip()[:70]}")
                                    if len(found) >= 15:
                                        break
                    except Exception:
                        pass
            if len(found) >= 15:
                break
        return "\n".join(found) if found else f"'{search_term}' not found."
    except Exception as e:
        return f"Error: {e}"

@tool
def text_to_speech_file(text: str, filename: str = "deku_speech.wav"):
    """Convert any text to a WAV audio file using TTS."""
    deku_tool_flash("tts_file [GOD]")
    if not TTS_OK:
        return "pyttsx3 not available. Install: pip install pyttsx3"
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, filename)
        engine.runAndWait()
        return f"Audio saved: {filename}"
    except Exception as e:
        return f"Error: {e}"

@tool
def process_manager(action: str = "list"):
    """Process management. action = list (all) / top (by RAM) / services."""
    deku_tool_flash("process_manager [GOD]")
    if action == "list":
        procs = list(psutil.process_iter(["pid", "name", "status"]))[:15]
        return "\n".join(f"  PID:{p.info['pid']} {p.info['name']} [{p.info['status']}]" for p in procs)
    if action == "top":
        procs = sorted(
            psutil.process_iter(["pid", "name", "memory_percent"]),
            key=lambda p: p.info["memory_percent"] or 0,
            reverse=True
        )[:10]
        return "\n".join(f"  {p.info['name']}: {p.info['memory_percent']:.1f}% RAM" for p in procs)
    if action == "services":
        try:
            r = subprocess.run(["sc", "query", "type=", "running"], capture_output=True, text=True, timeout=10)
            return r.stdout[:800]
        except Exception:
            return "Service query unavailable on this system."
    return "Use: list / top / services"

@tool
def knowledge_snapshot(topic: str):
    """Deep-research a topic by combining web, news, and RAG memory."""
    deku_tool_flash("knowledge_snapshot [GOD]")
    ddg = DuckDuckGoSearchRun()
    try:    web  = ddg.run(topic)[:350]
    except: web  = "Web search failed."
    try:    news = ddg.run(f"{topic} latest news 2025")[:250]
    except: news = "News search failed."
    rag = rag_engine.query_with_context(topic, top_k=3)
    return (
        f"=== KNOWLEDGE SNAPSHOT: {topic.upper()} ===\n"
        f"[WEB]\n{web}\n\n"
        f"[NEWS]\n{news}\n\n"
        f"[MY MEMORY]\n{rag[:300] if rag else '(nothing stored yet)'}"
    )

# ── BLOCK 7: NEW UTILITY TOOLS (22) ───────────────────────────────────────────

@tool
def qr_code_generator(data: str, filename: str = "deku_qr.png"):
    """Generate a QR code image for any URL, text, or data."""
    deku_tool_flash("qr_code_generator [NEW]")
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        return f"QR code saved: {filename}  (encodes: {data[:50]})"
    except ImportError:
        return "Install qrcode: pip install qrcode[pil]"
    except Exception as e:
        return f"Error: {e}"

@tool
def text_diff(text1: str, text2: str):
    """Show a unified diff between two text strings."""
    deku_tool_flash("text_diff [NEW]")
    try:
        diff   = difflib.unified_diff(
            text1.splitlines(), text2.splitlines(),
            fromfile="original", tofile="modified", lineterm=""
        )
        result = "\n".join(list(diff)[:60])
        return result if result.strip() else "Texts are identical — no differences found."
    except Exception as e:
        return f"Error: {e}"

@tool
def zip_manager(action: str, archive_path: str, target: str = ""):
    """ZIP file manager. action = create / extract / list."""
    deku_tool_flash("zip_manager [NEW]")
    try:
        if action == "create":
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(target):
                    for root, _, files in os.walk(target):
                        for f in files:
                            fp = os.path.join(root, f)
                            zf.write(fp, os.path.relpath(fp, target))
                else:
                    zf.write(target)
            return f"Archive created: {archive_path}"
        if action == "extract":
            dest = target or os.path.splitext(archive_path)[0]
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest)
            return f"Extracted to: {dest}"
        if action == "list":
            with zipfile.ZipFile(archive_path, "r") as zf:
                names = zf.namelist()
            return f"Contents ({len(names)} files):\n" + "\n".join(f"  {n}" for n in names[:30])
        return "Use: create / extract / list"
    except Exception as e:
        return f"Error: {e}"

@tool
def csv_analyzer(filepath: str, action: str = "summary"):
    """Analyze a CSV file. action = summary / head / stats / columns."""
    deku_tool_flash("csv_analyzer [NEW]")
    try:
        rows = []
        with open(filepath, "r", encoding="utf-8", errors="ignore", newline="") as f:
            reader  = csv.DictReader(f)
            headers = reader.fieldnames or []
            for row in reader:
                rows.append(row)
                if len(rows) >= 1000:
                    break
        if action == "summary":
            return f"File: {filepath}\nRows: {len(rows)}  |  Columns: {len(headers)}\nHeaders: {', '.join(headers)}"
        if action == "head":
            return "\n".join(str(r) for r in rows[:5])
        if action == "columns":
            return f"Columns ({len(headers)}): {', '.join(headers)}"
        if action == "stats":
            stats = []
            for h in headers:
                vals = [r[h] for r in rows if r.get(h)]
                nums = []
                for v in vals:
                    try:
                        nums.append(float(v))
                    except Exception:
                        pass
                if nums:
                    stats.append(f"  {h}: min={min(nums):.2f}  max={max(nums):.2f}  avg={sum(nums)/len(nums):.2f}")
                else:
                    stats.append(f"  {h}: {len(set(vals))} unique text values")
            return "\n".join(stats)
        return "Use: summary / head / stats / columns"
    except Exception as e:
        return f"Error: {e}"

@tool
def json_formatter(json_input: str, action: str = "format"):
    """Format, minify, or validate JSON. action = format / minify / validate / keys."""
    deku_tool_flash("json_formatter [NEW]")
    try:
        data = json.loads(json_input)
        if action == "format":   return json.dumps(data, indent=2, ensure_ascii=False)[:1000]
        if action == "minify":   return json.dumps(data, separators=(",", ":"))[:1000]
        if action == "validate": return f"Valid JSON! Root type: {type(data).__name__}"
        if action == "keys":
            if isinstance(data, dict): return f"Keys ({len(data)}): {', '.join(str(k) for k in data)}"
            if isinstance(data, list): return f"Array with {len(data)} items. First item: {str(data[0])[:100]}"
        return "Use: format / minify / validate / keys"
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"
    except Exception as e:
        return f"Error: {e}"

@tool
def random_data_generator(data_type: str = "uuid", count: int = 5):
    """Generate random fake data. data_type = uuid / name / email / phone / ip / hex / lorem."""
    deku_tool_flash("random_data_generator [NEW]")
    results = []
    for _ in range(min(count, 20)):
        dt = data_type.lower()
        if dt == "uuid":
            results.append(str(uuid.uuid4()))
        elif dt == "email":
            name = "".join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
            dom  = random.choice(["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"])
            results.append(f"{name}@{dom}")
        elif dt == "phone":
            results.append(f"+91 {''.join(random.choices(string.digits, k=10))}")
        elif dt == "ip":
            results.append(f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}")
        elif dt == "hex":
            results.append("".join(random.choices("0123456789ABCDEF", k=16)))
        elif dt == "name":
            first = random.choice(["Aarav", "Virat", "Priya", "Ananya", "Raj", "Arjun", "Neha", "Dev"])
            last  = random.choice(["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Verma", "Rao"])
            results.append(f"{first} {last}")
        elif dt == "lorem":
            words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit"]
            results.append(" ".join(random.choices(words, k=10)) + ".")
        else:
            return "Use: uuid / name / email / phone / ip / hex / lorem"
    return f"Generated {len(results)} {data_type}(s):\n" + "\n".join(f"  {r}" for r in results)

@tool
def color_converter(color: str, to_format: str = "all"):
    """Convert a color between HEX, RGB, and HSL formats."""
    deku_tool_flash("color_converter [NEW]")
    try:
        r = g = b = 0
        color = color.strip()
        if color.startswith("#"):
            h = color.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        elif color.lower().startswith("rgb"):
            nums = re.findall(r'\d+', color)
            r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
        else:
            return "Use HEX (#RRGGBB) or RGB (rgb(R,G,B)) format."
        r2, g2, b2 = r/255, g/255, b/255
        cmax  = max(r2, g2, b2)
        cmin  = min(r2, g2, b2)
        delta = cmax - cmin
        l     = (cmax + cmin) / 2
        s     = 0 if delta == 0 else delta / (1 - abs(2 * l - 1))
        if   delta == 0: hval = 0
        elif cmax == r2: hval = 60 * (((g2 - b2) / delta) % 6)
        elif cmax == g2: hval = 60 * ((b2 - r2) / delta + 2)
        else:            hval = 60 * ((r2 - g2) / delta + 4)
        return (
            f"HEX: #{r:02X}{g:02X}{b:02X}\n"
            f"RGB: rgb({r}, {g}, {b})\n"
            f"HSL: hsl({hval:.0f}, {s*100:.1f}%, {l*100:.1f}%)\n"
            f"CSS: rgba({r}, {g}, {b}, 1.0)"
        )
    except Exception as e:
        return f"Error: {e}"

@tool
def timestamp_converter(value: str = "now", to_format: str = "all"):
    """Convert timestamps. value = 'now' / unix epoch number / date string."""
    deku_tool_flash("timestamp_converter [NEW]")
    try:
        if value.lower() == "now":
            now = datetime.datetime.now()
        elif value.isdigit():
            now = datetime.datetime.fromtimestamp(int(value))
        else:
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    now = datetime.datetime.strptime(value, fmt)
                    break
                except Exception:
                    pass
            else:
                return f"Could not parse date: {value}"
        return (
            f"Local:    {now.strftime('%A, %d %B %Y  %H:%M:%S')}\n"
            f"ISO 8601: {now.isoformat()}\n"
            f"Unix:     {int(now.timestamp())}\n"
            f"UTC:      {datetime.datetime.utcfromtimestamp(now.timestamp()).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Week:     {now.isocalendar()[1]} of {now.year}"
        )
    except Exception as e:
        return f"Error: {e}"

@tool
def word_counter(text: str):
    """Count words, characters, sentences, paragraphs, and estimate reading time."""
    deku_tool_flash("word_counter [NEW]")
    try:
        words     = len(text.split())
        chars     = len(text)
        chars_ns  = len(text.replace(" ", ""))
        sentences = len(re.findall(r'[.!?]+', text)) or 1
        paras     = len([p for p in text.split("\n\n") if p.strip()]) or 1
        read_min  = max(1, round(words / 200))
        return (
            f"Words:      {words}\n"
            f"Characters: {chars} ({chars_ns} without spaces)\n"
            f"Sentences:  {sentences}\n"
            f"Paragraphs: {paras}\n"
            f"Read time:  ~{read_min} min at 200 wpm"
        )
    except Exception as e:
        return f"Error: {e}"

@tool
def bulk_rename(directory: str, pattern: str, replacement: str, dry_run: bool = True):
    """Rename files in bulk using regex. dry_run=True shows preview without changing files."""
    deku_tool_flash("bulk_rename [NEW]")
    try:
        files = [f for f in os.listdir(directory) if re.search(pattern, f)]
        if not files:
            return f"No files matched pattern: {pattern}"
        results = []
        for f in files[:20]:
            new_name = re.sub(pattern, replacement, f)
            results.append(f"  {f}  →  {new_name}")
            if not dry_run:
                os.rename(os.path.join(directory, f), os.path.join(directory, new_name))
        label = "PREVIEW (no changes made):" if dry_run else "RENAMED:"
        return f"{label}\n" + "\n".join(results)
    except Exception as e:
        return f"Error: {e}"

@tool
def dir_tree(path: str = ".", max_depth: int = 3):
    """Display a directory tree structure with file sizes."""
    deku_tool_flash("dir_tree [NEW]")
    try:
        lines = [f"📁 {os.path.abspath(path)}"]
        def walk(p, depth, prefix=""):
            if depth > max_depth:
                return
            try:
                items = sorted(os.listdir(p))
            except PermissionError:
                return
            for i, item in enumerate(items[:20]):
                fp        = os.path.join(p, item)
                is_last   = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                size      = ""
                if os.path.isfile(fp):
                    try:
                        size = f"  [{os.path.getsize(fp) // 1024}KB]"
                    except Exception:
                        pass
                lines.append(f"{prefix}{connector}{item}{size}")
                if os.path.isdir(fp):
                    ext = "    " if is_last else "│   "
                    walk(fp, depth + 1, prefix + ext)
        walk(path, 1)
        return "\n".join(lines[:80])
    except Exception as e:
        return f"Error: {e}"

@tool
def env_manager(action: str = "list", key: str = "", value: str = ""):
    """Manage environment variables. action = list / get / set / delete."""
    deku_tool_flash("env_manager [NEW]")
    if action == "list":
        items = list(os.environ.items())[:20]
        return "\n".join(f"  {k} = {v[:50]}" for k, v in items)
    if action == "get":
        return f"{key} = {os.environ.get(key, 'NOT SET')}"
    if action == "set":
        os.environ[key] = value
        return f"Set: {key} = {value}"
    if action == "delete":
        if key in os.environ:
            del os.environ[key]
            return f"Deleted: {key}"
        return f"Key not found: {key}"
    return "Use: list / get / set / delete"

@tool
def ping_sweep(network: str = "192.168.1", start: int = 1, end: int = 20):
    """Sweep a network range to find live hosts. ETHICAL USE: your own network."""
    deku_tool_flash("ping_sweep [NEW/HACK]")
    live    = []
    flag    = "-n" if platform.system() == "Windows" else "-c"
    threads = []

    def check(ip):
        try:
            r = subprocess.run(["ping", flag, "1", "-w", "500", ip], capture_output=True, timeout=3)
            if r.returncode == 0:
                live.append(ip)
        except Exception:
            pass

    for i in range(start, min(end + 1, start + 50)):
        ip = f"{network}.{i}"
        t  = threading.Thread(target=check, args=(ip,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=5)

    if live:
        return f"Live hosts in {network}.{start}-{end}:\n" + "\n".join(f"  ✔ {ip}" for ip in sorted(live))
    return "No live hosts found in range."

@tool
def ssl_checker(domain: str):
    """Check SSL certificate details (expiry, issuer, SANs) for a domain."""
    deku_tool_flash("ssl_checker [NEW/HACK]")
    try:
        import ssl
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            cert = s.getpeercert()
        subject   = dict(x[0] for x in cert.get("subject", []))
        issuer    = dict(x[0] for x in cert.get("issuer", []))
        not_after = cert.get("notAfter", "N/A")
        san       = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
        return (
            f"Domain:  {domain}\n"
            f"CN:      {subject.get('commonName', 'N/A')}\n"
            f"Issuer:  {issuer.get('organizationName', 'N/A')}\n"
            f"Expires: {not_after}\n"
            f"SANs:    {', '.join(san[:5])}"
        )
    except Exception as e:
        return f"SSL check error: {e}"

@tool
def http_tester(url: str, method: str = "GET", headers: str = "", body: str = ""):
    """Test an HTTP/HTTPS endpoint and show status, headers, and body preview."""
    deku_tool_flash("http_tester [NEW]")
    try:
        import urllib.request
        req_headers = {}
        if headers:
            for h in headers.split(";"):
                if ":" in h:
                    k, v = h.split(":", 1)
                    req_headers[k.strip()] = v.strip()
        req = urllib.request.Request(
            url,
            method=method.upper(),
            data=body.encode() if body else None,
            headers=req_headers
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status    = resp.status
            resp_hdrs = dict(resp.headers)
            content   = resp.read(500).decode("utf-8", errors="replace")
        return (
            f"URL:          {url}\n"
            f"Method:       {method.upper()}\n"
            f"Status:       {status}\n"
            f"Content-Type: {resp_hdrs.get('Content-Type', 'N/A')}\n"
            f"Body (500B):  {content}"
        )
    except Exception as e:
        return f"HTTP error: {e}"

@tool
def cron_helper(description: str):
    """Convert a plain English schedule to a cron expression."""
    deku_tool_flash("cron_helper [NEW]")
    desc = description.lower()
    if "every minute"  in desc: return "* * * * *       (every minute)"
    if "every hour"    in desc: return "0 * * * *       (every hour at :00)"
    if "every day"     in desc:
        m = re.search(r'(\d+)\s*(am|pm)?', desc)
        h = int(m.group(1)) if m else 0
        if m and "pm" in desc and h < 12: h += 12
        return f"0 {h} * * *       (every day at {h:02d}:00)"
    if "every week"  in desc: return "0 9 * * 1        (every Monday at 09:00)"
    if "every month" in desc: return "0 9 1 * *        (1st of every month at 09:00)"
    if "midnight"    in desc: return "0 0 * * *        (daily at midnight)"
    if "noon"        in desc: return "0 12 * * *       (daily at noon)"
    if "weekday"     in desc: return "0 9 * * 1-5      (weekdays at 09:00)"
    if "weekend"     in desc: return "0 10 * * 6,0     (weekends at 10:00)"
    return "Could not parse. Examples:\n  '* * * * *'   = every minute\n  '0 9 * * *'   = daily 9am\n  See: https://crontab.guru"

@tool
def git_summary(repo_path: str = "."):
    """Show git branch, status, recent commits, and remotes for a repo."""
    deku_tool_flash("git_summary [NEW]")
    try:
        def git(cmd):
            r = subprocess.run(["git"] + cmd, cwd=repo_path, capture_output=True, text=True, timeout=10)
            return r.stdout.strip() or r.stderr.strip()
        return (
            f"Branch:  {git(['rev-parse', '--abbrev-ref', 'HEAD'])}\n\n"
            f"Status:\n{git(['status', '--short'])[:300] or '(clean)'}\n\n"
            f"Recent commits:\n{git(['log', '--oneline', '-8'])}\n\n"
            f"Remotes:\n{git(['remote', '-v'])[:200] or '(none)'}"
        )
    except Exception as e:
        return f"Git error: {e}. Is git installed and is this inside a repository?"

@tool
def ascii_art(text: str, style: str = "standard"):
    """Generate ASCII art text. style = standard / block / banner."""
    deku_tool_flash("ascii_art [NEW]")
    try:
        import pyfiglet
        fonts  = {"block": "block", "standard": "standard", "banner": "banner3"}
        font   = fonts.get(style, "standard")
        return pyfiglet.figlet_format(text, font=font)[:600]
    except ImportError:
        # Simple fallback if pyfiglet not installed
        result = "  ".join(f"[{c}]" for c in text.upper()[:12])
        return f"ASCII: {result}\n(Install for better art: pip install pyfiglet)"
    except Exception as e:
        return f"Error: {e}"

@tool
def memory_dump(query: str = "all"):
    """Show a summary of the current Mistral conversation history."""
    deku_tool_flash("memory_dump [NEW]")
    if not mistral_history:
        return "No conversation history yet. Start chatting!"
    lines = [
        f"  [{i+1}] {m['role'].upper()}: {m['content'][:80]}..."
        for i, m in enumerate(mistral_history[-20:])
    ]
    return f"Last {min(20, len(mistral_history))} messages:\n" + "\n".join(lines)

@tool
def todo_manager(action: str = "list", task: str = "", task_id: str = ""):
    """Manage a persistent TODO list. action = add / list / done / delete / clear."""
    deku_tool_flash("todo_manager [NEW]")
    todo_file = "deku_todos.json"

    # Load existing todos (or start fresh)
    try:
        todos = json.loads(open(todo_file).read()) if os.path.exists(todo_file) else []
    except Exception:
        todos = []

    def save():
        open(todo_file, "w").write(json.dumps(todos, indent=2))

    if action == "add":
        if not task:
            return "Provide a task description."
        tid = str(len(todos) + 1)
        todos.append({
            "id": tid, "task": task, "done": False,
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        save()
        return f"✅ Added task #{tid}: {task}"

    if action == "list":
        if not todos:
            return "No todos yet! Add one: todo_manager(action='add', task='Your task')"
        undone = [t for t in todos if not t["done"]]
        done   = [t for t in todos if t["done"]]
        lines  = []
        for t in undone: lines.append(f"  ⬜ #{t['id']} {t['task']}  (created {t['created']})")
        for t in done:   lines.append(f"  ✅ #{t['id']} {t['task']}  DONE")
        return f"TODO List — {len(undone)} pending, {len(done)} done:\n" + "\n".join(lines)

    if action == "done":
        for t in todos:
            if t["id"] == task_id:
                t["done"] = True
                save()
                return f"Marked done: task #{task_id}"
        return f"Task #{task_id} not found."

    if action == "delete":
        before = len(todos)
        todos  = [t for t in todos if t["id"] != task_id]
        save()
        return f"Deleted task #{task_id}." if len(todos) < before else "Task not found."

    if action == "clear":
        todos = []
        save()
        return "All todos cleared!"

    return "Use: list / add / done / delete / clear"

@tool
def math_plotter(expression: str, x_range: str = "-10,10"):
    """Plot a math function. Saves PNG if matplotlib is installed, else ASCII art."""
    deku_tool_flash("math_plotter [NEW]")
    try:
        lo, hi = map(float, x_range.split(","))
        x_vals = [lo + (hi - lo) * i / 40 for i in range(41)]
        y_vals = []
        for xv in x_vals:
            ns = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            ns["x"] = xv
            try:
                y_vals.append(float(eval(expression, {"__builtins__": {}}, ns)))
            except Exception:
                y_vals.append(None)

        # Try matplotlib first (much nicer output)
        try:
            import matplotlib.pyplot as plt
            xs = [x for x, y in zip(x_vals, y_vals) if y is not None]
            ys = [y for y in y_vals if y is not None]
            plt.figure(figsize=(8, 4))
            plt.plot(xs, ys, "c-", linewidth=2)
            plt.title(f"f(x) = {expression}")
            plt.xlabel("x")
            plt.ylabel("f(x)")
            plt.grid(True)
            fn = f"deku_plot_{int(time.time())}.png"
            plt.savefig(fn)
            plt.close()
            return f"Plot saved: {fn}"
        except ImportError:
            pass

        # ASCII fallback
        valid = [(x, y) for x, y in zip(x_vals, y_vals) if y is not None]
        if not valid:
            return "Could not evaluate expression."
        ymin = min(y for _, y in valid)
        ymax = max(y for _, y in valid)
        height, width = 12, 41
        grid = [[" "] * width for _ in range(height)]
        for col, (x, y) in enumerate(valid[:width]):
            row = int((ymax - y) / (ymax - ymin + 1e-9) * (height - 1)) if ymax != ymin else height // 2
            row = max(0, min(height - 1, row))
            grid[row][col] = "●"
        lines = [f"  f(x) = {expression}"]
        lines += ["|" + "".join(row) + "|" for row in grid]
        lines += [f"  x: [{lo:.1f} → {hi:.1f}]   y: [{ymin:.2f} → {ymax:.2f}]"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

# ══════════════════════════════════════════════════════════════════════════════
#  TOOL REGISTRY — collect all tools into a list and lookup dict
# ══════════════════════════════════════════════════════════════════════════════

deku_tools = [
    # Core (15)
    generate_image, web_search, system_control, coding_master, read_code_file,
    system_stats, youtube_search, weather_info, volume_control, brightness_control,
    note_taker, currency_converter, motivation_booster, close_window, list_files,
    # Comm & System (8)
    send_email, send_whatsapp, file_manager, set_alarm, calculator,
    news_headlines, app_launcher, clipboard_manager,
    # General (8)
    maps_search, password_generator, dictionary_lookup, stock_price,
    network_info, kill_process, joke_fact_teller, pomodoro_timer,
    # Hacker (8)
    port_scanner, ping_traceroute, dns_whois_lookup, hash_generator,
    base64_tool, wifi_scanner, steganography, vulnerability_scanner,
    # RAG Memory (6)
    rag_ingest_text, rag_ingest_file, rag_query,
    rag_list_sources, rag_delete_source, rag_clear_all,
    # God-Level (16)
    auto_coder, system_optimizer, smart_summarizer, multi_search,
    conversation_export, screen_reader, schedule_task, language_translator,
    code_debugger, ip_geolocation, system_benchmark, regex_tool,
    file_search, text_to_speech_file, process_manager, knowledge_snapshot,
    # New Utility Tools (22)
    qr_code_generator, text_diff, zip_manager, csv_analyzer,
    json_formatter, random_data_generator, color_converter, timestamp_converter,
    word_counter, bulk_rename, dir_tree, env_manager,
    ping_sweep, ssl_checker, http_tester, cron_helper,
    git_summary, ascii_art, memory_dump, todo_manager,
    math_plotter, language_translator,  # language_translator listed twice — de-duped below
]

# Remove duplicate tool names (language_translator appears twice above)
seen_names  = set()
unique_tools = []
for t in deku_tools:
    if t.name not in seen_names:
        seen_names.add(t.name)
        unique_tools.append(t)
deku_tools = unique_tools

# Fast lookup dictionary: tool_name → tool function
TOOL_DISPATCH = {t.name: t for t in deku_tools}

# ══════════════════════════════════════════════════════════════════════════════
#  TOOL CALL PARSER & RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def _parse_tool_call(text: str):
    """
    Look for a tool call in the model's response text.
    Expected format: TOOL:tool_name|{"arg": "value"}

    Returns (tool_name, args_dict) or (None, None) if no call found.
    """
    # Try to match: TOOL:name|{...}
    match = re.search(r'TOOL:(\w+)\|(\{.*?\})', text, re.DOTALL)
    if match:
        name = match.group(1)
        try:
            args = json.loads(match.group(2))
            return name, args
        except Exception:
            pass

    # Fallback: TOOL:name with no args
    match2 = re.search(r'TOOL:(\w+)', text)
    if match2:
        return match2.group(1), {}

    return None, None


def _run_tool(name: str, args: dict) -> str:
    """Look up a tool by name and call it with the given arguments."""
    t = TOOL_DISPATCH.get(name)
    if not t:
        return f"Unknown tool: '{name}'. Check tool name spelling."
    try:
        return str(t.invoke(args))
    except Exception as e:
        return f"Tool '{name}' error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN QUERY PROCESSOR
# ══════════════════════════════════════════════════════════════════════════════

def process_query(query: str) -> str:
    """
    Main function that handles a user message end-to-end:
    1. Show the user's query in a nice box
    2. Check RAG memory for relevant context
    3. Send to Mistral AI
    4. If Mistral calls a tool → run it → send result back to Mistral
    5. Return final reply string

    Supports up to 3 rounds of tool calls per message.
    """
    # Display user's message
    console.print(
        f"\n{_c(C_DIM, '╔' + '═' * 62 + '╗')}\n"
        f"{_c(C_DIM, '║')}  {_c(C_GREEN, '◈')} "
        f"{_c(C_CYAN, f'{USER_NAME}  //')}  {_c(C_WHITE, query)}\n"
        f"{_c(C_DIM, '╚' + '═' * 62 + '╝')}"
    )

    # Add any relevant memory context to the query
    rag_ctx    = rag_engine.query_with_context(query, top_k=3) if query else ""
    full_query = f"{query}\n\n{rag_ctx}" if rag_ctx else query

    # Get the system prompt
    system = build_system_prompt()

    # Call Mistral AI (with thinking spinner)
    with deku_thinking() as prog:
        prog.add_task("", total=None)
        reply = mistral_chat(full_query, system_prompt=system)

    # Tool calling loop — up to 3 rounds
    for _ in range(3):
        tool_name, tool_args = _parse_tool_call(reply)
        if not tool_name:
            break  # No tool call found — return the reply as-is

        # Run the tool
        deku_tool_flash(tool_name)
        tool_result = _run_tool(tool_name, tool_args)

        # Show a preview of the tool result
        console.print(f"\n  {_c(C_DIM, '⮕ RESULT:')} {_c(C_WHITE, str(tool_result)[:200])}")

        # Feed the tool result back to Mistral so it can explain it
        with deku_thinking() as prog:
            prog.add_task("", total=None)
            reply = mistral_chat(
                f"Tool '{tool_name}' returned:\n{tool_result}\n\nSummarize this result in a friendly way for {USER_NAME}.",
                system_prompt=system
            )

    return reply


# ══════════════════════════════════════════════════════════════════════════════
#  INPUT HANDLER — supports text, voice [S], and voice toggle [V]
# ══════════════════════════════════════════════════════════════════════════════

def get_input_with_hotkeys() -> str:
    """
    Read user input from the terminal.
    Special single-key commands:
    - 's' → activate microphone (5 second recording)
    - 'v' → toggle voice output on/off
    """
    deku_input_prompt()
    try:
        raw = input().strip()
    except EOFError:
        return "exit"

    if raw.lower() == "s":
        if not SR_OK or not AUDIO_OK:
            console.print(_c(C_RED, "  ✖ Voice input unavailable."))
            console.print(_c(C_DIM, "  Install: pip install SpeechRecognition sounddevice scipy"))
            return ""
        console.print(f"  {_c(C_GOLD, '🎙  [S] SPEAK MODE')} — Recording 5 seconds...")
        return capture_audio(5)

    if raw.lower() == "v":
        deku_voice.toggle_voice_output()
        return ""

    return raw


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN TEXT CHAT LOOP
# ══════════════════════════════════════════════════════════════════════════════

def text_input_engine():
    """The main terminal chat loop — runs until the user says 'exit'."""
    os.system("cls" if platform.system() == "Windows" else "clear")
    deku_banner()
    deku_matrix_flash(4)
    deku_status_table()
    deku_section(f"BOOT COMPLETE — {len(deku_tools)} TOOLS — MISTRAL AI — ONLINE")

    # Show hotkey hints
    console.print(
        f"\n  {_c(C_GOLD, '◈ HOTKEYS:')}  "
        f"{_c(C_GREEN, '[S]')} Voice Input  ·  "
        f"{_c(C_GREEN, '[V]')} Toggle Voice  ·  "
        f"{_c(C_GREEN, '[help]')} Commands\n"
    )

    # Warn if API key is missing
    if not mistral_client:
        console.print(_c(C_RED, "\n  ⚠  MISTRAL_API_KEY not set in .env — AI responses will fail!"))
        console.print(_c(C_DIM, "  Get a free key at: https://console.mistral.ai\n"))

    # Greeting message
    h     = datetime.datetime.now().hour
    greet = "morning" if h < 12 else "afternoon" if h < 17 else "evening"
    deku_voice.speak(
        f"Yo! Good {greet}, {USER_NAME}! "
        f"DEKU v6 is online, powered by Mistral AI with {len(deku_tools)} tools. "
        f"RAG memory: {len(rag_engine.documents)} chunks. What's up?"
    )

    # Main chat loop
    while True:
        try:
            query = get_input_with_hotkeys()
            if not query:
                continue

            ql = query.lower().strip()

            # Exit commands
            if any(x in ql for x in ("exit", "bye", "goodbye", "quit", "shutdown deku", "see you")):
                deku_voice.speak(f"Later, {USER_NAME}! DEKU going offline. Stay awesome!")
                console.print(f"\n{_c(C_GREEN, '  ◈  DEKU OFFLINE  ◈')}\n")
                break

            # Built-in commands (no AI needed)
            if ql in ("cls", "clear"):
                os.system("cls" if platform.system() == "Windows" else "clear")
                deku_banner()
                continue
            if ql == "status":   deku_status_table();       continue
            if ql == "tools":    _show_tools();             continue
            if ql == "new":      _show_new_tools();         continue
            if ql == "hack":     _show_hack_tools();        continue
            if ql == "rag":      _show_rag_tools();         continue
            if ql == "god":      _show_god_tools();         continue
            if ql == "help":     _show_help();              continue
            if ql == "history":  deku_voice.speak(memory_dump.invoke({"query": "all"})); continue
            if ql == "todos":    deku_voice.speak(todo_manager.invoke({"action": "list"})); continue

            # Process through Mistral AI
            reply = process_query(query)
            deku_voice.speak(reply)
            time.sleep(0.1)

        except KeyboardInterrupt:
            deku_voice.speak("Interrupted. Later, bro!")
            break
        except Exception as e:
            console.print(f"\n  {_c(C_RED, f'✖  ERROR: {e}')}")
            continue


# ══════════════════════════════════════════════════════════════════════════════
#  VOICE WAKE-WORD ENGINE (--voice flag)
# ══════════════════════════════════════════════════════════════════════════════

def autonomous_engine():
    """
    Hands-free mode: constantly listens for the wake word ('deku'),
    then takes a 6-second voice command.
    """
    os.system("cls" if platform.system() == "Windows" else "clear")
    deku_banner()
    deku_status_table()
    deku_voice._v_mode = True  # Always speak in voice mode
    deku_voice.speak(f"Voice mode on! Say '{WAKE_WORD}' to talk to me, {USER_NAME}!")

    while True:
        try:
            with Live(console=console, refresh_per_second=4) as live:
                live.update(
                    f"  {_c(C_DIM, '◌  PASSIVE LISTENING')} · Say {_c(C_GREEN, WAKE_WORD.upper())}"
                )
                heard = capture_audio(3)

            if WAKE_WORD in heard:
                deku_voice.speak("Yo! I'm here. What do you need?")
                query = capture_audio(6)
                if not query:
                    deku_voice.speak("Didn't catch that. Try again?")
                    continue
                if any(x in query for x in ("exit", "bye", "shutdown", "stop", "quit")):
                    deku_voice.speak(f"Alright, {USER_NAME}! Signing off. Later!")
                    break
                reply = process_query(query)
                deku_voice.speak(reply)
                time.sleep(1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"  {_c(C_RED, f'Error: {e}')}")
            continue


# ══════════════════════════════════════════════════════════════════════════════
#  HELP DISPLAY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _show_tools():
    """Display all 75 tools in a formatted table."""
    t = Table(
        title=f"◈  DEKU v6  ·  {len(deku_tools)} TOOLS  ◈",
        box=box.DOUBLE_EDGE, title_style=C_GREEN,
        header_style=C_CYAN, border_style="cyan", show_lines=True
    )
    t.add_column("#",       style=C_DIM,   justify="center", min_width=4)
    t.add_column("TOOL",    style=C_GREEN, justify="left",   min_width=28)
    t.add_column("MOD",     style=C_GOLD,  justify="center", min_width=8)
    t.add_column("PURPOSE", style=C_WHITE, justify="left",   min_width=38)

    rows = [
        ("generate_image","Core","AI image from text"),("web_search","Core","DuckDuckGo search"),
        ("system_control","Core","PC control"),("coding_master","Core","Write code to file"),
        ("read_code_file","Core","Read workspace file"),("system_stats","Core","CPU/RAM/Disk/Bat"),
        ("youtube_search","Core","Open YouTube"),("weather_info","Core","Live weather"),
        ("volume_control","Core","Volume up/down/mute"),("brightness_control","Core","Screen brightness"),
        ("note_taker","Core","Save timestamped note"),("currency_converter","Core","FX conversion"),
        ("motivation_booster","Core","Motivational quote"),("close_window","Core","Alt+F4 window"),
        ("list_files","Core","List directory"),
        ("send_email","Comm","Email draft"),("send_whatsapp","Comm","WhatsApp Web"),
        ("file_manager","Files","Copy/move/delete/rename"),("set_alarm","Timer","Voice alarm"),
        ("calculator","Math","Full math eval"),("news_headlines","Web","Latest news"),
        ("app_launcher","Sys","Launch any app"),("clipboard_manager","Sys","Clipboard R/W"),
        ("maps_search","Web","Google Maps"),("password_generator","Sec","Strong password"),
        ("dictionary_lookup","Web","Word definition"),("stock_price","Web","Live stocks"),
        ("network_info","Net","IP + data stats"),("kill_process","Sys","Kill process"),
        ("joke_fact_teller","Fun","Joke or fun fact"),("pomodoro_timer","Timer","Focus sessions"),
        ("port_scanner","HACK","TCP port scan"),("ping_traceroute","HACK","Ping/traceroute"),
        ("dns_whois_lookup","HACK","DNS + WHOIS"),("hash_generator","HACK","Crypto hash"),
        ("base64_tool","HACK","Base64 encode/decode"),("wifi_scanner","HACK","Wi-Fi networks"),
        ("steganography","HACK","Hide msg in image"),("vulnerability_scanner","HACK","Vuln check"),
        ("rag_ingest_text","RAG","Learn from text"),("rag_ingest_file","RAG","Learn from file"),
        ("rag_query","RAG","Query memory"),("rag_list_sources","RAG","List sources"),
        ("rag_delete_source","RAG","Delete source"),("rag_clear_all","RAG","Wipe memory"),
        ("auto_coder","GOD","Natural lang → code"),("system_optimizer","GOD","Optimize PC"),
        ("smart_summarizer","GOD","Summarize text/URL"),("multi_search","GOD","Multi-engine"),
        ("conversation_export","GOD","Export history"),("screen_reader","GOD","OCR screenshot"),
        ("schedule_task","GOD","Delayed command"),("language_translator","GOD","Translate"),
        ("code_debugger","GOD","Run + debug Python"),("ip_geolocation","GOD","IP location"),
        ("system_benchmark","GOD","CPU/RAM/Disk bench"),("regex_tool","GOD","Regex ops"),
        ("file_search","GOD","Search in files"),("text_to_speech_file","GOD","TTS → WAV"),
        ("process_manager","GOD","Process control"),("knowledge_snapshot","GOD","Deep research"),
        ("qr_code_generator","NEW","QR code image"),("text_diff","NEW","Text diff"),
        ("zip_manager","NEW","ZIP archive"),("csv_analyzer","NEW","CSV stats"),
        ("json_formatter","NEW","JSON format/validate"),("random_data_generator","NEW","Fake data"),
        ("color_converter","NEW","HEX/RGB/HSL"),("timestamp_converter","NEW","Time convert"),
        ("word_counter","NEW","Word/char count"),("bulk_rename","NEW","Batch rename"),
        ("dir_tree","NEW","Folder tree"),("env_manager","NEW","ENV vars"),
        ("ping_sweep","NEW","Host sweep"),("ssl_checker","NEW","SSL cert check"),
        ("http_tester","NEW","HTTP endpoint"),("cron_helper","NEW","Cron expr helper"),
        ("git_summary","NEW","Git status"),("ascii_art","NEW","ASCII art"),
        ("memory_dump","NEW","Chat history"),("todo_manager","NEW","TODO list"),
        ("math_plotter","NEW","Math plot PNG"),
    ]
    c_map = {"HACK": C_RED, "GOD": C_GOLD, "RAG": C_PINK, "Core": C_CYAN, "NEW": C_ORANGE}
    for i, (name, mod, desc) in enumerate(rows, 1):
        col = c_map.get(mod, C_WHITE)
        t.add_row(str(i), name, f"[{col}]{mod}[/{col}]", desc)
    console.print(t)

def _show_new_tools():
    """Show all 22 new tools with usage examples."""
    t = Table(title="◈  22 NEW TOOLS  ◈", box=box.DOUBLE_EDGE,
              title_style=C_ORANGE, header_style=C_GREEN, border_style="bright_red", show_lines=True)
    t.add_column("TOOL",  style=C_ORANGE, min_width=26)
    t.add_column("USAGE", style=C_WHITE,  min_width=54)
    examples = [
        ("qr_code_generator",     'qr_code_generator("https://example.com")'),
        ("text_diff",             'text_diff("old text", "new text")'),
        ("zip_manager",           'zip_manager("create", "out.zip", "my_folder/")'),
        ("csv_analyzer",          'csv_analyzer("data.csv", "stats")'),
        ("json_formatter",        "json_formatter('{\"a\":1}', 'format')"),
        ("random_data_generator", 'random_data_generator("email", 5)'),
        ("color_converter",       'color_converter("#FF5733")'),
        ("timestamp_converter",   'timestamp_converter("now")'),
        ("word_counter",          'word_counter("Paste your text here...")'),
        ("bulk_rename",           'bulk_rename("./imgs", r"\\.jpg", "_photo.jpg")'),
        ("dir_tree",              'dir_tree(".", max_depth=3)'),
        ("env_manager",           'env_manager("list")'),
        ("ping_sweep",            'ping_sweep("192.168.1", 1, 50)'),
        ("ssl_checker",           'ssl_checker("google.com")'),
        ("http_tester",           'http_tester("https://api.example.com", "GET")'),
        ("cron_helper",           'cron_helper("every day at 9am")'),
        ("git_summary",           'git_summary(".")'),
        ("ascii_art",             'ascii_art("DEKU", "block")'),
        ("memory_dump",           'memory_dump()'),
        ("todo_manager",          "todo_manager('add', 'Fix the bug today')"),
        ("math_plotter",          'math_plotter("sin(x)", "-10,10")'),
    ]
    for name, usage in examples:
        t.add_row(name, usage)
    console.print(t)

def _show_hack_tools():
    """Show hacker tools with usage examples."""
    t = Table(title="◈  HACK MODULE  ◈", box=box.DOUBLE_EDGE,
              title_style=C_HACK, header_style=C_GREEN, border_style="green", show_lines=True)
    t.add_column("TOOL",  style=C_HACK,  min_width=24)
    t.add_column("USAGE", style=C_WHITE, min_width=50)
    for name, usage in [
        ("port_scanner",          'port_scanner("192.168.1.1", 1, 1024)'),
        ("ping_traceroute",       'ping_traceroute("google.com", "ping")'),
        ("dns_whois_lookup",      'dns_whois_lookup("example.com")'),
        ("hash_generator",        'hash_generator("mypassword", "sha256")'),
        ("base64_tool",           'base64_tool("hello world", "encode")'),
        ("wifi_scanner",          'wifi_scanner("scan")'),
        ("steganography",         'steganography("encode", "img.png", "secret msg")'),
        ("vulnerability_scanner", 'vulnerability_scanner("192.168.1.1")'),
        ("ping_sweep",            'ping_sweep("192.168.1", 1, 50)   [NEW]'),
        ("ssl_checker",           'ssl_checker("example.com")        [NEW]'),
        ("http_tester",           'http_tester("https://api.io/v1")  [NEW]'),
    ]:
        t.add_row(name, usage)
    console.print(t)

def _show_rag_tools():
    """Show RAG memory tools."""
    t = Table(title="◈  RAG MEMORY MODULE  ◈", box=box.DOUBLE_EDGE,
              title_style=C_PINK, header_style=C_CYAN, border_style="magenta", show_lines=True)
    t.add_column("TOOL",  style=C_PINK,  min_width=22)
    t.add_column("USAGE", style=C_WHITE, min_width=52)
    for name, usage in [
        ("rag_ingest_text",   'rag_ingest_text("Your notes here...", "source_name")'),
        ("rag_ingest_file",   'rag_ingest_file("docs/manual.txt")'),
        ("rag_query",         'rag_query("What does the manual say about X?")'),
        ("rag_list_sources",  'rag_list_sources()'),
        ("rag_delete_source", 'rag_delete_source("manual.txt")'),
        ("rag_clear_all",     'rag_clear_all("yes")'),
    ]:
        t.add_row(name, usage)
    console.print(f"\n  {_c(C_PINK, f'Memory: {len(rag_engine.documents)} chunks · {len(rag_engine.list_sources())} sources')}")
    console.print(t)

def _show_god_tools():
    """Show God-Level tools."""
    t = Table(title="◈  GOD-LEVEL  ·  16 TOOLS  ◈", box=box.DOUBLE_EDGE,
              title_style=C_GOLD, header_style=C_GREEN, border_style="yellow", show_lines=True)
    t.add_column("TOOL",  style=C_GOLD,  min_width=24)
    t.add_column("USAGE", style=C_WHITE, min_width=52)
    for name, usage in [
        ("auto_coder",          'auto_coder("REST API with Flask", "python")'),
        ("system_optimizer",    'system_optimizer("report")'),
        ("smart_summarizer",    'smart_summarizer("https://example.com")'),
        ("multi_search",        'multi_search("AI 2025", "web,news,github")'),
        ("conversation_export", 'conversation_export("json")'),
        ("screen_reader",       'screen_reader("read")'),
        ("schedule_task",       'schedule_task("notepad.exe", 120, "Open Notes")'),
        ("language_translator", 'language_translator("Hello", "Hindi")'),
        ("code_debugger",       'code_debugger("my_script.py")'),
        ("ip_geolocation",      'ip_geolocation("8.8.8.8")'),
        ("system_benchmark",    'system_benchmark("cpu")'),
        ("regex_tool",          r'regex_tool(r"\d+", "order 42", "find")'),
        ("file_search",         'file_search("TODO", ".", "py,txt")'),
        ("text_to_speech_file", 'text_to_speech_file("Hello!", "out.wav")'),
        ("process_manager",     'process_manager("top")'),
        ("knowledge_snapshot",  'knowledge_snapshot("Mistral AI 2025")'),
    ]:
        t.add_row(name, usage)
    console.print(t)

def _show_help():
    """Show the full help menu."""
    console.print(f"""
{_c(C_GREEN, '  ◈  DEKU v6  ·  MISTRAL AI  ·  COMMAND REFERENCE')}
{_c(C_DIM,   '  ' + '─' * 50)}

  {_c(C_GOLD, 'status')}    →  Live system diagnostics table
  {_c(C_GOLD, 'tools')}     →  All {len(deku_tools)} tools with descriptions
  {_c(C_GOLD, 'new')}       →  22 new tools added in v6
  {_c(C_GOLD, 'hack')}      →  Hacker/security tools
  {_c(C_GOLD, 'rag')}       →  Memory system tools
  {_c(C_GOLD, 'god')}       →  God-level tools
  {_c(C_GOLD, 'history')}   →  Show conversation history
  {_c(C_GOLD, 'todos')}     →  Show your TODO list
  {_c(C_GOLD, 'clear')}     →  Clear the screen
  {_c(C_GOLD, 'exit')}      →  Shut down DEKU

{_c(C_DIM,   '  ' + '─' * 50)}
  {_c(C_GREEN, '[S]')}  →  Press S then Enter for mic input (5s)
  {_c(C_GREEN, '[V]')}  →  Press V then Enter to toggle voice output
  {_c(C_GREEN, '--voice')} →  Run with wake-word: python deku_agent.py --voice
{_c(C_DIM,   '  ' + '─' * 50)}

  ENGINE:   {_c(C_GREEN, f'Mistral AI · {MISTRAL_MODEL}')}
  TOOLS:    {_c(C_GREEN, str(len(deku_tools)))} total
  RAG:      {_c(C_PINK, str(len(rag_engine.documents)))} chunks  ·  Dense: {_c(C_GREEN if RAG_DENSE else C_RED, 'ON' if RAG_DENSE else 'OFF')}  ·  Sparse: {_c(C_GREEN if RAG_SPARSE else C_RED, 'ON' if RAG_SPARSE else 'OFF')}
  API KEY:  {_c(C_GREEN, 'SET ✔') if mistral_client else _c(C_RED, 'MISSING ✖  →  https://console.mistral.ai')}




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="DEKU v6 — Mistral AI · 75 Tools · Your God-Level AI Friend"
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Run in hands-free wake-word voice mode"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MISTRAL_MODEL,
        help=f"Mistral model to use (default: {MISTRAL_MODEL})"
    )
    args = parser.parse_args()

    # Override model from command line if provided
    MISTRAL_MODEL = args.model

    try:
        if args.voice:
            autonomous_engine()
        else:
            text_input_engine()
    except Exception as e:
        console.print(_c(C_RED, f"BOOT FAILURE: {e}"))
        import traceback
        traceback.print_exc()
