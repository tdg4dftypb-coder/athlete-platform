export function createTextList(items: readonly string[], variant: "check" | "change" | "plan"): HTMLUListElement {
  const list = document.createElement("ul");
  list.className = `text-list text-list--${variant}`;

  for (const item of items) {
    const listItem = document.createElement("li");
    const marker = document.createElement("span");
    marker.className = "list-marker";
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = variant === "check" ? "✓" : variant === "change" ? "↑" : "•";

    const label = document.createElement("span");
    label.textContent = item;
    listItem.append(marker, label);
    list.append(listItem);
  }

  return list;
}
