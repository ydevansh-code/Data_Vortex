#!/usr/bin/env python3
"""
audit_phase2.py  —  Data Vortex Phase 2 submission auditor

Drop this file in the ROOT of your Data_Vortex repo (next to .gitignore)
and run:   python audit_phase2.py

It verifies — against the actual files and the actual database — every claim
made about the Phase 2 deliverable. Standard library only. Nothing to install.
Read-only: it never modifies your repo or your database.

Exit code 0 = no blockers. Exit code 1 = at least one BLOCKER found.
"""

import os
import re
import sys
import csv
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P2 = ROOT / "phase2"
DB = P2 / "social_engine.db"

results = []   # (level, section, message)
BLOCK, WARN, OK, INFO = "BLOCKER", "WARN", "OK", "INFO"


def add(level, section, msg):
    results.append((level, section, msg))


def hr(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def run(cmd):
    """Run a shell command, return (ok, stdout)."""
    try:
        out = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
        return out.returncode == 0, (out.stdout or "") + (out.stderr or "")
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------- SECTION 1
def section_files():
    hr("SECTION 1 — FILE INVENTORY")

    required = {
        "phase2/schema.sql": BLOCK,
        "phase2/load_data.py": BLOCK,
        "phase2/social_engine.db": BLOCK,
        "phase2/Phase2_Submission.md": BLOCK,
        "phase2/README.md": WARN,
        "phase2/decisions.md": WARN,
        "phase2/queries/e3.sql": BLOCK,
        "phase2/queries/m1.sql": BLOCK,
        "phase2/queries/h3.sql": BLOCK,
        "phase2/queries/validation.sql": WARN,
        "phase2/queries/bonus_trend.sql": WARN,
    }
    for rel, level in required.items():
        p = ROOT / rel
        if p.exists():
            size = p.stat().st_size
            if size == 0:
                add(BLOCK, "1-FILES", f"{rel} exists but is EMPTY (0 bytes)")
                print(f"  [EMPTY!]  {rel}")
            else:
                print(f"  [ok]      {rel}  ({size:,} bytes)")
        else:
            add(level, "1-FILES", f"MISSING: {rel}")
            print(f"  [MISSING] {rel}")

    # anomaly query may be named several ways
    anom = list((P2 / "queries").glob("*anom*")) + list((P2 / "queries").glob("*h5*"))
    if anom:
        print(f"  [ok]      anomaly query: {anom[0].name}")
    else:
        add(WARN, "1-FILES", "No anomaly/h5 query file found in phase2/queries/")
        print("  [MISSING] anomaly / h5 query")

    # SCREENSHOTS — the claim most likely to be false
    shots_dir = P2 / "screenshots"
    imgs = []
    if shots_dir.exists():
        imgs = [f for f in shots_dir.iterdir()
                if f.suffix.lower() in (".jpg", ".jpeg", ".png")]
    print(f"\n  screenshots/ contains {len(imgs)} image file(s)")
    for f in imgs:
        kb = f.stat().st_size / 1024
        flag = "  <-- suspiciously small" if kb < 30 else ""
        print(f"      {f.name}  ({kb:,.0f} KB){flag}")
        if kb < 30:
            add(WARN, "1-FILES", f"{f.name} is only {kb:.0f} KB - may be unreadable")
    if len(imgs) < 3:
        add(BLOCK, "1-FILES",
            f"Only {len(imgs)} screenshot(s) found. Rulebook requires Output "
            f"Screenshots for every question. Need at least 3.")

    jpegs = [f for f in imgs if f.suffix.lower() in (".jpg", ".jpeg")]
    if imgs and not jpegs:
        add(WARN, "1-FILES",
            "Screenshots are PNG. Your plan specified JPEG. Either is probably "
            "fine, but be consistent.")

    # outputs
    outs = list((P2 / "outputs").glob("*.csv")) if (P2 / "outputs").exists() else []
    print(f"\n  outputs/ contains {len(outs)} CSV file(s)")
    for f in outs:
        try:
            n = sum(1 for _ in open(f, encoding="utf-8", errors="replace")) - 1
            print(f"      {f.name}  ({n} data rows)")
            if n <= 0:
                add(WARN, "1-FILES", f"{f.name} has no data rows")
        except Exception as e:
            print(f"      {f.name}  (unreadable: {e})")

    # the PDF
    pdfs = list(P2.glob("*.pdf"))
    if pdfs:
        for f in pdfs:
            print(f"\n  [ok]      PDF present: {f.name} ({f.stat().st_size/1024:,.0f} KB)")
    else:
        add(BLOCK, "1-FILES",
            "NO PDF in phase2/. Rulebook: 'Submission Format: A PDF document.' "
            "You must export Phase2_Submission.md to PDF before submitting.")
        print("\n  [MISSING] phase2/*.pdf  <-- REQUIRED BY RULEBOOK")


# ---------------------------------------------------------------- SECTION 2
def section_git():
    hr("SECTION 2 — GIT STATE (verifies the 'all committed' claim)")

    ok, _ = run("git rev-parse --is-inside-work-tree")
    if not ok:
        add(WARN, "2-GIT", "Not a git repo, or git not available. Skipping.")
        print("  Not a git repository (or git missing). Skipped.")
        return

    ok, status = run("git status --porcelain")
    dirty = [l for l in status.splitlines() if l.strip()]
    if dirty:
        add(BLOCK, "2-GIT",
            f"{len(dirty)} uncommitted/untracked change(s). The 'everything is "
            f"pushed' claim is FALSE until these are committed.")
        print(f"  UNCOMMITTED / UNTRACKED ({len(dirty)}):")
        for l in dirty[:25]:
            print("      " + l)
        if len(dirty) > 25:
            print(f"      ... and {len(dirty)-25} more")
    else:
        print("  [ok] Working tree clean — everything is committed.")

    ok, cnt = run("git rev-list --count HEAD")
    if ok and cnt.strip().isdigit():
        n = int(cnt.strip())
        print(f"\n  Total commits: {n}")
        if n < 5:
            add(WARN, "2-GIT",
                f"Only {n} commits. Judges may read this as a last-minute dump.")

    ok, log = run('git log --oneline -15 --date=short --pretty=format:"%h %ad %s"')
    if ok:
        print("\n  Recent commits:")
        for l in log.splitlines()[:15]:
            print("      " + l.strip('"'))

    # is the .db actually tracked, or silently ignored?
    ok, tracked = run("git ls-files phase2/social_engine.db")
    if tracked.strip():
        print("\n  [ok] social_engine.db IS tracked by git.")
    else:
        add(WARN, "2-GIT",
            "social_engine.db is NOT tracked by git (likely caught by .gitignore). "
            "The committee reserves the right to verify outputs — they can't "
            "re-run your queries without it.")
        print("\n  [!!] social_engine.db is NOT tracked by git.")

    ok, ahead = run("git status -sb")
    if "ahead" in ahead:
        add(BLOCK, "2-GIT", "Local commits exist that have NOT been pushed to remote.")
        print("\n  [!!] You have unpushed commits. Run: git push")


# ---------------------------------------------------------------- SECTION 3
def section_schema():
    hr("SECTION 3 — SCHEMA AUDIT (reads the live database)")

    if not DB.exists():
        add(BLOCK, "3-SCHEMA", "social_engine.db not found — cannot audit schema.")
        print("  Database missing. Skipping.")
        return None

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    objs = cur.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    tables = [o["name"] for o in objs if o["type"] == "table"]
    views = [o["name"] for o in objs if o["type"] == "view"]
    indexes = [o["name"] for o in objs if o["type"] == "index"]

    print(f"  Tables : {tables}")
    print(f"  Views  : {views}")
    print(f"  Indexes: {indexes}")

    for t in ("users", "posts"):
        if t not in tables:
            add(BLOCK, "3-SCHEMA", f"Table '{t}' does not exist in the database.")

    if not views:
        add(WARN, "3-SCHEMA",
            "No VIEW found. The rulebook explicitly permits Views and you claimed "
            "v_post_engagement exists.")
    if not indexes:
        add(WARN, "3-SCHEMA", "No indexes found, despite the claim that platform "
                              "and user_id were indexed.")

    # ---- column inventory: verifies the imputation-flag claim
    print("\n  COLUMN INVENTORY")
    for t in tables:
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        names = [c["name"] for c in cols]
        print(f"\n    {t}  ({len(names)} columns)")
        for c in cols:
            bits = []
            if c["pk"]:
                bits.append("PK")
            if c["notnull"]:
                bits.append("NOT NULL")
            print(f"      - {c['name']:<28} {c['type']:<8} {' '.join(bits)}")
        flags = [n for n in names if n.endswith("_was_null")]
        print(f"      imputation flags present: {flags if flags else 'NONE'}")
        if t == "users" and not flags:
            add(WARN, "3-SCHEMA",
                "users table has NO *_was_null flags, contradicting claim 2.1")
        if t == "posts" and "platform_was_null" not in names:
            add(WARN, "3-SCHEMA",
                "posts table has no platform_was_null, contradicting claim 2.2")
        if t == "users":
            if "city" in names and "country" in names:
                print("      location normalization: city + country present [ok]")
            else:
                add(WARN, "3-SCHEMA",
                    "users has no city/country columns — claim 2.5 (location "
                    "normalization) is not supported by the database.")

    # ---- constraints: verifies claim 2.3
    print("\n  CONSTRAINT CHECK (from CREATE statements)")
    for o in objs:
        if o["type"] == "table" and o["sql"]:
            s = o["sql"].upper()
            print(f"    {o['name']}: "
                  f"PK={'PRIMARY KEY' in s}  "
                  f"NOTNULL={'NOT NULL' in s}  "
                  f"CHECK={'CHECK' in s}  "
                  f"FK={'REFERENCES' in s}")
            if "CHECK" not in s:
                add(WARN, "3-SCHEMA",
                    f"{o['name']} has no CHECK constraint, contradicting claim 2.3")
            if o["name"] == "posts" and "REFERENCES" not in s:
                add(WARN, "3-SCHEMA",
                    "posts has no FOREIGN KEY reference to users.")

    # ---- THE COALESCE / FABRICATION CHECK
    print("\n  VIEW DEFINITIONS (check for silent imputation)")
    for o in objs:
        if o["type"] == "view" and o["sql"]:
            print("    " + "-" * 60)
            for line in o["sql"].splitlines():
                print("    " + line)
            if "COALESCE" in o["sql"].upper():
                add(WARN, "3-SCHEMA",
                    f"View '{o['name']}' uses COALESCE. If it converts NULL likes "
                    f"to 0, unknown values silently become real zeros and enter "
                    f"your averages. Rulebook: 'Fabrication of data is prohibited.' "
                    f"Either justify this explicitly in the report, or filter NULLs "
                    f"instead of defaulting them.")
                print("\n    [!!] COALESCE detected — see WARN below.")

    fk = cur.execute("PRAGMA foreign_keys").fetchone()
    print(f"\n  PRAGMA foreign_keys (this session) = {fk[0]}")
    print("  NOTE: PRAGMA foreign_keys is per-connection in SQLite. Putting it in")
    print("        schema.sql does NOT persist it. Be ready to say that out loud.")

    return con


# ---------------------------------------------------------------- SECTION 4
def section_data(con):
    hr("SECTION 4 — DATA INTEGRITY (verifies the 1.x claims)")
    if con is None:
        return
    cur = con.cursor()

    def scalar(q, default=None):
        try:
            r = cur.execute(q).fetchone()
            return r[0] if r else default
        except Exception as e:
            return f"ERROR: {e}"

    claims = {}

    users_n = scalar("SELECT COUNT(*) FROM users")
    posts_n = scalar("SELECT COUNT(*) FROM posts")
    print(f"  users rows : {users_n}   (plan said 1,501)")
    print(f"  posts rows : {posts_n}   (plan said 12,000)")
    if isinstance(users_n, int) and users_n != 1501:
        add(WARN, "4-DATA", f"users has {users_n} rows, plan said 1,501. "
                            f"Explain the difference or fix the load.")
    if isinstance(posts_n, int) and posts_n != 12000:
        add(WARN, "4-DATA", f"posts has {posts_n} rows, plan said 12,000. "
                            f"Explain the difference or fix the load.")

    null_plat = scalar("SELECT COUNT(*) FROM posts WHERE platform IS NULL")
    neg_likes = scalar("SELECT COUNT(*) FROM posts WHERE likes < 0")
    null_likes = scalar("SELECT COUNT(*) FROM posts WHERE likes IS NULL")
    print(f"\n  NULL platform : {null_plat}   (claimed 1,784)")
    print(f"  negative likes: {neg_likes}   (claimed 509)")
    print(f"  NULL likes    : {null_likes}   <-- NOT the same as negative!")
    claims["null_platform"] = null_plat
    claims["negative_likes"] = neg_likes

    if null_plat != 1784:
        add(BLOCK, "4-DATA",
            f"Claimed 1,784 NULL platforms; database has {null_plat}. Your report "
            f"quotes a number that does not match your data.")
    if neg_likes != 509:
        add(BLOCK, "4-DATA",
            f"Claimed 509 negative likes; database has {neg_likes}. Fix the number "
            f"in the report.")
    if isinstance(null_likes, int) and null_likes > 0:
        add(WARN, "4-DATA",
            f"{null_likes} rows have NULL likes. 'WHERE likes >= 0' silently drops "
            f"these too — state that exclusion count in the Logic Explanation.")

    orphans = scalar("""SELECT COUNT(*) FROM posts p
                        LEFT JOIN users u ON p.user_id = u.user_id
                        WHERE u.user_id IS NULL""")
    print(f"\n  orphan posts  : {orphans}   (claimed 0)")
    if orphans != 0:
        add(BLOCK, "4-DATA",
            f"{orphans} orphan posts exist. M1's INNER JOIN silently drops them. "
            f"The claim of zero orphans is FALSE.")

    dup_u = scalar("""SELECT COUNT(*) FROM (SELECT user_id FROM users
                      GROUP BY user_id HAVING COUNT(*)>1)""")
    dup_p = scalar("""SELECT COUNT(*) FROM (SELECT post_id FROM posts
                      GROUP BY post_id HAVING COUNT(*)>1)""")
    print(f"  dup user_id   : {dup_u}")
    print(f"  dup post_id   : {dup_p}")

    bad_dates = scalar("""SELECT COUNT(*) FROM posts
                          WHERE timestamp IS NOT NULL
                            AND strftime('%Y-%m', timestamp) IS NULL""")
    print(f"  unparseable timestamps: {bad_dates}   (claimed 0)")
    if isinstance(bad_dates, int) and bad_dates > 0:
        add(WARN, "4-DATA", f"{bad_dates} timestamps do not parse. Trend query "
                            f"silently drops them.")

    # ---- THE H3 VIABILITY PROOF (the headline risk)
    print("\n  H3 VIABILITY — max vs 2x mean, per platform")
    print("  " + "-" * 68)
    print(f"  {'platform':<14}{'n':>7}{'avg_eng':>12}{'2x_avg':>12}{'max_eng':>12}{'qualify':>9}")
    print("  " + "-" * 68)
    try:
        rows = cur.execute("""
            SELECT platform,
                   COUNT(*) n,
                   ROUND(AVG(likes+shares+comments),1) avg_eng,
                   ROUND(2*AVG(likes+shares+comments),1) thr,
                   MAX(likes+shares+comments) max_eng
            FROM posts
            WHERE platform IS NOT NULL AND likes >= 0
            GROUP BY platform ORDER BY avg_eng DESC""").fetchall()
        total_q = 0
        for r in rows:
            q = cur.execute("""
                SELECT COUNT(*) FROM posts
                WHERE platform = ? AND likes >= 0
                  AND (likes+shares+comments) >= ?""",
                            (r["platform"], r["thr"])).fetchone()[0]
            total_q += q
            print(f"  {r['platform']:<14}{r['n']:>7}{r['avg_eng']:>12}"
                  f"{r['thr']:>12}{r['max_eng']:>12}{q:>9}")
        print("  " + "-" * 68)
        print(f"  TOTAL rows H3 (literal 2x) returns: {total_q}")
        claims["h3_rows"] = total_q
        if total_q == 0:
            add(WARN, "4-DATA",
                "H3 literal query returns 0 rows — CONFIRMED. This is defensible "
                "ONLY if the report (a) shows this exact table as proof, (b) "
                "explains max/mean ~= 2 under a near-uniform distribution, and "
                "(c) presents a working alternative. A blank result grid with no "
                "explanation reads as a failed query.")
    except Exception as e:
        add(WARN, "4-DATA", f"H3 diagnostic failed: {e}")
        print(f"  ERROR: {e}")

    # ---- correlation gap
    print("\n  RULEBOOK COVERAGE — 4 named challenge types")
    qdir = P2 / "queries"
    allsql = ""
    if qdir.exists():
        for f in qdir.glob("*.sql"):
            allsql += f.read_text(encoding="utf-8", errors="replace").lower() + "\n"
    cover = {
        "trend detection":    "strftime" in allsql or "lag(" in allsql,
        "anomaly discovery":  "anomal" in allsql or "likes < 0" in allsql,
        "behavioural grouping": "group by" in allsql,
        "correlation analysis": ("corr" in allsql or "follower_count" in allsql),
    }
    for k, v in cover.items():
        print(f"    {k:<24} {'[covered]' if v else '[NOT COVERED]'}")
        if not v:
            add(WARN, "4-DATA",
                f"'{k}' is named in the rulebook but no query appears to address it.")

    return claims


# ---------------------------------------------------------------- SECTION 5
def section_queries(con):
    hr("SECTION 5 — EXECUTE EVERY QUERY (proves they actually run)")
    if con is None:
        return
    qdir = P2 / "queries"
    if not qdir.exists():
        add(BLOCK, "5-QUERIES", "phase2/queries/ does not exist.")
        return

    cur = con.cursor()
    for f in sorted(qdir.glob("*.sql")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        # strip comments
        body = re.sub(r"--[^\n]*", "", raw)
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        
        stmts = []
        current = []
        in_quote = False
        for char in body:
            if char == "'":
                in_quote = not in_quote
            if char == ';' and not in_quote:
                stmts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        if ''.join(current).strip():
            stmts.append(''.join(current).strip())
            
        stmts = [s for s in stmts if s]
        print(f"\n  {f.name}  ({len(stmts)} statement(s))")
        if not stmts:
            add(BLOCK, "5-QUERIES", f"{f.name} contains no executable SQL.")
            print("    [!!] EMPTY")
            continue
        for i, s in enumerate(stmts, 1):
            if not s.upper().lstrip().startswith(("SELECT", "WITH")):
                print(f"    [{i}] skipped (not a SELECT)")
                continue
            try:
                rows = cur.execute(s).fetchall()
                cols = [d[0] for d in cur.description]
                print(f"    [{i}] OK — {len(rows)} row(s), {len(cols)} col(s)")
                print(f"        columns: {', '.join(cols)}")
                for r in rows[:3]:
                    vals = [str(r[c])[:18] for c in cols]
                    print(f"        | " + " | ".join(vals))
                if len(rows) == 0:
                    add(WARN, "5-QUERIES",
                        f"{f.name} statement {i} returns ZERO rows — you cannot "
                        f"screenshot a meaningful result.")
            except Exception as e:
                add(BLOCK, "5-QUERIES", f"{f.name} statement {i} FAILED: {e}")
                print(f"    [{i}] *** SQL ERROR: {e}")


# ---------------------------------------------------------------- SECTION 6
def section_hardcoding():
    hr("SECTION 6 — HARDCODING SCAN (rulebook: hardcoding => disqualification)")
    qdir = P2 / "queries"
    if not qdir.exists():
        return

    # literal platform names / user ids / post ids in a WHERE or IN clause
    patterns = [
        (r"=\s*'(facebook|youtube|twitter|reddit|instagram)'", "literal platform name in ="),
        (r"IN\s*\(\s*'(facebook|youtube|twitter|reddit|instagram)'", "literal platform list"),
        (r"=\s*'user_[a-z0-9]+'", "literal user_id"),
        (r"=\s*'post_[a-z0-9]+'", "literal post_id"),
        (r"UNION\s+ALL\s+SELECT\s+'", "UNION ALL SELECT of literal strings (fake result set!)"),
        (r"VALUES\s*\(\s*'", "VALUES clause with literals inside a query file"),
    ]
    found_any = False
    for f in sorted(qdir.glob("*.sql")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        low = txt.lower()
        for pat, label in patterns:
            for m in re.finditer(pat, low, flags=re.I):
                if f.name == 'validation.sql' and 'UNION' in pat:
                    continue
                line = low[:m.start()].count("\n") + 1
                found_any = True
                lvl = BLOCK if "fake result" in label or "VALUES" in label else WARN
                add(lvl, "6-HARDCODE", f"{f.name}:{line} — {label}")
                print(f"  [{lvl}] {f.name}:{line}  {label}")
                print(f"          ...{txt.splitlines()[line-1].strip()[:80]}")
    if not found_any:
        print("  [ok] No hardcoded literals detected in any query file.")

    # comment headers
    print("\n  COMMENT HEADERS (rulebook: 'Query logic should be clearly documented')")
    for f in sorted(qdir.glob("*.sql")):
        head = f.read_text(encoding="utf-8", errors="replace").lstrip()
        has = head.startswith("--") or head.startswith("/*")
        print(f"    {f.name:<24} {'[documented]' if has else '[NO HEADER COMMENT]'}")
        if not has:
            add(WARN, "6-HARDCODE", f"{f.name} has no explanatory header comment.")


# ---------------------------------------------------------------- SECTION 7
def section_report():
    hr("SECTION 7 — SUBMISSION DOCUMENT AUDIT")
    doc = P2 / "Phase2_Submission.md"
    if not doc.exists():
        add(BLOCK, "7-REPORT", "Phase2_Submission.md not found.")
        print("  Missing. Skipping.")
        return
    txt = doc.read_text(encoding="utf-8", errors="replace")
    low = txt.lower()
    words = len(txt.split())
    print(f"  Length: {words:,} words, {len(txt.splitlines()):,} lines")
    if words < 1200:
        add(WARN, "7-REPORT", f"Only {words} words. Thin for a document that must "
                              f"carry schema design, 3 logic explanations, bonus "
                              f"queries and an insight report.")

    # embedded images — the real screenshot test
    md_imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", txt)
    html_imgs = re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", txt, flags=re.I)
    embeds = md_imgs + html_imgs
    print(f"\n  Embedded images: {len(embeds)}")
    broken = 0
    for src in embeds:
        if src.startswith(("http://", "https://", "data:")):
            print(f"    [remote] {src[:60]}")
            continue
        target = (doc.parent / src).resolve()
        if target.exists():
            print(f"    [ok]     {src}")
        else:
            broken += 1
            print(f"    [BROKEN] {src}  <-- file does not exist")
    if broken:
        add(BLOCK, "7-REPORT", f"{broken} image link(s) point to files that do not "
                               f"exist. They will render as blank boxes in the PDF.")
    if len(embeds) < 3:
        add(BLOCK, "7-REPORT",
            f"Only {len(embeds)} image(s) embedded. The rulebook requires Output "
            f"Screenshots. Placeholder text is not a screenshot.")

    # placeholder detection
    for ph in ["<!-- paste", "paste screenshot", "todo", "tbd", "xxx",
               "insert screenshot", "action required", "your screenshot"]:
        if ph in low:
            add(BLOCK, "7-REPORT",
                f"Placeholder text found in the submission doc: '{ph}'. Search the "
                f"file and replace it before exporting.")
            print(f"\n  [!!] PLACEHOLDER FOUND: '{ph}'")

    # required sections
    print("\n  REQUIRED SECTIONS")
    need = {
        "schema": ["schema"],
        "logic explanation": ["logic", "explanation"],
        "insight report": ["insight"],
        "assumptions / limitations": ["assumption", "limitation"],
        "data validation": ["validation", "row count"],
        "exclusion counts (1784 / 509)": ["1,784", "1784", "509"],
    }
    for label, keys in need.items():
        hit = any(k in low for k in keys)
        print(f"    {label:<32} {'[present]' if hit else '[MISSING]'}")
        if not hit:
            add(WARN, "7-REPORT", f"No '{label}' section detected in the report.")


# ---------------------------------------------------------------- MAIN
def main():
    print("DATA VORTEX — PHASE 2 SUBMISSION AUDIT")
    print(f"Repo root: {ROOT}")

    section_files()
    section_git()
    con = section_schema()
    section_data(con)
    section_queries(con)
    section_hardcoding()
    section_report()
    if con:
        con.close()

    hr("FINAL VERDICT")
    blockers = [r for r in results if r[0] == BLOCK]
    warns = [r for r in results if r[0] == WARN]

    if blockers:
        print(f"\n  {len(blockers)} BLOCKER(S) — DO NOT SUBMIT UNTIL FIXED\n")
        for i, (_, sec, msg) in enumerate(blockers, 1):
            print(f"  {i:>2}. [{sec}] {msg}\n")
    else:
        print("\n  No blockers found.\n")

    if warns:
        print(f"  {len(warns)} WARNING(S) — fix if time allows\n")
        for i, (_, sec, msg) in enumerate(warns, 1):
            print(f"  {i:>2}. [{sec}] {msg}\n")

    # write a copy
    out = ROOT / "phase2_audit_report.txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("DATA VORTEX PHASE 2 — AUDIT REPORT\n\n")
        fh.write(f"BLOCKERS: {len(blockers)}   WARNINGS: {len(warns)}\n\n")
        for lvl, sec, msg in results:
            fh.write(f"[{lvl}] [{sec}] {msg}\n")
    print(f"\n  Written to: {out}")
    print("  (Do NOT commit this file — it is your scratchpad, not a deliverable.)")

    sys.exit(1 if blockers else 0)


if __name__ == "__main__":
    main() 
