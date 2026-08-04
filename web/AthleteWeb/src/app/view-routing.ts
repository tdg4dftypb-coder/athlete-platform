export type ApplicationView = "morning-briefing" | "recovery";

export function resolveApplicationView(search: string): ApplicationView {
  return new URLSearchParams(search).get("view") === "recovery"
    ? "recovery"
    : "morning-briefing";
}

export function searchForView(
  search: string,
  view: ApplicationView,
): string {
  const params = new URLSearchParams(search);
  if (view === "recovery") params.set("view", "recovery");
  else params.delete("view");
  const value = params.toString();
  return value ? `?${value}` : "";
}
