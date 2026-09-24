"""Quick database diagnostics for MPLADS pipeline."""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "mplads.db"

def main():
    if not DB.exists():
        print(f"DB not found: {DB}")
        sys.exit(1)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("TABLES:", tables)
    for t in tables:
        try:
            cnt = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            print(f"  {t}: {cnt}")
        except Exception as e:
            print(f"  {t}: ERROR {e}")

    # Project-specific diagnostics
    for qname, sql in [
        ("projects total", "SELECT COUNT(*) FROM projects"),
        ("projects unique project_id", "SELECT COUNT(DISTINCT project_id) FROM projects"),
        ("projects duplicate project_ids", """
            SELECT COUNT(*) FROM (
                SELECT project_id FROM projects GROUP BY project_id HAVING COUNT(*) > 1
            )
        """),
        ("analysis_results total", "SELECT COUNT(*) FROM analysis_results"),
        ("analysis unique project_id", "SELECT COUNT(DISTINCT project_id) FROM analysis_results"),
        ("risk distribution", """
            SELECT risk_level, COUNT(*) FROM analysis_results GROUP BY risk_level ORDER BY COUNT(*) DESC
        """),
        ("alerts total", "SELECT COUNT(*) FROM alerts"),
        ("alerts by severity", "SELECT severity, COUNT(*) FROM alerts GROUP BY severity"),
        ("analysis_runs", "SELECT id, status, project_count, created_at FROM analysis_runs ORDER BY id DESC LIMIT 5"),
    ]:
        try:
            if "distribution" in qname or "severity" in qname:
                rows = c.execute(sql.strip()).fetchall()
                print(f"\n{qname}:")
                for r in rows:
                    print(f"  {r}")
            elif qname == "analysis_runs":
                rows = c.execute(sql.strip()).fetchall()
                print(f"\n{qname}:")
                for r in rows:
                    print(f"  {r}")
            else:
                print(f"\n{qname}: {c.execute(sql.strip()).fetchone()[0]}")
        except Exception as e:
            print(f"\n{qname}: SKIP ({e})")

    conn.close()

if __name__ == "__main__":
    main()
