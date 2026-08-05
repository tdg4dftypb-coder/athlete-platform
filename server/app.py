from pathlib import Path
import sys
import json
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.composition import build_morning_coach_use_case
from biomarkers.composition import build_biomarkers_dashboard_use_case
from core.database import Database
from dashboard.serialization import DashboardSerializer


def dashboard_wsgi_app(environ: dict, start_response: Callable) -> list[bytes]:
    """WSGI application serving GET /api/v1/dashboard and GET /api/v1/biomarkers."""
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
                payload = build_biomarkers_dashboard_use_case()
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                # Privacy-safe error response (zero stack trace, zero health data)
                response_body = json.dumps({"error": "Internal server error generating biomarkers payload"}).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "GET, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type"),
            ]
            start_response(status, headers)
            return [response_body]

        elif request_method != "OPTIONS":
            status = "405 Method Not Allowed"
            response_body = json.dumps({"error": "Method Not Allowed"}).encode("utf-8")
            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
                ("Access-Control-Allow-Origin", "*"),
            ]
            start_response(status, headers)
            return [response_body]

    # 3. CORS Preflight OPTIONS
    if request_method == "OPTIONS":
        headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
        ]
        start_response("204 No Content", headers)
        return [b""]

    # 4. 404 Not Found fallback
    status = "404 Not Found"
    response_body = json.dumps({"error": "Not Found"}).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(response_body))),
    ]
    start_response(status, headers)
    return [response_body]


def run_server(port: int = 8000) -> None:
    from wsgiref.simple_server import make_server
    print(f"Starting AthletePlatform HTTP Server on http://127.0.0.1:{port}/api/v1/dashboard & /api/v1/biomarkers")
    httpd = make_server("127.0.0.1", port, dashboard_wsgi_app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run_server()
