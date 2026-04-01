import ipaddress
import logging
import os
import threading
from typing import Optional

try:
    from flask import Flask, jsonify, render_template, request
except ImportError:
    raise RuntimeError("Flask is required. Install it with: pip install flask")

_log = logging.getLogger("phantom_snare.vault")
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class Vault:
    def __init__(self, evidence_store=None, shield=None, observer=None,
                 deceptor=None, host="127.0.0.1", port=5000, debug=True):
        self._store = evidence_store
        self._shield = shield
        self._observer = observer
        self._deceptor = deceptor
        self._host = host
        self._port = port
        self._debug = debug
        self._thread: Optional[threading.Thread] = None
        self._app = Flask(__name__, template_folder=_TEMPLATE_DIR)
        self._app.config["JSON_SORT_KEYS"] = False
        self._register_routes()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_flask, daemon=True, name="vault-dashboard")
        self._thread.start()
        _log.info("[Vault] Dashboard at http://%s:%d", self._host, self._port)

    def _run_flask(self):
        if not self._debug:
            logging.getLogger("werkzeug").setLevel(logging.WARNING)
        self._app.run(host=self._host, port=self._port, debug=self._debug,
                      use_reloader=False, threaded=True)

    def _register_routes(self):
        app = self._app

        @app.route("/")
        def index():
            return render_template("dashboard.html")

        @app.route("/api/status")
        def api_status():
            honey_hits = self._store.get_honey_token_hit_count() if self._store else 0
            blocked_count = len(self._store.get_blocked_ips()) if self._store else 0
            return jsonify({"status": "running", "honey_token_hits": honey_hits, "blocked_ips": blocked_count})

        @app.route("/api/captures")
        def api_captures():
            limit = _safe_int(request.args.get("limit", "50"), 50, 1, 500)
            return jsonify(self._store.get_recent_captures(limit) if self._store else [])

        @app.route("/api/events")
        def api_events():
            limit = _safe_int(request.args.get("limit", "100"), 100, 1, 1000)
            return jsonify(self._store.get_recent_events(limit) if self._store else [])

        @app.route("/api/risk_scores")
        def api_risk_scores():
            return jsonify(self._observer.get_ip_risk_summary() if self._observer else [])

        @app.route("/api/ip_stats")
        def api_ip_stats():
            return jsonify(self._store.get_ip_stats() if self._store else [])

        @app.route("/api/blocked")
        def api_blocked():
            return jsonify(self._store.get_blocked_ips() if self._store else [])

        @app.route("/api/block", methods=["POST"])
        def api_block():
            body = request.get_json(silent=True) or {}
            ip = str(body.get("ip", "")).strip()
            reason = str(body.get("reason") or "Manual block").strip()
            if not ip:
                return jsonify({"error": "ip is required"}), 400
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                return jsonify({"error": f"Invalid IP address: {ip!r}"}), 400
            if self._shield:
                self._shield.block_ip(ip, reason)
            elif self._store:
                self._store.block_ip(ip, reason)
            else:
                return jsonify({"error": "No shield or store available"}), 503
            return jsonify({"ok": True, "ip": ip})

        @app.route("/api/unblock", methods=["POST"])
        def api_unblock():
            body = request.get_json(silent=True) or {}
            ip = str(body.get("ip", "")).strip()
            if not ip:
                return jsonify({"error": "ip is required"}), 400
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                return jsonify({"error": f"Invalid IP address: {ip!r}"}), 400
            if self._shield:
                self._shield.unblock_ip(ip)
            elif self._store:
                self._store.unblock_ip(ip)
            else:
                return jsonify({"error": "No shield or store available"}), 503
            return jsonify({"ok": True, "ip": ip})

        @app.route("/api/honey_tokens")
        def api_honey_tokens():
            tokens = self._deceptor.get_honey_tokens() if self._deceptor else []
            hits = self._store.get_honey_token_hits(50) if self._store else []
            return jsonify({"tokens": tokens, "hits": hits})

        @app.route("/api/site_visits")
        def api_site_visits():
            limit = _safe_int(request.args.get("limit", "50"), 50, 1, 500)
            return jsonify(self._store.get_recent_site_visits(limit) if self._store else [])


def _safe_int(value, default, min_val, max_val):
    try:
        return max(min_val, min(int(value), max_val))
    except (TypeError, ValueError):
        return default
