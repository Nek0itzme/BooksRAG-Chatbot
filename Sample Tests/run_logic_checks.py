"""Logic & race condition checks for the full codebase."""
import os, sys, warnings, inspect
os.environ.setdefault("GEMINI_API_KEY", "mock_key_for_testing_12345")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "Back End"))
sys.path.insert(0, str(_ROOT / "Web Database"))
sys.path.insert(0, str(_ROOT / "RAG Rules"))

PASS, WARN, FAIL = "[PASS]", "[WARN]", "[FAIL]"

def check(label, cond, msg="", severity=FAIL):
    if cond:
        print(f"  {PASS} {label}")
    else:
        print(f"  {severity} {label}: {msg}")

# ── 1. config ────────────────────────────────────────────────────────────────
print("\n[1] config.py")
import config
check("Weights sum to 1.0",
      abs(config.W_RATING + config.W_SALES + config.W_QUALITY - 1.0) < 1e-9,
      f"sum={config.W_RATING+config.W_SALES+config.W_QUALITY}")
check("ALPHA in (0,1)", 0 < config.ALPHA < 1)
check("MIN_RATING >= 0", config.MIN_RATING >= 0)
check("DEFAULT_BUDGET > 0", config.DEFAULT_BUDGET > 0)
check("TOP_K <= CHROMA_N_RESULTS", config.TOP_K <= config.CHROMA_N_RESULTS,
      "TOP_K > CHROMA_N_RESULTS means ChromaDB can never return enough candidates")
print(f"  GEMINI_FLASH    = {config.GEMINI_FLASH!r}")
print(f"  GEMINI_FALLBACK = {config.GEMINI_FALLBACK!r}")
check("GEMINI_FALLBACK not placeholder",
      "3.5" not in config.GEMINI_FALLBACK,
      "gemini-3.5-flash-lite does not exist; correct name is gemini-2.5-flash-lite or similar",
      severity=WARN)

# ── 2. doc_pipeline path traversal ──────────────────────────────────────────
print("\n[2] doc_pipeline.py — security")
from doc_pipeline import _safe_sid, get_markdown_content, get_pdf_path
evil = "../../../etc/passwd"
safe = _safe_sid(evil)
check("safe_sid strips ../", "/" not in safe and ".." not in safe,
      f"got {safe!r}")
check("get_markdown_content blocks traversal",
      get_markdown_content("../../evil", "file.md") is None)
check("get_pdf_path blocks traversal",
      get_pdf_path("../../evil", "file.pdf") is None)

# ── 3. doc_rag session isolation ─────────────────────────────────────────────
print("\n[3] doc_rag.py — session isolation")
from doc_rag import _safe_sid as doc_sid
check("Different sessions -> different collection names",
      doc_sid("sess-A") != doc_sid("sess-B"))
check("Same session -> same collection name",
      doc_sid("sess-A") == doc_sid("sess-A"))

# ── 4. med_gatekeeper ────────────────────────────────────────────────────────
print("\n[4] med_gatekeeper.py")
from med_gatekeeper import check_drug_safety
check("Rx drug blocked", not check_drug_safety("Amoxicillin 500mg", [])["allowed"])
check("OTC + safe conditions -> allowed",
      check_drug_safety("Vitamin C 500mg", ["mệt mỏi"])["allowed"])
check("Unknown drug -> not allowed",
      not check_drug_safety("FakeDrugXYZ9999", [])["allowed"])
check("OTC + matching contraindication -> blocked",
      not check_drug_safety("Hapacol 650", ["suy gan nặng"])["allowed"])

# ── 5. rag_engine hard_filter ────────────────────────────────────────────────
print("\n[5] rag_engine.py — hard_filter")
import rag_engine
books = [
    {"id":"B1","in_stock":True,  "rating":4.5,"price":50_000},
    {"id":"B2","in_stock":False, "rating":4.5,"price":50_000},
    {"id":"B3","in_stock":True,  "rating":1.5,"price":50_000},
    {"id":"B4","in_stock":True,  "rating":4.5,"price":500_000},
]
check("budget=0 returns empty",
      rag_engine.hard_filter(books, budget=0, min_rating=2.0) == [])
check("out-of-stock filtered",
      all(b["in_stock"] for b in rag_engine.hard_filter(books, 999_999, 2.0)))
check("below min_rating filtered",
      all(float(b["rating"]) >= 2.0 for b in rag_engine.hard_filter(books, 999_999, 2.0)))
check("over budget filtered",
      all(b["price"] <= 100_000 for b in rag_engine.hard_filter(books, 100_000, 2.0)))

# ── 6. scoring ───────────────────────────────────────────────────────────────
print("\n[6] rag_engine.py — scoring")
b5 = {"rating":5.0,"sold_count":1000,"total_reviews":100,"valid_reviews":90}
b1 = {"rating":1.0,"sold_count":0,   "total_reviews":0,  "valid_reviews":0}
check("score_rating(5.0) == 1.0", abs(rag_engine.score_rating(b5)-1.0) < 0.01)
check("score_rating(1.0) == 0.0", abs(rag_engine.score_rating(b1)) < 0.01)
check("score_sales(0) == 0.0",    rag_engine.score_sales(b1) == 0.0)
hs = rag_engine.hybrid_score(0.9, b5)
check("hybrid_score in [0,1]", 0.0 <= hs <= 1.0, f"got {hs}")

# ── 7. main.py race condition ─────────────────────────────────────────────────
print("\n[7] main.py — potential race condition")
import main
import asyncio
lock_type = type(main._sessions_lock).__name__
print(f"  _sessions_lock type: {lock_type}")
cleanup_src = inspect.getsource(main._cleanup_expired_sessions)
check("_cleanup_expired_sessions holds _sessions_lock",
      "_sessions_lock" in cleanup_src,
      "Background daemon thread modifies _sessions dict without lock -> race condition!",
      severity=WARN)

# ── 8. main.py _sessions_lock mismatch ───────────────────────────────────────
print("\n[8] main.py — asyncio.Lock in sync daemon thread")
# asyncio.Lock cannot be awaited from a non-async context.
# _cleanup_expired_sessions is a sync daemon thread but _sessions_lock is asyncio.Lock
# => cleanup thread cannot safely acquire it with await.
check("asyncio.Lock NOT misused in sync cleanup thread",
      "_sessions_lock" not in cleanup_src,
      "_cleanup_expired_sessions is a sync thread but _sessions_lock is asyncio.Lock -> cannot await in thread! Should use threading.Lock instead",
      severity=WARN)

# ── 9. query_context undefined variable risk ─────────────────────────────────
print("\n[9] rag_engine.py — query_context defined before use")
run_src = inspect.getsource(rag_engine.run_rag)
# query_context is set inside if/elif/else blocks under `if image_data:`
# but could theoretically be accessed before if a new branch was added
check("query_context defined in else branch",
      "query_context = " in run_src)

print("\n" + "="*60)
print("Codebase check complete.")
