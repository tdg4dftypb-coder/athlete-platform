from pathlib import Path
import os
import re
import sys
import json
from typing import Callable, Optional, Union
from datetime import date
from urllib.parse import parse_qs


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.composition import build_morning_coach_use_case
from activity_calendar.read_model import (
    ActivityCalendarBuilder,
    ActivityCalendarProviderError,
    RepositoryCalendarPlannedSessionProvider,
)
from activity_calendar.serialization import ActivityCalendarSerializer
from biomarkers.composition import (
    BiomarkersApplicationContext,
    build_biomarkers_dashboard_use_case,
    get_default_biomarkers_context,
)
from biomarkers.dashboard import BiomarkersDashboardBuilder
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
from training_plan.history import (
    PrescriptionHistoryProvider,
    PrescriptionHistoryProviderError,
    RepositoryPrescriptionHistoryProvider,
    RepositoryTrainingPlanHistoryProvider,
    TrainingPlanHistoryProvider,
    TrainingPlanHistoryProviderError,
)
from training_plan.serializers import (
    FinalSessionPrescriptionHistorySerializer,
    FinalSessionPrescriptionSerializer,
    TrainingPlanHistorySerializer,
    TrainingPlanSerializer,
)
from production_runtime.visibility import ProductionRuntimeVisibilityError


_CANONICAL_CODE_RE = re.compile(r'^[a-z0-9_\-]+$')
_HISTORY_PREFIX = "/api/v1/biomarkers/history/"
_TRENDS_PREFIX = "/api/v1/biomarkers/trends/"
_INSIGHTS_PREFIX = "/api/v1/biomarkers/insights/"


class EmptyTrainingPlanHistoryProvider(TrainingPlanHistoryProvider):
    def get_latest_plan(self):
        return None
    def get_plan_history(self):
        from training_plan.history import TrainingPlanHistory
        return TrainingPlanHistory(records=())


class EmptyPrescriptionHistoryProvider(PrescriptionHistoryProvider):
    def get_latest_prescription(self):
        return None
    def get_prescription_history(self):
        from training_plan.history import FinalSessionPrescriptionHistory
        return FinalSessionPrescriptionHistory(records=())


class EmptyActivityEventProvider:
    def load_between(self, start, end):
        return []


class EmptyPlannedSessionProvider:
    def get_planned_sessions(self, target_date):
        return ()


class EmptyProductionRuntimeVisibilityReader:
    def get_latest_payload(self):
        return {"schema_version": "1.0", "runtime": None}


