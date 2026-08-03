import { createCard } from "./card";

interface StatusNoticeOptions {
  readonly variant: "partial" | "unavailable" | "stale" | "failure";
  readonly title: string;
  readonly message: string;
  readonly details?: readonly string[];
  readonly detailLabel?: string;
  readonly nextAction?: string;
  readonly retryLabel?: string;
  readonly onRetry?: () => void;
}

export function createStatusNotice(options: StatusNoticeOptions): HTMLElement {
  const section = document.createElement("section");
  section.className = `state-notice state-notice--${options.variant} reveal`;
  section.setAttribute("aria-labelledby", `${options.variant}-state-title`);
  section.setAttribute("role", options.variant === "failure" ? "alert" : "status");
  section.setAttribute("aria-live", options.variant === "failure" ? "assertive" : "polite");

  const card = createCard("state-card");
  const title = document.createElement("h2");
  title.id = `${options.variant}-state-title`;
  title.textContent = options.title;

  const message = document.createElement("p");
  message.className = "state-message";
  message.textContent = options.message;
  card.append(title, message);

  if (options.details?.length) {
    if (options.detailLabel) {
      const label = document.createElement("p");
      label.className = "state-detail-label";
      label.textContent = options.detailLabel;
      card.append(label);
    }

    const list = document.createElement("ul");
    list.className = "state-detail-list";
    for (const detail of options.details) {
      const item = document.createElement("li");
      item.textContent = detail;
      list.append(item);
    }
    card.append(list);
  }

  if (options.nextAction) {
    const nextAction = document.createElement("p");
    nextAction.className = "state-next-action";
    nextAction.textContent = options.nextAction;
    card.append(nextAction);
  }

  if (options.retryLabel && options.onRetry) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "primary-action";
    retry.textContent = options.retryLabel;
    retry.addEventListener("click", options.onRetry);
    card.append(retry);
  }

  section.append(card);
  return section;
}
