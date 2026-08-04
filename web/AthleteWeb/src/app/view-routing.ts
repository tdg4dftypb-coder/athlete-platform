export type ApplicationView = "morning-briefing" | "recovery" | "training" | "progress" | "nutrition" | "icons";

export function resolveApplicationView(search: string): ApplicationView {
  const params = new URLSearchParams(search);
  const view = params.get("view");
  if (view === "recovery" || view === "training" || view === "progress" || view === "nutrition" || view === "icons") {
    return view;
  }
  return "morning-briefing";
}


export function searchForView(
  search: string,
  targetView: ApplicationView,
): string {
  const params = new URLSearchParams(search);
  if (targetView === "morning-briefing") {
    params.delete("view");
  } else {
    params.set("view", targetView);
  }
  const stringified = params.toString();
  return stringified ? `?${stringified}` : "";
}
