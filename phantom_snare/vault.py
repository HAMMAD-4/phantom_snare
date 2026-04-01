import ipaddress
import logging
import os
import threading
from typing import Optional

_module_logger = logging.getLogger("phantom_snare.vault")

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _require_flask():
    try:
        import flask  # noqa: F401
        return flask
    except ImportError:
        raise RuntimeError(
            "Flask is required for the Vault dashboard.\n"
            "Install it with:  pip install flask"
        )


class Vault:
    def __init__(
        self,
        evidence_store=None,
        shield=None,
        observer=None,
        deceptor=None,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: bool = True,
    ) -> None:
        flask = _require_flask()
        self._store = evidence_store
        self._shield = shield
        self._observer = observer
        self._deceptor = deceptor
        self._host = host
        self._port = port
        self._debug = debug
        self._thread: Optional[threading.Thread] = None

        self._app = flask.Flask(
            __name__, template_folder=_TEMPLATE_DIR
        )
        self._app.config["JSON_SORT_KEYS"] = False
        self._register_routes()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_flask,
            daemon=True,
            name="vault-dashboard",
        )
        self._thread.start()
        _module_logger.info(
            "[Vault] Dashboard running at http://%s:%d", self._host, self._port
        )

    def _run_flask(self) -> None:
        import logging as _log
        if not self._debug:
            _log.getLogger("werkzeug").setLevel(_log.WARNING)
        self._app.run(
            host=self._host,
            port=self._port,
            debug=self._debug,
            use_reloader=False,
            threaded=True,
        )

    def _register_routes(self) -> None:
        from flask import jsonify, render_template, request

        app = self._app

        @app.route("/")
        def index():  # type: ignore[return]
            return render_template("dashboard.html")

        @app.route("/api/status")
        def api_status():  # type: ignore[return]
            honey_hits = (
                self._store.get_honey_token_hit_count()
                if self._store else 0
            )
            blocked_count = (
                len(self._store.get_blocked_ips())
                if self._store else 0
            )
            return jsonify(
                {
                    "status": "running",
                    "honey_token_hits": honey_hits,
                    "blocked_ips": blocked_count,
                }
            )

        @app.route("/api/captures")
        def api_captures():  # type: ignore[return]
            limit = _safe_int(request.args.get("limit", "50"), 50, 1, 500)
            data = self._store.get_recent_captures(limit) if self._store else []
            return jsonify(data)

        @app.route("/api/events")
        def api_events():  # type: ignore[return]
            limit = _safe_int(request.args.get("limit", "100"), 100, 1, 1000)
            data = self._store.get_recent_events(limit) if self._store else []
            return jsonify(data)

        @app.route("/api/risk_scores")
        def api_risk_scores():  # type: ignore[return]
            data = self._observer.get_ip_risk_summary() if self._observer else []
            return jsonify(data)

        @app.route("/api/ip_stats")
        def api_ip_stats():  # type: ignore[return]
            data = self._store.get_ip_stats() if self._store else []
            return jsonify(data)

        @app.route("/api/blocked")
        def api_blocked():  # type: ignore[return]
            data = self._store.get_blocked_ips() if self._store else []
            return jsonify(data)

        @app.route("/api/block", methods=["POST"])
        def api_block():  # type: ignore[return]
            body = request.get_json(silent=True) or {}
            ip = str(body.get("ip", "")).strip()
            reason = str(body.get("reason") or "Manual block from Vault dashboard").strip()
            if not ip:
                return jsonify({"error": "ip is required"}), 400
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                return jsonify({"error": f"Invalid IP address: {ip!r}"}), 400
            if self._shield:
                self._shield.block_ip(ip, reason)
                if not self._shield.is_blocked(ip):
                    return jsonify({"error": "Failed to persist block"}), 500
            elif self._store:
                self._store.block_ip(ip, reason)
                if not self._store.is_blocked(ip):
                    return jsonify({"error": "Failed to persist block"}), 500
            else:
                return jsonify({"error": "No shield or store available"}), 503
            return jsonify({"ok": True, "ip": ip})

        @app.route("/api/unblock", methods=["POST"])
        def api_unblock():  # type: ignore[return]
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
        def api_honey_tokens():  # type: ignore[return]
            tokens = self._deceptor.get_honey_tokens() if self._deceptor else []
            hits = (
                self._store.get_honey_token_hits(50) if self._store else []
            )
            return jsonify({"tokens": tokens, "hits": hits})

        @app.route("/api/site_visits")
        def api_site_visits():  # type: ignore[return]
            limit = _safe_int(request.args.get("limit", "50"), 50, 1, 500)
            data = self._store.get_recent_site_visits(limit) if self._store else []
            return jsonify(data)


def _safe_int(value: object, default: int, min_val: int, max_val: int) -> int:
    try:
        n = int(value)  # type: ignore[arg-type]
        return max(min_val, min(n, max_val))
    except (TypeError, ValueError):
        return default
