"""Canonical same-logical-plan horizon continuity contracts."""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
import json

from training_plan.intent import Weekday
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan


@dataclass(frozen=True)
class ContinuationSessionSlot:
    slot_id: str
    kind: PlannedSessionKind
    session_type: str | None
    duration_minutes: int
    target_tss: float | None
    intensity: str | None
    priority: int
    rationale: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.slot_id, str) or not self.slot_id.strip(): raise ValueError("slot_id must be non-empty")
        probe=PlannedSession("probe",date(2000,1,1),self.kind,self.session_type,self.duration_minutes,
                             self.target_tss,self.intensity,self.priority,self.rationale)
        object.__setattr__(self,"session_type",probe.session_type); object.__setattr__(self,"intensity",probe.intensity)


@dataclass(frozen=True)
class ContinuationWeekday:
    weekday: Weekday
    slots: tuple[ContinuationSessionSlot, ...]
    def __post_init__(self):
        if not isinstance(self.weekday,Weekday): raise TypeError("weekday must be Weekday")
        if not self.slots or any(not isinstance(x,ContinuationSessionSlot) for x in self.slots): raise ValueError("slots must be non-empty")
        if len({x.slot_id for x in self.slots}) != len(self.slots): raise ValueError("duplicate slot_id")
        rests=sum(x.kind is PlannedSessionKind.REST for x in self.slots)
        if rests and len(self.slots)!=1: raise ValueError("weekday cannot mix REST and TRAINING")
        object.__setattr__(self,"slots",tuple(sorted(self.slots,key=lambda x:x.slot_id)))


@dataclass(frozen=True)
class TrainingPlanContinuationSpecification:
    specification_id: str
    version: int
    plan_id: str
    target_horizon_days: int
    extension_days: int
    weekdays: tuple[ContinuationWeekday, ...]
    semantic_fingerprint: str
    created_at: datetime

    def __post_init__(self):
        for value,name in ((self.specification_id,"specification_id"),(self.plan_id,"plan_id")):
            if not isinstance(value,str) or not value.strip(): raise ValueError(f"{name} must be non-empty")
        if not isinstance(self.version,int) or self.version<1: raise ValueError("version must be >= 1")
        if not isinstance(self.target_horizon_days,int) or self.target_horizon_days<7: raise ValueError("target_horizon_days must be >= 7")
        if not isinstance(self.extension_days,int) or self.extension_days<1: raise ValueError("extension_days must be >= 1")
        if not isinstance(self.created_at,datetime) or self.created_at.tzinfo is None or self.created_at.utcoffset()!=timezone.utc.utcoffset(self.created_at):
            raise ValueError("created_at must be timezone-aware UTC")
        if len(self.weekdays)!=7 or {x.weekday for x in self.weekdays}!={x for x in Weekday}: raise ValueError("weekdays must cover all seven days")
        object.__setattr__(self,"weekdays",tuple(sorted(self.weekdays,key=lambda x:x.weekday.value)))
        if self.semantic_fingerprint != self.fingerprint_for(self.specification_id,self.version,self.plan_id,self.target_horizon_days,self.extension_days,self.weekdays):
            raise ValueError("semantic_fingerprint mismatch")

    @staticmethod
    def fingerprint_for(specification_id,version,plan_id,target_horizon_days,extension_days,weekdays):
        payload={"specification_id":specification_id,"version":version,"plan_id":plan_id,"target_horizon_days":target_horizon_days,"extension_days":extension_days,
                 "weekdays":[{"weekday":x.weekday.name,"slots":[{"slot_id":s.slot_id,"kind":s.kind.value,
                 "session_type":s.session_type,"duration_minutes":s.duration_minutes,"target_tss":s.target_tss,
                 "intensity":s.intensity,"priority":s.priority,"rationale":s.rationale} for s in x.slots]} for x in weekdays]}
        return "sha256:"+sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()

    @classmethod
    def create(cls, specification_id, version, plan_id, target_horizon_days, extension_days, weekdays, created_at):
        canonical=tuple(sorted(weekdays,key=lambda x:x.weekday.value))
        return cls(specification_id,version,plan_id,target_horizon_days,extension_days,canonical,
                   cls.fingerprint_for(specification_id,version,plan_id,target_horizon_days,extension_days,canonical),created_at)


class HorizonExtensionStatus(str,Enum):
    NO_EXTENSION="NO_EXTENSION"
    EXTENDED="EXTENDED"


@dataclass(frozen=True)
class HorizonExtensionResult:
    status: HorizonExtensionStatus
    plan: TrainingPlan


class TrainingPlanHorizonExtensionService:
    def extend(self, source, specification, required_coverage_date, *, generated_at):
        if source.plan_id != specification.plan_id: raise ValueError("specification targets different plan")
        if source.end_date >= required_coverage_date: return HorizonExtensionResult(HorizonExtensionStatus.NO_EXTENSION,source)
        chunks=((required_coverage_date-source.end_date).days+specification.extension_days-1)//specification.extension_days
        new_end=source.end_date+timedelta(days=chunks*specification.extension_days)
        by_weekday={x.weekday.value:x for x in specification.weekdays}; generated=[]; day=source.end_date+timedelta(days=1)
        while day<=new_end:
            for slot in by_weekday[day.weekday()].slots:
                generated.append(PlannedSession(
                    f"{source.plan_id}:{specification.version}:{day.isoformat()}:{slot.slot_id}",day,slot.kind,
                    slot.session_type,slot.duration_minutes,slot.target_tss,slot.intensity,slot.priority,slot.rationale))
            day+=timedelta(days=1)
        plan=TrainingPlan(source.plan_id,source.start_date,new_end,source.version+1,generated_at,
                          source.sessions+tuple(generated),source.supersedes_plan_id)
        return HorizonExtensionResult(HorizonExtensionStatus.EXTENDED,plan)
