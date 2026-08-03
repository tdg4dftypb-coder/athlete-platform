export function createCard(className?: string): HTMLElement {
  const card = document.createElement("div");
  card.className = ["card", className].filter(Boolean).join(" ");
  return card;
}

export function createSection(title: string, id: string): HTMLElement {
  const section = document.createElement("section");
  section.className = "briefing-section reveal";
  section.setAttribute("aria-labelledby", id);

  const heading = document.createElement("h2");
  heading.id = id;
  heading.textContent = title;
  section.append(heading);

  return section;
}
