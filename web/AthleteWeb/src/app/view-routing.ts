export type ApplicationView = "morning-briefing" | "recovery" | "training" | "icons";

export function resolveApplicationView(search: string): ApplicationView {
  const requested = new URLSearchParams(search).get("view");
  if (requested === "recovery") return "recovery";
  if (requested === "training") return "training";
  if (requested === "icons" || requested === "activity-icons") return "icons";
  return "morning-briefing";
}

export function searchForView(
  search: string,
  view: ApplicationView,
): string {
  const params = new URLSearchParams(search);
  if (view === "recovery") params.set("view", "recovery");
  else if (view === "training") params.set("view", "training");
  else if (view === "icons") params.set("view", "icons");
  else params.delete("view");
  const value = params.toString();
  return value ? `?${value}` : "";
}
