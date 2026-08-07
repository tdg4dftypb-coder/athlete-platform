from pathlib import Path
import re
import sys
import json
from typing import Callable, Optional, Union


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
from biomarkers.trends.analyzer import BiomarkerTrendAnalyzer
from biomarkers.trends.serialization import BiomarkerTrendSerializer
from biomarkers.intelligence.analyzer import BiomarkerInsightAnalyzer
from biomarkers.intelligence.serialization import BiomarkerInsightSerializer
from core.database import Database
from dashboard.serialization import DashboardSerializer
from morning_briefing.builder import MorningBriefingBuilder
from morning_briefing.recommendations import MorningRecommendationEngine
from morning_briefing.serialization import MorningBriefingSerializer
from morning_briefing.provider import (
    MorningBriefingInputProvider,
    MorningBriefingInputError,
    EmptyMorningBriefingInputProvider,
)
from performance_lab.history import PerformanceTestHistoryBuilder
from performance_lab.provider import (
    PerformanceTestSessionProvider,
    PerformanceTestSessionProviderError,
    EmptyPerformanceTestSessionProvider,
)
from performance_lab.serialization import PerformanceTestHistorySerializer
from decision.audit_provider import (
    DecisionAuditRecordProvider,
    DecisionAuditRecordProviderError,
    EmptyDecisionAuditRecordProvider,
)
from decision.history_provider import (
    DecisionHistoryProvider,
    DecisionHistoryProviderError,
    EmptyDecisionHistoryProvider,
)
from decision.history_serialization_v2 import DecisionHistorySerializer
from decision.serialization_v2 import DecisionAuditRecordSerializer




_CANONICAL_CODE_RE = re.compile(r'^[a-z0-9_\-]+$')
_HISTORY_PREFIX = "/api/v1/biomarkers/history/"
_TRENDS_PREFIX = "/api/v1/biomarkers/trends/"
_INSIGHTS_PREFIX = "/api/v1/biomarkers/insights/"




