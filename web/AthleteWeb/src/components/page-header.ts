import type { RecoveryPresentationHeader } from "../models/recovery-presentation";
import { createIcon } from "./icon";

export function createPageHeader(
  model: RecoveryPresentationHeader,
  onBack: () => void,
): HTMLElement {
  const header = document.createElement("header");
  header.className = "page-header reveal";

  const back = document.createElement("button");
  back.type = "button";
  back.className = "back-button";
  back.setAttribute("aria-label", "Wróć do Dzisiaj");
  back.append(createIcon("arrow-left"));
  back.addEventListener("click", onBack);

  const copy = document.createElement("div");
  copy.className = "page-header__copy";
  const title = document.createElement("h1");
  title.tabIndex = -1;
  title.textContent = model.title;
  const date = document.createElement("p");
  date.className = "date-line";
  date.textContent = model.dateText;
  const updated = document.createElement("p");
  updated.className = "page-header__updated";
  updated.textContent = model.lastUpdatedText;
  copy.append(title, date, updated);

  header.append(back, copy);
  if (model.freshnessLabel) {
    const freshness = document.createElement("span");
    freshness.className = "freshness-badge";
    freshness.textContent = model.freshnessLabel;
    header.append(freshness);
  }
  return header;
}
