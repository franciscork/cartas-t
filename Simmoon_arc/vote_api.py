#!/usr/bin/env python3
"""
SIMMOON Vote API — Simple HTTP server for vote persistence.
Replaces localStorage with PostgreSQL-backed votes for viewer.html.

Usage:
    python vote_api.py                    # Start on http://0.0.0.0:9099
    python vote_api.py --port 9100
    python vote_api.py --bind 127.0.0.1   # Localhost only
    python vote_api.py --bind 0.0.0.0     # All interfaces

Endpoints:
    GET    /api/votes             → List all votes
    GET    /api/votes/:asset_id   → Get vote for an asset
    POST   /api/votes             → Submit a vote { asset_id, vote_value, session_id } (rate-limited)
    PUT    /api/votes/:asset_id   → Update all votes for asset { vote_value } (admin)
    DELETE /api/votes/:asset_id   → Delete all votes for asset (admin)
    PATCH  /api/admin/reset-all   → Bulk reset all votes to value { vote_value } (admin)
    GET    /api/stats             → Vote statistics (total, avg, distribution)
    GET    /health                → Health check (PostgreSQL status, uptime)

Rate Limiting:
    POST /api/votes is rate-limited to N requests per minute per IP (default: 30).
    Returns 429 Too Many Requests with Retry-After header when exceeded.
    Configure with: --rate-limit 60
"""

import json
import os
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

START_TIME = time.time()


def load_api_key():
    """Load API key from env var or config.json. Returns None if not configured."""
    key = os.environ.get("SIMMOON_API_KEY")
    if key:
        return key
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(cfg_path) as f:
            cfg = json.load(f)
        return cfg.get("vote_api", {}).get("api_key")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


API_KEY = load_api_key()
if not API_KEY:
    print("  [WARN] No API key configured — set vote_api.api_key in config.json or SIMMOON_API_KEY env var")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
}


