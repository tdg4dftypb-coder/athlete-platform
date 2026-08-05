import { createBottomNavigation } from "../components/bottom-navigation";
import { createPageHeader } from "../components/page-header";
import { createIcon } from "../components/icon";
import { searchForHistory } from "../app/view-routing";
import type { BiomarkersPresentationState } from "./biomarkers-presentation-state";

export function createBiomarkersExperienceApp(
  state: BiomarkersPresentationState,
  onBackToBriefing: () => void,
  onRetry?: () => void,
): HTMLElement {
  const shell = document.createElement("div");
  shell.className = "app-shell biomarkers-shell";

  const main = document.createElement("main");
  main.className = "briefing biomarkers-view";

  const pageHeader = createPageHeader(
    {
      title: "Wyniki badań",
      dateText: getHeaderDateText(state),
      lastUpdatedText: getHeaderLastUpdatedText(state),
      freshnessLabel: state.kind === "stale" ? "Nieodświeżone" : null,
    },
    onBackToBriefing,
  );
  main.appendChild(pageHeader);

  // Content rendering based on Presentation State
  switch (state.kind) {
    case "loading": {
      const loadingSection = document.createElement("section");
      loadingSection.className = "card card-loading biomarkers-skeleton";
      loadingSection.setAttribute("aria-busy", "true");
      loadingSection.setAttribute("aria-live", "polite");

      loadingSection.innerHTML = `
        <div class="skeleton-pill" style="height: 1.5rem; width: 60%; margin-bottom: 1rem; background: var(--color-surface-muted); border-radius: 4px;"></div>
        <div class="skeleton-pill" style="height: 4rem; width: 100%; margin-bottom: 1rem; background: var(--color-surface-muted); border-radius: 8px;"></div>
        <div class="skeleton-pill" style="height: 8rem; width: 100%; background: var(--color-surface-muted); border-radius: 8px;"></div>
      `;
      main.appendChild(loadingSection);
      break;
    }
    case "failure": {
      const failSection = document.createElement("section");
      failSection.className = "card card-failure";
      failSection.setAttribute("aria-live", "assertive");

      const h2 = document.createElement("h2");
      h2.textContent = state.title;
      failSection.appendChild(h2);

      const pMsg = document.createElement("p");
      pMsg.textContent = state.message;
      failSection.appendChild(pMsg);

      const pSupp = document.createElement("p");
      pSupp.className = "supporting-text";
      pSupp.style.cssText = "color: var(--color-text-secondary); font-size: 0.85rem; margin-top: 0.5rem;";
      pSupp.textContent = state.supportingText;
      failSection.appendChild(pSupp);

      if (onRetry) {
        const retryBtn = document.createElement("button");
        retryBtn.className = "btn-retry";
        retryBtn.type = "button";
        retryBtn.style.cssText = "margin-top: 1rem; padding: 0.6rem 1.2rem; cursor: pointer;";
        retryBtn.textContent = state.retryLabel;
        retryBtn.addEventListener("click", onRetry);
        failSection.appendChild(retryBtn);
      }

      main.appendChild(failSection);
      break;
    }
    case "unavailable": {
      const unavSection = document.createElement("section");
      unavSection.className = "card card-unavailable";
      unavSection.style.cssText = "text-align: center; padding: 2rem 1.2rem;";

      const h2 = document.createElement("h2");
      h2.style.cssText = "font-size: 1.1rem; margin-bottom: 0.5rem;";
      h2.textContent = state.title;
      unavSection.appendChild(h2);

      const pMsg = document.createElement("p");
      pMsg.style.cssText = "font-weight: 600; margin-bottom: 0.5rem; color: var(--color-text-primary);";
      pMsg.textContent = state.message;
      unavSection.appendChild(pMsg);

      const pReason = document.createElement("p");
      pReason.style.cssText = "color: var(--color-text-secondary); font-size: 0.88rem; margin-bottom: 1.5rem;";
      pReason.textContent = state.reason;
      unavSection.appendChild(pReason);

      // Non-functional visual action placeholder
      const placeholderBtn = document.createElement("button");
      placeholderBtn.type = "button";
      placeholderBtn.className = "btn-action-placeholder";
      placeholderBtn.style.cssText = "padding: 0.7rem 1.5rem; border-radius: 8px; background: var(--color-surface-muted); color: var(--color-text-primary); border: 1px solid var(--color-border); font-weight: 600; cursor: not-allowed; opacity: 0.8;";
      placeholderBtn.textContent = state.nextAction;
      placeholderBtn.setAttribute("aria-disabled", "true");
      unavSection.appendChild(placeholderBtn);

      main.appendChild(unavSection);
      break;
    }
    case "ready":
    case "partial":
    case "stale": {
      const pres = state.presentation;

      // Hero Summary Card
      const heroCard = document.createElement("section");
      heroCard.className = "card card-hero";
      heroCard.setAttribute("aria-live", "polite");

      const heroHeader = document.createElement("div");
      heroHeader.className = "hero-header-row";

      const heroTitle = document.createElement("h2");
      heroTitle.style.cssText = "font-size: 1.05rem; font-weight: 700; margin: 0 0 0.4rem 0;";
      heroTitle.textContent = pres.title;

      const heroMsg = document.createElement("p");
      heroMsg.style.cssText = "font-size: 0.92rem; color: var(--color-text-primary); margin: 0 0 0.8rem 0; line-height: 1.4;";
      heroMsg.textContent = state.kind === "stale" ? state.message : pres.statusLabel;

      heroHeader.append(heroTitle, heroMsg);
      heroCard.appendChild(heroHeader);

      // Hero Pills Summary
      const pillGrid = document.createElement("div");
      pillGrid.style.cssText = "display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.6rem; margin-bottom: 0.8rem;";

      pillGrid.innerHTML = `
        <div style="background: var(--color-surface-muted); padding: 0.6rem; border-radius: 6px;">
          <small style="color: var(--color-text-secondary); display: block;">Raporty</small>
          <strong>${pres.summary.totalReports}</strong>
        </div>
        <div style="background: var(--color-surface-muted); padding: 0.6rem; border-radius: 6px;">
          <small style="color: var(--color-text-secondary); display: block;">Biomarkery</small>
          <strong>${pres.summary.totalObservations}</strong>
        </div>
        <div style="background: var(--color-surface-muted); padding: 0.6rem; border-radius: 6px;">
          <small style="color: var(--color-text-secondary); display: block;">Do weryfikacji</small>
          <strong>${pres.unresolvedCount}</strong>
        </div>
        <div style="background: var(--color-surface-muted); padding: 0.6rem; border-radius: 6px;">
          <small style="color: var(--color-text-secondary); display: block;">Ostatnie badanie</small>
          <strong style="font-size: 0.85rem;">${pres.summary.latestCollectionDate ?? "Brak"}</strong>
        </div>
      `;
      heroCard.appendChild(pillGrid);

      const compText = document.createElement("div");
      compText.style.cssText = "display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.4rem; font-size: 0.78rem; color: var(--color-text-secondary); border-top: 1px solid var(--color-border); padding-top: 0.6rem;";
      compText.innerHTML = `<span>${pres.completenessLabel}</span><span>${pres.latestCollectionLabel}</span>`;
      heroCard.appendChild(compText);

      main.appendChild(heroCard);

      // Partial or Stale Notice Card
      if (state.kind === "stale") {
        const staleNotice = document.createElement("section");
        staleNotice.className = "card card-notice warning-notice";
        staleNotice.style.cssText = "border-left: 4px solid var(--color-warning); padding: 0.8rem 1rem; margin-bottom: 1rem;";
        staleNotice.textContent = `${state.message} (${state.lastUpdatedText})`;
        main.appendChild(staleNotice);
      } else if (state.kind === "partial") {
        const partialNotice = document.createElement("section");
        partialNotice.className = "card card-notice warning-notice";
        partialNotice.style.cssText = "border-left: 4px solid var(--color-info); padding: 0.8rem 1rem; margin-bottom: 1rem;";
        partialNotice.textContent = state.message;
        main.appendChild(partialNotice);
      }

      // Attention & Quality Limitations
      if (pres.limitations.length > 0) {
        const limitSection = document.createElement("section");
        limitSection.className = "card card-limitations";
        
        const limTitle = document.createElement("h3");
        limTitle.style.cssText = "font-size: 0.95rem; font-weight: 700; margin-bottom: 0.5rem;";
        limTitle.textContent = "Ograniczenia jakości danych";
        limitSection.appendChild(limTitle);

        const ul = document.createElement("ul");
        ul.style.cssText = "margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: var(--color-text-secondary);";
        for (const lim of pres.limitations) {
          const li = document.createElement("li");
          li.textContent = lim;
          ul.appendChild(li);
        }
        limitSection.appendChild(ul);
        main.appendChild(limitSection);
      }

      // Categories & Biomarker Items
      for (const cat of pres.categories) {
        const catCard = document.createElement("section");
        catCard.className = "card card-category";
        catCard.style.cssText = "padding: 0; overflow: hidden; margin-bottom: 1rem;";

        const toggleBtn = document.createElement("button");
        toggleBtn.type = "button";
        toggleBtn.className = "category-toggle";
        toggleBtn.style.cssText = "display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 1rem 1.1rem; background: none; border: none; text-align: left; cursor: pointer; color: var(--color-text-primary);";
        toggleBtn.setAttribute("aria-expanded", "true");

        const catTitle = document.createElement("h3");
        catTitle.style.cssText = "font-size: 0.98rem; font-weight: 700; margin: 0;";
        catTitle.textContent = `${cat.displayName} (${cat.biomarkers.length})`;

        const chevron = createIcon("chevron");
        chevron.style.cssText = "transform: rotate(180deg); transition: transform 0.2s ease;";

        toggleBtn.append(catTitle, chevron);
        catCard.appendChild(toggleBtn);

        const listContainer = document.createElement("div");
        listContainer.className = "category-body";
        listContainer.style.cssText = "padding: 0 1.1rem 1rem 1.1rem;";

        const bList = document.createElement("ul");
        bList.style.cssText = "list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.75rem;";

        for (const b of cat.biomarkers) {
          const bLi = document.createElement("li");
          bLi.className = "biomarker-item-row";
          bLi.style.cssText = "padding: 0.75rem; border-radius: 6px; background: var(--color-surface-muted); display: flex; flex-direction: column; gap: 0.35rem;";

          const mainRow = document.createElement("div");
          mainRow.style.cssText = "display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;";

          const bName = document.createElement("span");
          bName.style.cssText = "font-weight: 680; font-size: 0.9rem; flex: 1 1 auto; overflow-wrap: anywhere;";
          bName.textContent = b.name;

          const bVal = document.createElement("span");
          bVal.style.cssText = "font-weight: 700; font-size: 0.95rem; text-align: right; margin-left: auto; flex: 0 0 auto;";
          bVal.textContent = `${b.valueLabel} ${b.unitLabel}`.trim();

          mainRow.append(bName, bVal);

          const metaRow = document.createElement("div");
          metaRow.style.cssText = "display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.78rem; color: var(--color-text-secondary); align-items: center;";

          const refSpan = document.createElement("span");
          refSpan.textContent = b.referenceLabel;
          metaRow.appendChild(refSpan);

          if (b.laboratoryFlag) {
            const flagSpan = document.createElement("span");
            flagSpan.style.cssText = "font-weight: 600; padding: 0.1rem 0.35rem; border-radius: 4px; background: var(--color-surface-elevated); border: 1px solid var(--color-border);";
            flagSpan.textContent = b.laboratoryFlag;
            metaRow.appendChild(flagSpan);
          }

          const trendBadge = document.createElement("span");
          trendBadge.style.cssText = "padding: 0.1rem 0.4rem; border-radius: 4px; background: var(--color-surface-elevated); font-weight: 500; border: 1px solid var(--color-border);";
          trendBadge.textContent = `Trend: ${b.trendLabel}`;
          metaRow.appendChild(trendBadge);

          const verSpan = document.createElement("span");
          verSpan.textContent = `• ${b.verificationLabel}`;
          metaRow.appendChild(verSpan);

          bLi.append(mainRow, metaRow);

          // Navigate to history view on click
          bLi.style.cursor = "pointer";
          bLi.setAttribute("role", "button");
          bLi.setAttribute("tabindex", "0");
          bLi.setAttribute("aria-label", `Historia: ${b.name}`);
          const openHistory = () => {
            const url = new URL(window.location.href);
            url.search = searchForHistory(url.search, b.code);
            window.history.pushState({ athleteView: "history" }, "", url);
            window.dispatchEvent(new Event("popstate"));
          };
          bLi.addEventListener("click", openHistory);
          bLi.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              openHistory();
            }
          });

          bList.appendChild(bLi);
        }

        listContainer.appendChild(bList);
        catCard.appendChild(listContainer);

        // Accordion Toggle Handler with Keyboard accessibility
        const toggleAccordion = () => {
          const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
          toggleBtn.setAttribute("aria-expanded", String(!expanded));
          listContainer.style.display = expanded ? "none" : "block";
          chevron.style.transform = expanded ? "rotate(0deg)" : "rotate(180deg)";
        };

        toggleBtn.addEventListener("click", toggleAccordion);
        toggleBtn.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleAccordion();
          }
        });

        main.appendChild(catCard);
      }

      // Unresolved Items Section ("Do weryfikacji")
      if (pres.unresolvedItems.length > 0) {
        const unresSection = document.createElement("section");
        unresSection.className = "card card-unresolved";

        const unresTitle = document.createElement("h3");
        unresTitle.style.cssText = "font-size: 0.95rem; font-weight: 700; margin-bottom: 0.6rem;";
        unresTitle.textContent = `Do weryfikacji (${pres.unresolvedItems.length})`;
        unresSection.appendChild(unresTitle);

        const uUl = document.createElement("ul");
        uUl.style.cssText = "list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem;";

        for (const u of pres.unresolvedItems) {
          const uLi = document.createElement("li");
          uLi.style.cssText = "padding: 0.65rem 0.8rem; border-radius: 6px; background: var(--color-surface-muted); font-size: 0.85rem;";
          uLi.innerHTML = `
            <div style="font-weight: 600;">${u.name} <span style="font-weight: 400; color: var(--color-text-secondary);">[${u.unit}]</span></div>
            <div style="font-size: 0.78rem; color: var(--color-text-secondary); margin-top: 0.2rem;">${u.reason} • ${u.collectedAtLabel}</div>
          `;
          uUl.appendChild(uLi);
        }
        unresSection.appendChild(uUl);
        main.appendChild(unresSection);
      }

      // Data Quality Summary Footer Card
      const summaryFooter = document.createElement("section");
      summaryFooter.className = "card card-data-quality-summary";
      summaryFooter.style.cssText = "font-size: 0.82rem; color: var(--color-text-secondary); padding: 1rem 1.1rem;";

      const sumTitle = document.createElement("h4");
      sumTitle.style.cssText = "font-size: 0.88rem; font-weight: 700; margin: 0 0 0.5rem 0; color: var(--color-text-primary);";
      sumTitle.textContent = "Podsumowanie jakości importu";
      summaryFooter.appendChild(sumTitle);

      const sumGrid = document.createElement("div");
      sumGrid.style.cssText = "display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.4rem;";
      sumGrid.innerHTML = `
        <div>Raporty aktywne: ${pres.summary.activeReports}/${pres.summary.totalReports}</div>
        <div>Obserwacje ogółem: ${pres.summary.totalObservations}</div>
        <div>Zweryfikowane: ${pres.summary.verifiedObservations}</div>
        <div>Do weryfikacji: ${pres.summary.unresolvedObservations}</div>
      `;
      summaryFooter.appendChild(sumGrid);
      main.appendChild(summaryFooter);

      break;
    }
  }

  shell.append(main, createBottomNavigation({ currentView: "biomarkers" }));
  return shell;
}

function getHeaderDateText(state: BiomarkersPresentationState): string {
  if (state.kind === "ready" || state.kind === "partial" || state.kind === "stale") {
    return state.presentation.latestCollectionLabel;
  }
  return "Panel biomarkerów";
}

function getHeaderLastUpdatedText(state: BiomarkersPresentationState): string {
  if (state.kind === "stale") return state.lastUpdatedText;
  if (state.kind === "ready" || state.kind === "partial") return state.presentation.completenessLabel;
  return "Wczytywanie danych...";
}
