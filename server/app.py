from pathlib import Path
import sys
import json
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.composition import build_morning_coach_use_case
from core.database import Database
from dashboard.serialization import DashboardSerializer


def dashboard_wsgi_app(environ: dict, start_response: Callable) -> list[bytes]:
    """WSGI application serving GET /api/v1/dashboard with DashboardSerializer payload v1.0."""
    path_info = environ.get("PATH_INFO", "")
    request_method = environ.get("REQUEST_METHOD", "GET")

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
        except Exception as exc:
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

    if request_method == "OPTIONS":
        headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
        ]
        start_response("204 No Content", headers)
        return [b""]

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
    print(f"Starting AthleteDashboard HTTP Server on http://127.0.0.1:{port}/api/v1/dashboard")
    httpd = make_server("127.0.0.1", port, dashboard_wsgi_app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run_server()
