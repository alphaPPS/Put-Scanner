#!/usr/bin/env python3
"""
Delta Put Scanner — local web page
====================================
Runs the same scan as put_scanner.py, but in your browser instead of the
terminal. Everything runs on your own computer: the page is served from
127.0.0.1 only, and your Robinhood login goes straight from this program
to Robinhood.

Usage:
    python3 put_scanner_web.py                 (opens http://127.0.0.1:8765)
    python3 put_scanner_web.py --port 9000
    python3 put_scanner_web.py --no-browser

Press Ctrl+C in the terminal to stop it.

Requirements:
    pip3 install robin_stocks tabulate
"""

import os
import re
import sys
import json
import types
import secrets
import argparse
import threading
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import put_scanner as ps
import robin_stocks.robinhood.authentication as rh_auth

rh = ps.rh

DELTA_TOL   = 0.05
TOKEN_PATH  = os.path.expanduser("~/.tokens/robinhood.pickle")
CODE_WAIT_S = 120
BASE_DIR    = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
PAGE_PATH   = os.path.join(BASE_DIR, "web", "index.html")
TICKER_RE   = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


# ── Shared state ──────────────────────────────────────────────────────────────

lock = threading.Lock()

login_state = {
    "status":  "logged_out",   # logged_out | working | need_code | approve_in_app | logged_in
    "message": "",
}
code_event = threading.Event()
code_value = {"code": None}

scan_state = {
    "running": False,
    "stop":    False,
    "expiry":  None,
    "delta":   None,
    "total":   0,
    "done":    0,
    "current": None,
    "rows":    [],
    "error":   None,
}


LOGIN_NOTES = {
    "logged_out":     "Waiting for you to log in on the page.",
    "need_code":      "Enter the verification code on the page.",
    "approve_in_app": "Approve this login in your Robinhood app.",
    "logged_in":      "Logged in. Run a scan from the page.",
}


def set_login(status, message=""):
    with lock:
        changed = (login_state["status"], login_state["message"]) != (status, message)
        login_state["status"] = status
        login_state["message"] = message
    # Mirror login progress in the terminal so it never looks stuck.
    if changed and status in LOGIN_NOTES:
        note = f"{message}  " if message and status != "need_code" else ""
        print(f"  Login: {note}{LOGIN_NOTES[status]}", flush=True)


# ── Robinhood login, driven from the page ─────────────────────────────────────
# robin_stocks asks for verification codes with input() and reports progress
# with print(). We swap those names inside its authentication module so the
# questions show up on the web page instead of the terminal.

class NeedCredentials(Exception):
    pass


def _web_input(prompt=""):
    if "verification code" not in prompt:
        raise NeedCredentials()
    code_event.clear()
    code_value["code"] = None
    set_login("need_code", prompt.strip().rstrip(":"))
    if not code_event.wait(CODE_WAIT_S):
        set_login("working", "No code entered, waiting for Robinhood...")
        return ""
    set_login("working", "Checking code...")
    return code_value["code"] or ""


def _no_getpass(prompt=""):
    raise NeedCredentials()


