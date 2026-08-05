from pathlib import Path
import re
import sys
import json
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.composition import build_morning_coach_use_case
from biomarkers.composition import (
    BiomarkersApplicationContext,
    build_biomarkers_dashboard_use_case,
    get_default_biomarkers_context,
)
from biomarkers.history import BiomarkerHistoryBuilder
from biomarkers.history_serialization import BiomarkerHistorySerializer
from core.database import Database
from dashboard.serialization import DashboardSerializer

_CANONICAL_CODE_RE = re.compile(r'^[a-z0-9_\-]+$')
_HISTORY_PREFIX = "/api/v1/biomarkers/history/"


def create_dashboard_wsgi_app(
    biomarkers_context: Optional[BiomarkersApplicationContext] = None,
) -> Callable[[dict, Callable], list[bytes]]:
    """
    Factory creating WSGI application for local development server.
    Accepts optional BiomarkersApplicationContext for dependency injection in tests.
    """
    context = biomarkers_context or get_default_biomarkers_context()

    def wsgi_app(environ: dict, start_response: Callable) -> list[bytes]:
        path_info = environ.get("PATH_INFO", "")
        request_method = environ.get("REQUEST_METHOD", "GET")

        # 1. Route: GET /api/v1/dashboard
        if path_info == "/api/v1/dashboard" and request_method == "GET":
            database = Database()
            try:
                use_case = build_morning_coach_use_case(database)
                result = use_case.run()
                if result.dashboard is None:
                    status = "500 Internal Server Error"
                    response_body = json.dumps({"error": "Dashboard generation returned null"}).encode("utf-8")
                else:
                    payload = DashboardSerializer().serialize(result.dashboard)
                    status = "200 OK"
                    response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps({"error": "Internal server error generating dashboard payload"}).encode("utf-8")
            finally:
                database.close()

            # Historical endpoint retains wildcard CORS
            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "GET, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type"),
            ]
            start_response(status, headers)
            return [response_body]

        # 2. Route: /api/v1/biomarkers
        if path_info == "/api/v1/biomarkers":
            if request_method == "GET":
                try:
                    payload = build_biomarkers_dashboard_use_case(context=context)
                    status = "200 OK"
                    response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
                except Exception:
                    status = "500 Internal Server Error"
                    response_body = json.dumps({"error": "Internal server error generating biomarkers payload"}).encode("utf-8")

                # Hardened Endpoint: Wildcard CORS 'Access-Control-Allow-Origin: *' is omitted.
                # Client connects via Vite same-origin proxy (/api -> http://127.0.0.1:8000).
                headers = [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(response_body))),
                ]
                start_response(status, headers)
                return [response_body]

            elif request_method != "OPTIONS":
                status = "405 Method Not Allowed"
                response_body = json.dumps({"error": "Method Not Allowed"}).encode("utf-8")
                headers = [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(response_body))),
                ]
                start_response(status, headers)
                return [response_body]

        # 3. Route: GET /api/v1/biomarkers/history/{canonical_code}
        if path_info.startswith(_HISTORY_PREFIX) and request_method == "GET":
            raw_code = path_info[len(_HISTORY_PREFIX):]

            # 400 — invalid canonical_code (empty or forbidden characters)
            if not raw_code or not _CANONICAL_CODE_RE.match(raw_code):
                status = "400 Bad Request"
                response_body = json.dumps(
                    {"error": "Invalid canonical_code. Use only lowercase letters, digits, underscores, or hyphens."}
                ).encode("utf-8")
                headers = [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(response_body))),
                ]
                start_response(status, headers)
                return [response_body]

            try:
                builder = BiomarkerHistoryBuilder(
                    repository=context.repository,
                    biomarker_registry=context.registry,
                )
                history = builder.build_for_code(raw_code)

                if not history.measurements:
                    status = "404 Not Found"
                    response_body = json.dumps(
                        {"error": f"No history found for biomarker '{raw_code}'."}
                    ).encode("utf-8")
                else:
                    payload = BiomarkerHistorySerializer.serialize(history)
                    status = "200 OK"
                    response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error generating biomarker history."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4. CORS Preflight OPTIONS
        if request_method == "OPTIONS":
            headers = [
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "GET, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type"),
            ]
            start_response("204 No Content", headers)
            return [b""]

        # 5. 404 Not Found fallback
        status = "404 Not Found"
        response_body = json.dumps({"error": "Not Found"}).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(response_body))),
        ]
        start_response(status, headers)
        return [response_body]

    return wsgi_app


# Default WSGI app instance for server process & default imports
dashboard_wsgi_app = create_dashboard_wsgi_app()


def run_server(port: int = 8000) -> None:
    from wsgiref.simple_server import make_server
    print(
        f"Starting AthletePlatform HTTP Server on "
        f"http://127.0.0.1:{port}/api/v1/dashboard "
        f"& /api/v1/biomarkers "
        f"& /api/v1/biomarkers/history/{{canonical_code}}"
    )
    httpd = make_server("127.0.0.1", port, dashboard_wsgi_app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run_server()
