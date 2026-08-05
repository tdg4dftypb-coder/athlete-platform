import type { MappingContext } from "../mappers/mapping-context";
import { formatContractDateTime, parseContractTimestamp } from "../mappers/contract-temporal";
import type { BiomarkersDashboardPayloadV1 } from "./biomarkers-payload-v1";
import { parseBiomarkersDashboardPayloadV1 } from "./biomarkers-payload-parser";
import type {
  BiomarkerCategoryPresentationGroup,
  BiomarkerPresentationItem,
  BiomarkersPresentation,
  UnresolvedBiomarkerPresentationItem,
} from "./biomarkers-presentation";
import type { BiomarkersPresentationState } from "./biomarkers-presentation-state";

export type PayloadMappedBiomarkersState = Exclude<BiomarkersPresentationState, { kind: "loading" }>;

export function parseAndMapBiomarkersPayloadToPresentation(
  input: unknown,
  context: MappingContext,
): PayloadMappedBiomarkersState {
  const parsed = parseBiomarkersDashboardPayloadV1(input);
  if (!parsed.success) {
    const issueMsg = parsed.issues[0]?.message ?? "Błąd kontraktu payloadu.";
    return {
      kind: "failure",
      title: "Błąd walidacji danych biomarkerów",
      message: "Otrzymany payload biomarkerów jest niezgodny z wersją v1.0.",
      supportingText: `Błąd kontraktu: ${issueMsg}`,
      retryLabel: "Spróbuj ponownie",
    };
  }
  return mapBiomarkersPayloadToPresentation(parsed.data, context);
}

export function mapBiomarkersPayloadToPresentation(
  payload: BiomarkersDashboardPayloadV1,
  context: MappingContext,
): PayloadMappedBiomarkersState {
  const asOf = parseContractTimestamp(payload.as_of);
  const ageMs = context.now.getTime() - asOf.getTime();

  if (!Number.isFinite(ageMs) || ageMs < 0 || context.staleAfterMs < 0) {
    return {
      kind: "failure",
      title: "Błąd czasu synchronizacji",
      message: "Payload biomarkerów zawiera niespójne znaczniki czasu.",
      supportingText: "Znacznik as_of znajduje się w przyszłości lub zawiera błędną strefę czasową.",
      retryLabel: "Spróbuj ponownie",
    };
  }

  // Unavailable check
  if (payload.metadata.status === "unavailable" || payload.summary.total_reports === 0) {
    return {
      kind: "unavailable",
      title: "Badania laboratoryjne",
      message: "Brak aktywnych badań laboratoryjnych w profilu.",
      reason: payload.metadata.limitations[0] ?? "Nie zaimportowano jeszcze żadnych wyników badań laboratoryjnych.",
      nextAction: "Dodaj pierwsze wyniki badań, aby przejrzeć panel biomarkerów.",
    };
  }

  const presentation = createBiomarkersPresentation(payload, context);

  // Stale check
  const isStale = ageMs > context.staleAfterMs;
  if (isStale) {
    return {
      kind: "stale",
      presentation,
      message: "Dane laboratoryjne mogą być nieaktualne.",
      lastUpdatedText: `Ostatnia aktualizacja: ${formatContractDateTime(asOf, context)}.`,
    };
  }

  // Partial check
  if (payload.metadata.status === "partial" || payload.unresolved_items.length > 0 || payload.summary.possible_duplicates > 0) {
    return {
      kind: "partial",
      presentation,
      message: "Panel biomarkerów jest dostępny, ale występują ograniczenia jakościowe danych.",
      limitations: payload.metadata.limitations,
    };
  }

  return {
    kind: "ready",
    presentation,
  };
}