class RateLimiter:
    """Sliding-window rate limiter by IP address. POST-only, no external deps."""

    def __init__(self, max_requests=30, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits = defaultdict(list)  # ip → [timestamps]
        self._cleanup_counter = 0

    def is_allowed(self, ip):
        """Check if the IP is within the rate limit. Returns (allowed, remaining, reset_ts)."""
        now = time.time()
        cutoff = now - self.window
        # Prune old entries for this IP
        hits = self._hits[ip]
        self._hits[ip] = [t for t in hits if t > cutoff]
        hits = self._hits[ip]

        remaining = max(0, self.max_requests - len(hits))
        reset_ts = int(hits[0] + self.window) if hits else int(now + self.window)

        if len(hits) >= self.max_requests:
            return False, 0, reset_ts

        hits.append(now)
        remaining = max(0, self.max_requests - len(hits))
        return True, remaining, reset_ts

    def cleanup(self):
        """Periodically remove stale IPs to prevent memory growth."""
        self._cleanup_counter += 1
        if self._cleanup_counter % 100 != 0:
            return
        cutoff = time.time() - self.window
        stale = [ip for ip, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for ip in stale:
            del self._hits[ip]


rate_limiter = None  # Initialized in main() after argparse


def get_db():
    try:
        import psycopg
        config = {"host": "localhost", "port": 5432, "dbname": "simmoon", "user": "postgres"}
        return psycopg.connect(**config)
    except ImportError:
        import psycopg2
        config = {"host": "localhost", "port": 5432, "database": "simmoon", "user": "postgres"}
        return psycopg2.connect(**config)


class VoteHandler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/votes":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT asset_id, vote_value, session_id, updated_at FROM votes ORDER BY asset_id")
            rows = cur.fetchall()
            votes_list = [
                {"asset_id": r[0], "vote_value": r[1],
                 "session_id": r[2], "updated_at": r[3].isoformat()}
                for r in rows
            ]
            cur.close()
            conn.close()
            return self._send_json(votes_list)

        if path.startswith("/api/votes/"):
            asset_id = path.split("/api/votes/")[1]
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT asset_id, vote_value, session_id, updated_at FROM votes WHERE asset_id = %s",
                (asset_id,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return self._send_json({
                    "asset_id": row[0], "vote_value": row[1],
                    "session_id": row[2], "updated_at": row[3].isoformat()
                })
            return self._send_json({"asset_id": asset_id, "vote_value": 0}, 200)

        if path == "/api/stats":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*), AVG(vote_value), MIN(vote_value), MAX(vote_value)
                FROM votes
            """)
            total, avg, mn, mx = cur.fetchone()
            cur.execute("SELECT vote_value, COUNT(*) FROM votes GROUP BY vote_value ORDER BY vote_value")
            dist = {str(r[0]): r[1] for r in cur.fetchall()}
            cur.close()
            conn.close()
            return self._send_json({
                "total_votes": total or 0,
                "average": round(float(avg), 2) if avg else 0,
                "min": mn or 0,
                "max": mx or 0,
                "distribution": dist,
            })

        if path == "/health":
            status = "healthy"
            db_ok = False
            db_error = None
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.execute("SELECT count(*) FROM votes")
                vote_count = cur.fetchone()[0]
                cur.close()
                conn.close()
                db_ok = True
            except Exception as e:
                status = "degraded"
                db_error = str(e)

            uptime_sec = int(time.time() - START_TIME)
            hours, remainder = divmod(uptime_sec, 3600)
            minutes, seconds = divmod(remainder, 60)

            pg_check = {"status": "ok" if db_ok else "error"}
            if db_ok:
                pg_check["votes"] = vote_count
            else:
                pg_check["error"] = db_error

            health = {
                "status": status,
                "uptime": f"{hours}h {minutes}m {seconds}s",
                "uptime_seconds": uptime_sec,
                "started_at": datetime.fromtimestamp(START_TIME, tz=timezone.utc).isoformat(),
                "checks": {"postgresql": pg_check},
            }

            http_status = 200 if db_ok else 503
            return self._send_json(health, http_status)

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") != "/api/votes":
            return self._send_json({"error": "Not found"}, 404)

        # Rate limiting (before auth to prevent brute-force too)
        rate_headers = {}
        if rate_limiter:
            ip = self.client_address[0]
            allowed, remaining, reset_ts = rate_limiter.is_allowed(ip)
            rate_limiter.cleanup()
            rate_headers = {
                "X-RateLimit-Limit": str(rate_limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_ts),
            }
            if not allowed:
                retry_after = max(1, reset_ts - int(time.time()))
                rate_headers["Retry-After"] = str(retry_after)
                return self._send_json(
                    {"error": f"Rate limit exceeded — max {rate_limiter.max_requests} requests per {rate_limiter.window}s per IP",
                     "retry_after": retry_after},
                    429, rate_headers)

        # API key authentication
        if API_KEY:
            req_key = self.headers.get("X-API-Key", "")
            if req_key != API_KEY:
                return self._send_json({"error": "Unauthorized — invalid or missing X-API-Key header"}, 401, rate_headers)

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON"}, 400)

        asset_id = data.get("asset_id")
        vote_value = data.get("vote_value")
        session_id = data.get("session_id", f"anon_{uuid.uuid4().hex[:8]}")

        if not asset_id or not vote_value:
            return self._send_json({"error": "asset_id and vote_value required"}, 400, rate_headers)
        if not isinstance(vote_value, int) or vote_value < 1 or vote_value > 5:
            return self._send_json({"error": "vote_value must be 1-5"}, 400, rate_headers)

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO votes (asset_id, vote_value, session_id)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (asset_id, session_id)
                   DO UPDATE SET vote_value = EXCLUDED.vote_value, updated_at = NOW()
                   RETURNING id""",
                (asset_id, vote_value, session_id),
            )
            conn.commit()
            vote_id = cur.fetchone()[0]
            self._send_json({"id": vote_id, "asset_id": asset_id,
                             "vote_value": vote_value, "session_id": session_id,
                             "status": "saved"}, 201, rate_headers)
        except Exception as e:
            conn.rollback()
            self._send_json({"error": str(e)}, 500, rate_headers)
        finally:
            cur.close()
            conn.close()

    def _require_admin(self):
        """Check API key for admin endpoints. Returns True if authorized."""
        if not API_KEY:
            return True  # No key configured = open access
        req_key = self.headers.get("X-API-Key", "")
        return req_key == API_KEY

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path.startswith("/api/votes/"):
            return self._send_json({"error": "Not found"}, 404)

        if not self._require_admin():
            return self._send_json({"error": "Unauthorized"}, 401)

        asset_id = path.split("/api/votes/")[1]
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON"}, 400)

        vote_value = data.get("vote_value")
        session_id = data.get("session_id", "admin")

        if not vote_value:
            return self._send_json({"error": "vote_value required"}, 400)
        if not isinstance(vote_value, int) or vote_value < 1 or vote_value > 5:
            return self._send_json({"error": "vote_value must be 1-5"}, 400)

        conn = get_db()
        cur = conn.cursor()
        try:
            # Update ALL existing votes for this asset_id (preserves sessions)
            cur.execute(
                """UPDATE votes SET vote_value = %s, updated_at = NOW()
                   WHERE asset_id = %s""",
                (vote_value, asset_id),
            )
            updated = cur.rowcount
            if updated == 0:
                # No existing votes — create one with provided session_id
                cur.execute(
                    """INSERT INTO votes (asset_id, vote_value, session_id)
                       VALUES (%s, %s, %s) RETURNING id""",
                    (asset_id, vote_value, session_id),
                )
            conn.commit()
            self._send_json({"asset_id": asset_id, "vote_value": vote_value,
                             "updated": updated, "status": "updated"}, 200)
        except Exception as e:
            conn.rollback()
            self._send_json({"error": str(e)}, 500)
        finally:
            cur.close()
            conn.close()

    def do_PATCH(self):
        """PATCH /api/admin/reset-all — Bulk reset all votes to a value (admin only)."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/admin/reset-all":
            if not self._require_admin():
                return self._send_json({"error": "Unauthorized"}, 401)

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, 400)

            vote_value = data.get("vote_value", 4)
            if not isinstance(vote_value, int) or vote_value < 1 or vote_value > 5:
                return self._send_json({"error": "vote_value must be 1-5"}, 400)

            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("UPDATE votes SET vote_value = %s, updated_at = NOW()", (vote_value,))
                updated = cur.rowcount
                conn.commit()
                self._send_json({"updated": updated, "vote_value": vote_value, "status": "ok"}, 200)
            except Exception as e:
                conn.rollback()
                self._send_json({"error": str(e)}, 500)
            finally:
                cur.close()
                conn.close()
            return

        self._send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path.startswith("/api/votes/"):
            return self._send_json({"error": "Not found"}, 404)

        if not self._require_admin():
            return self._send_json({"error": "Unauthorized"}, 401)

        asset_id = path.split("/api/votes/")[1]
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM votes WHERE asset_id = %s", (asset_id,))
            deleted = cur.rowcount
            conn.commit()
            if deleted > 0:
                self._send_json({"asset_id": asset_id, "deleted": deleted, "status": "ok"}, 200)
            else:
                self._send_json({"error": "Asset not found"}, 404)
        except Exception as e:
            conn.rollback()
            self._send_json({"error": str(e)}, 500)
        finally:
            cur.close()
            conn.close()

    def log_message(self, format, *args):
        print(f"  [VoteAPI] {args[0]} {args[1]} {args[2]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SIMMOON Vote API")
    parser.add_argument("--port", type=int, default=9099, help="Port (default: 9099)")
    parser.add_argument("--host", "--bind", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--rate-limit", type=int, default=30, help="Max POST requests per minute per IP (default: 30, 0=disabled)")
    args = parser.parse_args()

    global rate_limiter
    if args.rate_limit > 0:
        rate_limiter = RateLimiter(max_requests=args.rate_limit, window_seconds=60)

    bind = args.host
    server = HTTPServer((bind, args.port), VoteHandler)
    print(f"\n  SIMMOON Vote API running on http://{bind}:{args.port}")
    print(f"  Endpoints:")
    print(f"    GET    /api/votes       — List all votes")
    print(f"    POST   /api/votes       — Submit vote (rate-limited: {args.rate_limit}/min)")
    print(f"    GET    /api/votes/:id   — Get vote for asset")
    print(f"    PUT    /api/votes/:id   — Update all votes for asset (admin)")
    print(f"    DELETE /api/votes/:id   — Delete all votes for asset (admin)")
    print(f"    PATCH  /api/admin/reset-all — Bulk reset all votes (admin)")
    print(f"    GET    /api/stats       — Vote statistics")
    print(f"    GET    /health          — Health check (DB + uptime)")
    if args.rate_limit > 0:
        print(f"  Rate limit: {args.rate_limit} POST/min per IP")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.server_close()


if __name__ == "__main__":
    # Force line-buffered stdout so logs appear in pipes/tee/tmux
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    main()