def create_dashboard_wsgi_app(
    biomarkers_context: Optional[BiomarkersApplicationContext] = None,
    morning_briefing_provider: Optional[MorningBriefingInputProvider] = None,
    performance_lab_provider: Optional[PerformanceTestSessionProvider] = None,
    decision_audit_provider: Optional[DecisionAuditRecordProvider] = None,
    decision_history_provider: Optional[DecisionHistoryProvider] = None,
    training_plan_history_provider: Optional[TrainingPlanHistoryProvider] = None,
    prescription_history_provider: Optional[PrescriptionHistoryProvider] = None,
    activity_calendar_builder: Optional[ActivityCalendarBuilder] = None,
    production_runtime_visibility_reader=None,
    healthkit_ingestion_endpoint=None,
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

    _tp_history_provider = (
        training_plan_history_provider if training_plan_history_provider is not None else EmptyTrainingPlanHistoryProvider()
    )
    _tp_serializer = TrainingPlanSerializer()
    _tp_history_serializer = TrainingPlanHistorySerializer()

    _rx_history_provider = (
        prescription_history_provider if prescription_history_provider is not None else EmptyPrescriptionHistoryProvider()
    )
    _rx_serializer = FinalSessionPrescriptionSerializer()
    _rx_history_serializer = FinalSessionPrescriptionHistorySerializer()

    _calendar_builder = activity_calendar_builder or ActivityCalendarBuilder(
        activity_provider=EmptyActivityEventProvider(),
        planned_session_provider=EmptyPlannedSessionProvider(),
    )
    _calendar_serializer = ActivityCalendarSerializer()
    _runtime_visibility = production_runtime_visibility_reader or EmptyProductionRuntimeVisibilityReader()






    def wsgi_app(environ: dict, start_response: Callable) -> list[bytes]:
        path_info = environ.get("PATH_INFO", "")
        request_method = environ.get("REQUEST_METHOD", "GET")

        if path_info == "/api/v1/ingestion/healthkit":
            if request_method != "POST":
                status, payload = "405 Method Not Allowed", {"error": "method_not_allowed"}
            elif healthkit_ingestion_endpoint is None:
                status, payload = "503 Service Unavailable", {"error": "healthkit_ingestion_not_configured"}
            else:
                status, payload = healthkit_ingestion_endpoint.handle(environ)
            response_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
                ("Cache-Control", "no-store"),
            ]
            start_response(status, headers)
            return [response_body]

        if path_info == "/api/v1/production-runtime/latest" and request_method == "GET":
            try:
                payload = _runtime_visibility.get_latest_payload()
                status = "200 OK"
            except ProductionRuntimeVisibilityError:
                payload = {"error": "Production Runtime visibility data is unavailable."}
                status = "503 Service Unavailable"
            except Exception:
                payload = {"error": "Internal server error fetching Production Runtime visibility."}
                status = "500 Internal Server Error"
            response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            headers = [("Content-Type", "application/json; charset=utf-8"),
                       ("Content-Length", str(len(response_body)))]
            start_response(status, headers)
            return [response_body]

        # Canonical bounded month/day history projection.
        if path_info == "/api/v1/activity-calendar" and request_method == "GET":
            try:
                query = parse_qs(environ.get("QUERY_STRING", ""))
                start_values = query.get("start_date", [])
                end_values = query.get("end_date", [])
                if len(start_values) != 1 or len(end_values) != 1:
                    raise ValueError(
                        "start_date and end_date are required exactly once"
                    )
                start_date = date.fromisoformat(start_values[0])
                end_date = date.fromisoformat(end_values[0])
                calendar = _calendar_builder.build(start_date, end_date)
                payload = _calendar_serializer.serialize(calendar)
                status = "200 OK"
            except (ValueError, TypeError) as error:
                status = "400 Bad Request"
                payload = {"error": str(error)}
            except ActivityCalendarProviderError:
                status = "503 Service Unavailable"
                payload = {
                    "error": "Activity Calendar data source is temporarily unavailable."
                }
            except Exception:
                status = "500 Internal Server Error"
                payload = {"error": "Internal server error fetching Activity Calendar."}

            response_body = json.dumps(
                payload, indent=2, ensure_ascii=False
            ).encode("utf-8")
            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

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

        # 4.8 Route: GET /api/v1/training-plan/latest
        if path_info == "/api/v1/training-plan/latest" and request_method == "GET":
            try:
                plan = _tp_history_provider.get_latest_plan()
                payload = {"plan": _tp_serializer.serialize(plan) if plan else None}
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except TrainingPlanHistoryProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Training Plan data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Training Plan record."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4.9 Route: GET /api/v1/training-plan/history
        if path_info == "/api/v1/training-plan/history" and request_method == "GET":
            try:
                history = _tp_history_provider.get_plan_history()
                payload = {"history": _tp_history_serializer.serialize(history)}
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except TrainingPlanHistoryProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Training Plan history data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Training Plan history."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4.10 Route: GET /api/v1/training-plan/prescriptions/latest
        if path_info == "/api/v1/training-plan/prescriptions/latest" and request_method == "GET":
            try:
                rx = _rx_history_provider.get_latest_prescription()
                payload = {"prescription": _rx_serializer.serialize(rx) if rx else None}
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except PrescriptionHistoryProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Prescription data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Prescription record."}
                ).encode("utf-8")

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
            start_response(status, headers)
            return [response_body]

        # 4.11 Route: GET /api/v1/training-plan/prescriptions/history
        if path_info == "/api/v1/training-plan/prescriptions/history" and request_method == "GET":
            try:
                history = _rx_history_provider.get_prescription_history()
                payload = {"history": _rx_history_serializer.serialize(history)}
                status = "200 OK"
                response_body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            except PrescriptionHistoryProviderError:
                status = "503 Service Unavailable"
                response_body = json.dumps(
                    {"error": "Prescription history data source is temporarily unavailable."}
                ).encode("utf-8")
            except Exception:
                status = "500 Internal Server Error"
                response_body = json.dumps(
                    {"error": "Internal server error fetching Prescription history."}
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
    biomarkers_db_path: Optional[Union[str, Path]] = None,
    health_db_path: Optional[Union[str, Path]] = None,
    training_plan_db_path: Optional[Union[str, Path]] = None,
    activity_reconciliation_db_path: Optional[Union[str, Path]] = None,
    runtime_audit_db_path: Optional[Union[str, Path]] = None,
    plan_adaptation_db_path: Optional[Union[str, Path]] = None,
) -> Callable[[dict, Callable], list[bytes]]:
    """Production composition root for WSGI app wiring real Athlete Platform sources, DuckDB Decision Repository, and Training Plan Repository."""
    from decision.persistence import DuckDbDecisionAuditRecordRepository
    from decision.persistence.paths import get_default_decisions_db_path
    from decision.repository_audit_provider import RepositoryDecisionAuditRecordProvider
    from decision.repository_history_provider import RepositoryDecisionHistoryProvider
    from athlete.memory.repository import AthleteMemoryRepository
    from morning_briefing.production_provider import ProductionMorningBriefingInputProvider
    from repositories.health_repository import HealthRepository
    from training_plan.history import (
        RepositoryPrescriptionHistoryProvider,
        RepositoryTrainingPlanHistoryProvider,
    )
    from training_plan.persistence.duckdb_repository import (
        DuckDbFinalSessionPrescriptionRepository,
        DuckDbTrainingPlanRepository,
    )
    from training_plan.persistence.paths import get_default_training_plan_db_path
    from activity_reconciliation.paths import get_default_activity_reconciliation_db_path
    from activity_reconciliation.persistence import DuckDbReconciliationResultRepository
    from plan_adaptation.paths import get_default_plan_adaptation_db_path
    from production_runtime.diagnostics_composition import create_runtime_operational_status_reader
    from production_runtime.persistence import get_default_runtime_audit_db_path
    from production_runtime.visibility import (
        DuckDbPlanAdaptationEntryReader,
        EmptyAdaptationEntryReader,
        ProductionRuntimeVisibilityReader,
    )
    from health_ingestion.http import HealthKitIngestionEndpoint
    from health_ingestion.persistence import HealthKitRepository
    from health_ingestion.service import HealthKitIngestionService

    # 1. Health DB & Morning Coach UseCase
    target_health_path = str(health_db_path) if health_db_path is not None else "data/database/health.duckdb"
    db = Database(db_path=target_health_path)
    health_repo = HealthRepository(database=db)
    morning_coach_use_case = build_morning_coach_use_case(database=db, health_repository=health_repo)

    # 2. Persisted Biomarkers context
    target_bio_path = str(biomarkers_db_path) if biomarkers_db_path is not None else "data/database/biomarkers.duckdb"
    bio_context = BiomarkersApplicationContext(db_path=target_bio_path)
    bio_builder = BiomarkersDashboardBuilder(
        repository=bio_context.repository,
        biomarker_registry=bio_context.registry,
        clock=bio_context.clock,
    )

    # 3. Production Morning Briefing Provider
    mb_provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=morning_coach_use_case,
        biomarkers_dashboard_builder=bio_builder,
    )

    # 4. Decision Repository
    target_path = get_default_decisions_db_path(decision_db_path)
    repo = DuckDbDecisionAuditRecordRepository(db_path=str(target_path))
    decision_provider = RepositoryDecisionAuditRecordProvider(repository=repo)
    history_provider = RepositoryDecisionHistoryProvider(repository=repo)

    # 5. Training Plan Repository
    target_tp_path = get_default_training_plan_db_path(training_plan_db_path)
    tp_repo = DuckDbTrainingPlanRepository(db_path=str(target_tp_path))
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=str(target_tp_path))
    tp_history_provider = RepositoryTrainingPlanHistoryProvider(repository=tp_repo)
    rx_history_provider = RepositoryPrescriptionHistoryProvider(repository=rx_repo)
    calendar_builder = ActivityCalendarBuilder(
        activity_provider=AthleteMemoryRepository(db),
        planned_session_provider=RepositoryCalendarPlannedSessionProvider(tp_repo),
        reconciliation_provider=DuckDbReconciliationResultRepository(
            get_default_activity_reconciliation_db_path(
                activity_reconciliation_db_path
            )
        ),
    )
    runtime_path = get_default_runtime_audit_db_path(runtime_audit_db_path)
    adaptation_path = get_default_plan_adaptation_db_path(plan_adaptation_db_path)
    runtime_visibility = (
        ProductionRuntimeVisibilityReader(
            create_runtime_operational_status_reader(runtime_path),
            tp_repo,
            DuckDbPlanAdaptationEntryReader(adaptation_path)
            if adaptation_path.is_file() else EmptyAdaptationEntryReader(),
        )
        if runtime_path.is_file() else EmptyProductionRuntimeVisibilityReader()
    )
    healthkit_endpoint = HealthKitIngestionEndpoint(
        HealthKitIngestionService(HealthKitRepository(db)),
        os.environ.get("HEALTHKIT_INGESTION_TOKEN"),
    )

    return create_dashboard_wsgi_app(
        biomarkers_context=bio_context,
        morning_briefing_provider=mb_provider,
        decision_audit_provider=decision_provider,
        decision_history_provider=history_provider,
        training_plan_history_provider=tp_history_provider,
        prescription_history_provider=rx_history_provider,
        activity_calendar_builder=calendar_builder,
        production_runtime_visibility_reader=runtime_visibility,
        healthkit_ingestion_endpoint=healthkit_endpoint,
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