function createBiomarkersPresentation(
  payload: BiomarkersDashboardPayloadV1,
  context: MappingContext,
): BiomarkersPresentation {
  const categories: BiomarkerCategoryPresentationGroup[] = payload.categories.map((catPayload) => {
    const items: BiomarkerPresentationItem[] = catPayload.biomarkers.map((bPayload) => {
      const valStr = bPayload.latest_value !== null ? formatNumber(bPayload.latest_value, context) : (bPayload.latest_text_value ?? "Brak");
      const valueLabel = bPayload.inequality_operator ? `${bPayload.inequality_operator} ${valStr}` : valStr;
      const unitLabel = bPayload.normalized_unit ?? bPayload.raw_unit ?? "";
      const refLabel = bPayload.laboratory_reference_text ? `Norma lab: ${bPayload.laboratory_reference_text}` : "Brak zakresu referencyjnego";

      const collDate = parseContractTimestamp(bPayload.collected_at);
      const collLabel = formatContractDateTime(collDate, context);

      const trendDirection = bPayload.trend_direction ?? "unavailable";
      const trendLabel = mapTrendLabel(trendDirection);

      const verLabel = bPayload.verification_status === "verified" ? "Zweryfikowano" : "Niezweryfikowane";

      return {
        code: bPayload.canonical_code,
        name: bPayload.canonical_name,
        valueLabel,
        unitLabel,
        referenceLabel: refLabel,
        collectedAtLabel: collLabel,
        trendLabel,
        trendDirection,
        laboratoryFlag: bPayload.laboratory_flag,
        verificationLabel: verLabel,
        limitations: bPayload.limitations,
      };
    });

    return {
      categoryCode: catPayload.category,
      displayName: catPayload.display_name,
      attentionCount: catPayload.attention_count,
      unresolvedCount: catPayload.unresolved_count,
      biomarkers: items,
    };
  });

  const unresolvedItems: UnresolvedBiomarkerPresentationItem[] = payload.unresolved_items.map((u) => ({
    id: u.observation_id,
    name: u.raw_name,
    unit: u.raw_unit,
    collectedAtLabel: formatContractDateTime(parseContractTimestamp(u.collected_at), context),
    reason: u.safe_reason,
  }));

  const compPct = Math.round(payload.metadata.completeness_score * 100);

  return {
    title: "Badania laboratoryjne i biomarkery",
    statusLabel: mapStatusLabel(payload.metadata.status),
    completenessLabel: `Kompletność danych: ${compPct}%`,
    latestCollectionLabel: payload.summary.latest_collection_date ? `Ostatnie badanie: ${payload.summary.latest_collection_date}` : "Brak daty pobrania",
    attentionCount: categories.reduce((sum, c) => sum + c.attentionCount, 0),
    unresolvedCount: payload.unresolved_items.length,
    limitations: payload.metadata.limitations,
    summary: {
      totalReports: payload.summary.total_reports,
      activeReports: payload.summary.active_reports,
      totalObservations: payload.summary.total_observations,
      verifiedObservations: payload.summary.verified_observations,
      unresolvedObservations: payload.summary.unresolved_observations,
      possibleDuplicates: payload.summary.possible_duplicates,
      latestCollectionDate: payload.summary.latest_collection_date,
    },
    categories,
    unresolvedItems,
  };
}

function mapStatusLabel(status: "ready" | "partial" | "unavailable"): string {
  switch (status) {
    case "ready":
      return "Wszystkie biomarkery zweryfikowane";
    case "partial":
      return "Częściowe dane laboratoryjne";
    case "unavailable":
      return "Brak aktywnych wyników";
  }
}

function mapTrendLabel(trend: string): string {
  switch (trend) {
    case "increasing":
      return "Trend rosnący";
    case "decreasing":
      return "Trend malejący";
    case "stable":
      return "Wartość stabilna";
    default:
      return "Brak wystarczającego trendu";
  }
}

function formatNumber(val: number, context: MappingContext): string {
  return new Intl.NumberFormat(context.locale ?? "pl-PL", { maximumFractionDigits: 2 }).format(val);
}
