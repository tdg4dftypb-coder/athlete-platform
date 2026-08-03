import "./styles/reset.css";
import "./theme/tokens.css";
import "./styles/main.css";

import { createApp } from "./app/create-app";
import { morningBriefingPreviewData } from "./preview-data/morning-briefing-preview-data";

const root = document.querySelector<HTMLDivElement>("#app");

if (!root) {
  throw new Error("Missing application root");
}

root.append(createApp(morningBriefingPreviewData));
