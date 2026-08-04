export type ApplicationView =
  | "morning-briefing"
  | "morning"
  | "recovery"
  | "training"
  | "progress"
  | "nutrition"
  | "body"
  | "more"
  | "icons";

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
    view === "icons"
  ) {
    return view;
  }
  return "morning-briefing";
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
