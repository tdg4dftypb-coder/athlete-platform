export type ActivityIconName =
  | "activity-cycling"
  | "activity-indoor-cycling"
  | "activity-swimming"
  | "activity-crossfit"
  | "activity-gravel";

export type IconName =
  | "arrow-left"
  | "apple"
  | "chart"
  | "check"
  | "chevron"
  | "coach"
  | "gauge"
  | "heart"
  | "history"
  | "lock"
  | "moon"
  | "more"
  | "nutrition"
  | "play"
  | "runner"
  | "sun"
  | "target"
  | "trend-down"
  | "trend-up"
  | ActivityIconName;

const paths: Readonly<Record<IconName, readonly string[]>> = {
  "arrow-left": ["m15 18-6-6 6-6", "M9 12h10"],
  apple: ["M12 7c-2-3-7-2-7 4 0 5 3 9 7 9s7-4 7-9c0-6-5-7-7-4", "M12 7c0-3 2-5 5-5"],
  chart: ["M5 20V10", "M12 20V4", "M19 20v-7"],
  check: ["m5 12 4 4L19 6"],
  chevron: ["m9 5 7 7-7 7"],
  coach: ["M4 13a8 8 0 1 1 3 6l-4 1 1-4a8 8 0 0 1 0-3", "M9 11h.01", "M15 11h.01", "M9 15c2 1 4 1 6 0"],
  gauge: ["M4 16a8 8 0 1 1 16 0", "m12 14 4-5", "M8 16h.01", "M16 16h.01"],
  heart: ["M20.8 5.7a5.4 5.4 0 0 0-7.7 0L12 6.8l-1.1-1.1a5.4 5.4 0 0 0-7.7 7.7L12 22l8.8-8.6a5.4 5.4 0 0 0 0-7.7Z", "M5 13h4l1.5-3 3 6 1.5-3h4"],
  history: ["M4 12a8 8 0 1 0 3-6", "M4 4v5h5", "M12 8v5l3 2"],
  lock: ["M7 11V8a5 5 0 0 1 10 0v3", "M6 11h12v10H6z", "M12 15v2"],
  moon: ["M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"],
  more: ["M5 12h.01", "M12 12h.01", "M19 12h.01"],
  nutrition: ["M5 12h14", "M7 12a5 5 0 0 0 10 0", "M9 4c0 2 2 2 2 4", "M14 3c0 2-2 2-2 5"],
  play: ["m9 6 9 6-9 6Z"],
  runner: ["M13 5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z", "m10 22 2-6-4-3 2-5 4 3 3 1", "m12 16 4 3-2 5", "m8 13-4 3"],
  sun: ["M4 18h16", "M7 14a5 5 0 0 1 10 0", "M12 3v3", "M5 7l2 2", "m19 7-2 2"],
  target: ["M12 21a9 9 0 1 0-9-9 9 9 0 0 0 9 9Z", "M12 17a5 5 0 1 0-5-5 5 5 0 0 0 5 5Z", "m12 12 8-8", "M16 4h4v4"],
  "trend-down": ["m5 8 5 5 4-4 5 5", "M19 9v5h-5"],
  "trend-up": ["m5 16 5-5 4 4 5-5", "M14 10h5v5"],
  "activity-cycling": [
    "M5 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
    "M19 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
    "M5 16h5l-2-6h-4l3 6Z",
    "M10 16l6-6h-8",
    "M16 10l3 6",
    "M7 10h2.5",
    "M16 10h1.5v1",
    "M14 6a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
    "M9 10l4-4",
    "M13 6l3 4",
    "M9 10l1.5 3-1 3"
  ],
  "activity-indoor-cycling": [
    "M3 21h5",
    "M16 21h4",
    "M6 18a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    "M6 16.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
    "M11 17l-5-2",
    "M11 17l-2-6",
    "M9 11h7",
    "M16 11l-5 6",
    "M16 11l2 10",
    "M7.5 11h3",
    "M16 11l-1-2h3v2h-1"
  ],
  "activity-swimming": [
    "M3 18c1.5-1 2.5 1 4 0s2.5-1 4 0 2.5 1 4 0 2.5-1 4 0",
    "M3 21c1.5-1 2.5 1 4 0s2.5-1 4 0 2.5 1 4 0 2.5-1 4 0",
    "M17 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
    "M16 13.5l-4.5 3",
    "M6 16l4-5 4 3"
  ],
  "activity-crossfit": [
    "M4 9h16",
    "M7 7v4",
    "M6 7.5v3",
    "M5 8v2",
    "M17 7v4",
    "M18 7.5v3",
    "M19 8v2",
    "M12 12.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
    "M12 12.5v5.5",
    "M12 18l-3 4",
    "M12 18l3 4",
    "M8 9l2 3.5 2-0.5",
    "M16 9l-2 3.5-2-0.5"
  ],
  "activity-gravel": [
    "M3 21l3-1 3 1 3-1 3 1 3-1 3 1",
    "M5 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
    "M19 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
    "M5 16h5l-2-6h-4l3 6Z",
    "M10 16l6-6h-8",
    "M16 10l3 6",
    "M7 10h2.5",
    "M16 10h1.5v1",
    "M14 6a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
    "M9 10l4-4",
    "M13 6l3 4",
    "M9 10l1.5 3-1 3"
  ],
};

export function createIcon(name: IconName, label?: string): SVGSVGElement {
  const namespace = "http://www.w3.org/2000/svg";
  const icon = document.createElementNS(namespace, "svg");
  icon.classList.add("icon");
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("fill", "none");
  icon.setAttribute("stroke", "currentColor");
  icon.setAttribute("stroke-width", "1.6");
  icon.setAttribute("stroke-linecap", "round");
  icon.setAttribute("stroke-linejoin", "round");
  if (label) {
    icon.setAttribute("role", "img");
    icon.setAttribute("aria-label", label);
  } else {
    icon.setAttribute("aria-hidden", "true");
  }

  const pathDataList = paths[name] ?? paths["activity-cycling"];
  for (const data of pathDataList) {
    const path = document.createElementNS(namespace, "path");
    path.setAttribute("d", data);
    icon.append(path);
  }
  return icon;
}



export function mapActivityToIcon(activityType?: string | null): IconName {
  if (!activityType) return "activity-cycling";
  const normalized = activityType.toLowerCase().trim();

  if (
    normalized.includes("indoor") ||
    normalized.includes("trainer") ||
    normalized.includes("zwift") ||
    normalized.includes("trenażer")
  ) {
    return "activity-indoor-cycling";
  }
  if (
    normalized.includes("gravel") ||
    normalized.includes("mountain") ||
    normalized.includes("mtb") ||
    normalized.includes("górsk")
  ) {
    return "activity-gravel";
  }
  if (
    normalized.includes("swim") ||
    normalized.includes("pływa")
  ) {
    return "activity-swimming";
  }
  if (
    normalized.includes("crossfit") ||
    normalized.includes("functional") ||
    normalized.includes("strength") ||
    normalized.includes("sztang") ||
    normalized.includes("siłow")
  ) {
    return "activity-crossfit";
  }
  if (
    normalized.includes("cycling") ||
    normalized.includes("bike") ||
    normalized.includes("road") ||
    normalized.includes("kolarsk") ||
    normalized.includes("rower") ||
    normalized.includes("endurance") ||
    normalized.includes("tempo") ||
    normalized.includes("próg") ||
    normalized.includes("threshold") ||
    normalized.includes("vo2")
  ) {
    return "activity-cycling";
  }
  if (
    normalized.includes("run") ||
    normalized.includes("bieg")
  ) {
    return "runner";
  }
  return "activity-cycling";
}
