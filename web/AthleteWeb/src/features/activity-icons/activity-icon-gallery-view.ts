import { createIcon, type ActivityIconName } from "../../components/icon";
import { createBottomNavigation } from "../../components/bottom-navigation";

export interface ActivityIconGalleryItem {
  readonly id: ActivityIconName;
  readonly name: string;
  readonly description: string;
}

export const activityIconGalleryItems: readonly ActivityIconGalleryItem[] = [
  {
    id: "activity-cycling",
    name: "Cycling / Outdoor",
    description: "Kolarstwo szosowe — sylwetka kolarza na rowerze szosowym",
  },
  {
    id: "activity-indoor-cycling",
    name: "Indoor Trainer",
    description: "Trenażer stacjonarny — rama trenażera w stylu Zwift Frame bez postaci",
  },
  {
    id: "activity-swimming",
    name: "Swimming",
    description: "Pływanie — głowa, ruch ręki w chwycie wody i linie fal",
  },
  {
    id: "activity-crossfit",
    name: "CrossFit",
    description: "CrossFit — sylwetka unosząca sztangę z obciążeniem nad głowę",
  },
  {
    id: "activity-gravel",
    name: "Gravel / MTB",
    description: "Gravel / MTB — rowerzysta terenowy z bieżnikiem i pochyloną sylwetką",
  },
];

export function renderActivityIconGallery(onBack?: () => void): HTMLElement {
  const container = document.createElement("div");
  container.className = "app-shell icon-gallery-shell";

  const header = document.createElement("header");
  header.className = "briefing-header reveal";

  const copy = document.createElement("div");
  copy.className = "header-copy";
  const title = document.createElement("h1");
  title.textContent = "Zestaw ikon aktywności";
  const subtitle = document.createElement("p");
  subtitle.className = "date-line";
  subtitle.textContent = "Activity Icon System • Podgląd deweloperski (20px, 24px, 32px, 40px)";
  copy.append(title, subtitle);

  if (onBack) {
    const backBtn = document.createElement("button");
    backBtn.type = "button";
    backBtn.className = "listen-button";
    backBtn.style.marginTop = "8px";
    backBtn.textContent = "← Powrót do Odprawy";
    backBtn.addEventListener("click", onBack);
    copy.append(backBtn);
  }

  header.append(copy);

  const main = document.createElement("main");
  main.className = "briefing icon-gallery-main";

  const sizes = [20, 24, 32, 40] as const;

  for (const item of activityIconGalleryItems) {
    const card = document.createElement("article");
    card.className = "hero-card icon-gallery-card reveal";

    const titleEl = document.createElement("h2");
    titleEl.textContent = item.name;

    const codeEl = document.createElement("code");
    codeEl.className = "icon-technical-name";
    codeEl.textContent = item.id;

    const descEl = document.createElement("p");
    descEl.textContent = item.description;

    const sizeRow = document.createElement("div");
    sizeRow.className = "icon-size-row";

    for (const size of sizes) {
      const wrapper = document.createElement("div");
      wrapper.className = "icon-size-sample";

      const badge = document.createElement("span");
      badge.className = "icon-badge icon-badge--training";
      badge.style.width = `${size + 16}px`;
      badge.style.height = `${size + 16}px`;

      const svg = createIcon(item.id, item.name);
      svg.style.width = `${size}px`;
      svg.style.height = `${size}px`;
      badge.append(svg);

      const sizeTag = document.createElement("span");
      sizeTag.className = "size-tag";
      sizeTag.textContent = `${size}px`;

      wrapper.append(badge, sizeTag);
      sizeRow.append(wrapper);
    }

    card.append(titleEl, codeEl, descEl, sizeRow);
    main.append(card);
  }

  container.append(
    header,
    main,
    createBottomNavigation({ currentView: "icons" }),
  );
  return container;
}
