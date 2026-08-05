export type ApplicationView =
  | "morning-briefing"
  | "morning"
  | "recovery"
  | "training"
  | "progress"
  | "nutrition"
  | "body"
  | "more"
  | "icons"
  | "biomarkers"
  | "history";

export function resolveApplicationView(search: string): ApplicationView {
  const params = new URLSearchParams(search);
  const view = params.get("view");
  if (view === "morning" || view === "morning-briefing") {
    return "morning-briefing";
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