def create_dashboard_wsgi_app(
    biomarkers_context: Optional[BiomarkersApplicationContext] = None,
    morning_briefing_provider: Optional[MorningBriefingInputProvider] = None,
    performance_lab_provider: Optional[PerformanceTestSessionProvider] = None,
    decision_audit_provider: Optional[DecisionAuditRecordProvider] = None,
    decision_history_provider: Optional[DecisionHistoryProvider] = None,
) -> Callable[[dict, Callable], list[bytes]]:

    """
    Factory creating WSGI application for local development server.
    Accepts optional BiomarkersApplicationContext for dependency injection in tests.
    Accepts optional MorningBriefingInputProvider for dependency injection in tests.
    Accepts optional PerformanceTestSessionProvider for dependency injection in tests.
    Accepts optional DecisionAuditRecordProvider for dependency injection in tests.
    """

    context = biomarkers_context or get_default_biomarkers_context()
    _briefing_provider: MorningBriefingInputProvider = (
        morning_briefing_provider or EmptyMorningBriefingInputProvider()
    )
    _briefing_builder = MorningBriefingBuilder()
    _recommendation_engine = MorningRecommendationEngine()
    _briefing_serializer = MorningBriefingSerializer()

    _performance_provider = (
        performance_lab_provider if performance_lab_provider is not None else EmptyPerformanceTestSessionProvider()
    )
    _performance_history_builder = PerformanceTestHistoryBuilder()
    _performance_history_serializer = PerformanceTestHistorySerializer()

    _decision_provider = (
        decision_audit_provider if decision_audit_provider is not None else EmptyDecisionAuditRecordProvider()
    )
    _decision_serializer = DecisionAuditRecordSerializer()

    _decision_history_provider = (
        decision_history_provider if decision_history_provider is not None else EmptyDecisionHistoryProvider()
    )
    _decision_history_serializer = DecisionHistorySerializer()






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

        # 3b. Route: GET /api/v1/biomarkers/trends/{canonical_code}
        if path_info.startswith(_TRENDS_PREFIX) and request_method == "GET":
            raw_code = path_info[len(_TRENDS_PREFIX):]

            # 400 — invalid canonical_code
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

            # Verify existence of biomarker in registry
            definition = context.registry.get(raw_code)
            if not definition:
                status = "404 Not Found"
                response_body = json.dumps(
                    {"error": f"Biomarker '{raw_code}' not found in registry."}
                ).encode("utf-8")
                headers = [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(response_body))),
                ]
                start_response(status, headers)
                return [response_body]

            try:
                # 1. Build history (may contain 0 measurements)
                builder = BiomarkerHistoryBuilder(
                    repository=context.repository,
                    biomarker_registry=context.registry,
                )
                history = builder.build_for_code(raw_code)

                # 2. Analyze trend
                analyzer = BiomarkerTrendAnalyzer()
                trend = analyzer.analyze(history)

                # 3. Serialize trend
                payload = BiomarkerTrendSerializer.serialize(trend)
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error generating biomarker trend."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 3c. Route: GET /api/v1/biomarkers/insights/{canonical_code}
        if path_info.startswith(_INSIGHTS_PREFIX) and request_method == "GET":
            raw_code = path_info[len(_INSIGHTS_PREFIX):]

            # 400 — invalid canonical_code
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

            # Verify existence of biomarker in registry
            definition = context.registry.get(raw_code)
            if not definition:
                status = "404 Not Found"
                response_body = json.dumps(
                    {"error": f"Biomarker '{raw_code}' not found in registry."}
                ).encode("utf-8")
                headers = [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(response_body))),
                ]
                start_response(status, headers)
                return [response_body]

            try:
                # 1. Build history (may contain 0 measurements)
                builder = BiomarkerHistoryBuilder(
                    repository=context.repository,
                    biomarker_registry=context.registry,
                )
                history = builder.build_for_code(raw_code)

                # 2. Analyze trend
                trend_analyzer = BiomarkerTrendAnalyzer()
                trend = trend_analyzer.analyze(history)

                # 3. Analyze insight
                insight_analyzer = BiomarkerInsightAnalyzer()
                insight = insight_analyzer.analyze(trend)

                # 4. Serialize insight
                payload = BiomarkerInsightSerializer.serialize(insight)
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error generating biomarker insight."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4. Route: GET /api/v1/morning-briefing
        if path_info == "/api/v1/morning-briefing" and request_method == "GET":
            try:
                input_data = _briefing_provider.get_input()
                briefing = _briefing_builder.build(input_data)
                briefing = _recommendation_engine.apply(briefing)
                payload = _briefing_serializer.serialize(briefing)
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except MorningBriefingInputError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Morning Briefing data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error generating Morning Briefing."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4.5 Route: GET /api/v1/performance-lab/history
        if path_info == "/api/v1/performance-lab/history" and request_method == "GET":
            try:
                sessions = _performance_provider.get_sessions()
                history = _performance_history_builder.build(sessions)
                payload = _performance_history_serializer.serialize(history)
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except PerformanceTestSessionProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Performance Lab data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Performance Lab history."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4.6 Route: GET /api/v1/decision-intelligence/latest
        if path_info == "/api/v1/decision-intelligence/latest" and request_method == "GET":
            try:
                record = _decision_provider.get_latest_record()
                if record is None:
                    payload = {"decision": None}
                else:
                    payload = {"decision": _decision_serializer.serialize(record)}
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except DecisionAuditRecordProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Decision Intelligence data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Decision Intelligence record."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4.7 Route: GET /api/v1/decision-intelligence/history
        if path_info == "/api/v1/decision-intelligence/history" and request_method == "GET":
            try:
                history = _decision_history_provider.get_history()
                payload = {"history": _decision_history_serializer.serialize(history)}
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except DecisionHistoryProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Decision Intelligence history data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Decision Intelligence history."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]




        # 5. CORS Preflight OPTIONS
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


def create_production_dashboard_wsgi_app(
    decision_db_path: Optional[Union[str, Path]] = None,
) -> Callable[[dict, Callable], list[bytes]]:
    """Production composition root for WSGI app wiring DuckDB Decision Repository."""
    from decision.persistence import DuckDbDecisionAuditRecordRepository
    from decision.persistence.paths import get_default_decisions_db_path
    from decision.repository_audit_provider import RepositoryDecisionAuditRecordProvider
    from decision.repository_history_provider import RepositoryDecisionHistoryProvider

    target_path = get_default_decisions_db_path(decision_db_path)
    repo = DuckDbDecisionAuditRecordRepository(db_path=str(target_path))
    decision_provider = RepositoryDecisionAuditRecordProvider(repository=repo)
    history_provider = RepositoryDecisionHistoryProvider(repository=repo)

    return create_dashboard_wsgi_app(
        decision_audit_provider=decision_provider,
        decision_history_provider=history_provider,
    )



# Default WSGI app instance for server process & default imports
dashboard_wsgi_app = create_dashboard_wsgi_app()


def run_server(port: int = 8000) -> None:
    from wsgiref.simple_server import make_server
    prod_app = create_production_dashboard_wsgi_app()
    print(
        f"Starting AthletePlatform HTTP Server on "
        f"http://127.0.0.1:{port}/api/v1/dashboard "
        f"& /api/v1/biomarkers "
        f"& /api/v1/biomarkers/history/{{canonical_code}}"
    )
    httpd = make_server("127.0.0.1", port, prod_app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    run_server()