def _web_print(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    if "robinhood app" in text.lower():
        set_login("approve_in_app", "Approve this login in your Robinhood app.")
    print(*args, **kwargs)


rh_auth.input   = _web_input
rh_auth.getpass = types.SimpleNamespace(getpass=_no_getpass)
rh_auth.print   = _web_print


def run_login(username=None, password=None, mfa_code=None):
    try:
        data = rh.login(
            username=username,
            password=password,
            expiresIn=86400,
            store_session=True,
            mfa_code=mfa_code or None,
        )
    except NeedCredentials:
        set_login("logged_out", "Saved session expired. Please log in." if username is None else "")
        return
    except Exception as e:
        set_login("logged_out", f"Login failed: {e}")
        return

    if data:
        set_login("logged_in", "")
    else:
        set_login("logged_out", "Login failed. Check your email and password.")


def start_login(username=None, password=None, mfa_code=None):
    with lock:
        if login_state["status"] in ("working", "need_code", "approve_in_app"):
            return False
        login_state["status"] = "working"
        login_state["message"] = "Logging in..."
    threading.Thread(target=run_login, args=(username, password, mfa_code), daemon=True).start()
    return True


def logout():
    try:
        rh.logout()
    except Exception:
        pass
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    set_login("logged_out", "Logged out.")


# ── Scan ──────────────────────────────────────────────────────────────────────

def scan_ticker(ticker, expiry, target_delta):
    """Same lookups and math as put_scanner.main(), returned as numbers."""
    row = {
        "ticker": ticker,
        "stock":  ps.get_stock_price(ticker),
        "buy":    ps.get_analyst_rating(ticker),
        "div":    ps.get_dividend_yield(ticker),
        "strike": None, "mark": None, "bid": None, "ask": None, "delta": None,
        "iv": None, "oi": None, "volume": None, "status": None,
        "weekly": None, "annual": None,
    }
    result = ps.find_best_put(ticker, expiry, target_delta, DELTA_TOL)

    if result is None:
        row["status"] = "no chain"
        return row
    if result.get("error"):
        row["status"] = "error"
        return row

    for key in ("strike", "mark", "bid", "ask", "delta", "iv", "oi", "volume", "status"):
        row[key] = result[key]

    # Weekly % return = (Mark / Strike) * 100
    if result["mark"] and result["strike"]:
        row["weekly"] = (result["mark"] / result["strike"]) * 100
        row["annual"] = row["weekly"] * 52
    return row


def run_scan(tickers, expiry, target_delta):
    for ticker in tickers:
        with lock:
            if scan_state["stop"]:
                break
            scan_state["current"] = ticker
        try:
            row = scan_ticker(ticker, expiry, target_delta)
        except Exception:
            row = {"ticker": ticker, "status": "error"}
        with lock:
            scan_state["rows"].append(row)
            scan_state["done"] += 1
            done, total = scan_state["done"], scan_state["total"]
        print(f"  [{done:2}/{total}] {ticker:<6} {row.get('status') or ''}", flush=True)
    with lock:
        scan_state["running"] = False
        scan_state["current"] = None
    print("  Scan finished. Results are on the page.", flush=True)


def start_scan(tickers, delta, expiry):
    with lock:
        if scan_state["running"]:
            return "A scan is already running."
        scan_state.update({
            "running": True, "stop": False, "expiry": expiry, "delta": delta,
            "total": len(tickers), "done": 0, "current": None, "rows": [], "error": None,
        })
    threading.Thread(target=run_scan, args=(tickers, expiry, delta), daemon=True).start()
    return None


def parse_scan_request(body):
    """Validate the page's scan request. Returns (tickers, delta, expiry, error)."""
    raw = body.get("tickers") or []
    tickers = []
    for t in raw:
        t = str(t).strip().upper()
        if t and not t.startswith("#") and t not in tickers:
            if not TICKER_RE.match(t):
                return None, None, None, f"'{t}' doesn't look like a ticker."
            tickers.append(t)
    if not tickers:
        return None, None, None, "Add at least one ticker."

    try:
        delta = float(body.get("delta", 0.10))
    except (TypeError, ValueError):
        return None, None, None, "Delta must be a number like 0.10."
    if not 0 < delta < 1:
        return None, None, None, "Delta must be between 0 and 1, like 0.10."

    expiry_raw = str(body.get("expiry") or "").strip()
    if not expiry_raw:
        expiry = ps.next_friday()
    else:
        try:
            expiry = ps.parse_expiry(expiry_raw)
        except SystemExit:
            return None, None, None, f"Couldn't read the date '{expiry_raw}'."
    return tickers, delta, expiry, None


# ── HTTP server ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "PutScanner"
    page_token = ""
    allowed_hosts = set()

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self):
        # Blocks other websites from reaching this server through DNS tricks.
        return self.headers.get("Host", "") in self.allowed_hosts

    def _token_ok(self):
        return secrets.compare_digest(self.headers.get("X-Scanner-Token", ""), self.page_token)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        if self.path in ("/", "/index.html"):
            with open(PAGE_PATH, "rb") as f:
                html = f.read().replace(b"__SCANNER_TOKEN__", self.page_token.encode())
            return self._send(200, html, "text/html; charset=utf-8")
        if self.path == "/api/status":
            if not self._token_ok():
                return self._send(403, {"error": "forbidden"})
            with lock:
                return self._send(200, {
                    "login": dict(login_state),
                    "scan": {k: v for k, v in scan_state.items() if k != "stop"},
                    "has_saved_session": os.path.exists(TOKEN_PATH),
                    "next_friday": ps.next_friday(),
                    "delta_tol": DELTA_TOL,
                })
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok() or not self._token_ok():
            return self._send(403, {"error": "forbidden"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "bad request"})

        if self.path == "/api/login":
            if body.get("saved"):
                ok = start_login()
            else:
                email = str(body.get("email", "")).strip()
                password = str(body.get("password", ""))
                if not email or not password:
                    return self._send(400, {"error": "Enter your email and password."})
                ok = start_login(email, password, str(body.get("mfa", "")).strip())
            return self._send(200 if ok else 409, {"ok": ok})

        if self.path == "/api/code":
            code_value["code"] = str(body.get("code", "")).strip()
            code_event.set()
            return self._send(200, {"ok": True})

        if self.path == "/api/logout":
            logout()
            return self._send(200, {"ok": True})

        if self.path == "/api/scan":
            with lock:
                logged_in = login_state["status"] == "logged_in"
            if not logged_in:
                return self._send(400, {"error": "Log in to Robinhood first."})
            tickers, delta, expiry, err = parse_scan_request(body)
            if err:
                return self._send(400, {"error": err})
            err = start_scan(tickers, delta, expiry)
            return self._send(409 if err else 200, {"error": err} if err else {"ok": True})

        if self.path == "/api/stop":
            with lock:
                scan_state["stop"] = True
            return self._send(200, {"ok": True})

        self._send(404, {"error": "not found"})


def make_server(port):
    try:
        return ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        print(f"Port {port} is busy, picking another one.")
        return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def main():
    parser = argparse.ArgumentParser(description="Delta put scanner, local web page")
    parser.add_argument("--port", type=int, default=8765, help="Port to use (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the browser automatically")
    args = parser.parse_args()

    server = make_server(args.port)
    port = server.server_address[1]
    Handler.page_token = secrets.token_urlsafe(24)
    Handler.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    url = f"http://127.0.0.1:{port}/"

    print(f"\n{'='*62}")
    print(f"  Delta Put Scanner (web)")
    print(f"  Open  : {url}")
    print(f"  Stop  : press Ctrl+C here")
    print(f"{'='*62}\n")

    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped. Done.\n")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
