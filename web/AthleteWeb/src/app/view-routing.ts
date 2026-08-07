export type ApplicationView =
  | "morning-briefing"
  | "morning-briefing-detail"
  | "morning"
  | "recovery"
  | "training"
  | "progress"
  | "nutrition"
  | "body"
  | "more"
  | "icons"
  | "biomarkers"
  | "history"
  | "performance-lab"
  | "performance-lab-detail"
  | "ai-coach";



export function resolveApplicationView(search: string): ApplicationView {
  const params = new URLSearchParams(search);
  const view = params.get("view");
  if (view === "morning" || view === "morning-briefing") {
    return "morning-briefing";
  }
  if (view === "morning-briefing-detail") {
    return "morning-briefing-detail";
  }
  if (view === "performance-lab") {
    return "performance-lab";
  }
  if (view === "performance-lab-detail") {
    return "performance-lab-detail";
  }
  if (view === "ai-coach" || view === "decision-intelligence") {
    return "ai-coach";
  }

  if (
    view === "recovery" ||
    view === "training" ||
    view === "progress" ||
    view === "nutrition" ||
    view === "body" ||
    view === "more" ||
    view === "icons" ||
    view === "biomarkers" ||
    view === "history"
  ) {
    return view;
  }
  return "morning-briefing";
}

/** Extracts the `id` query param for performance-lab-detail view, e.g. `?view=performance-lab-detail&id=lac-001` */
export function resolvePerformanceTestId(search: string): string {
  return new URLSearchParams(search).get("id") ?? "";
}


/** Extracts the `code` query param for the history view, e.g. `?view=history&code=ferritin` */
export function resolveHistoryCode(search: string): string {
  return new URLSearchParams(search).get("code") ?? "";
}

export function searchForView(
  search: string,
  targetView: ApplicationView,
): string {
  const params = new URLSearchParams(search);
  if (targetView === "morning-briefing" || targetView === "morning") {
    params.delete("view");
  } else {
    params.set("view", targetView);
  }
  const stringified = params.toString();
  return stringified ? `?${stringified}` : "";
}

/** Builds a history URL: ?view=history&code={canonicalCode} */
export function searchForHistory(search: string, canonicalCode: string): string {
  const params = new URLSearchParams(search);
  params.set("view", "history");
  params.set("code", canonicalCode);
  return `?${params.toString()}`;
}

