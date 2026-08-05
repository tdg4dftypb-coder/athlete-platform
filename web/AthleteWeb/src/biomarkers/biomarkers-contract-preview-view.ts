import type { BiomarkersPresentationState } from "./biomarkers-presentation-state";

export function createBiomarkersContractPreviewApp(
  state: BiomarkersPresentationState,
  onBackToBriefing: () => void,
  onRetry?: () => void,
): HTMLElement {
  const container = document.createElement("div");
  container.className = "experience-container biomarkers-preview-container";

  // Header / Navigation
  const headerNav = document.createElement("nav");
  headerNav.className = "header-nav";

  const backButton = document.createElement("button");
  backButton.className = "btn-back";
  backButton.type = "button";
  backButton.textContent = "← Powrót do briefingu";
  backButton.addEventListener("click", onBackToBriefing);
  headerNav.appendChild(backButton);
  container.appendChild(headerNav);

  const titleHeader = document.createElement("header");
  titleHeader.className = "experience-header";

  const h1 = document.createElement("h1");
  h1.tabIndex = -1;
  h1.textContent = "Biomarkers Contract Preview";
  titleHeader.appendChild(h1);
  container.appendChild(titleHeader);

  // Render State
  switch (state.kind) {
    case "loading": {
      const loadingCard = document.createElement("section");
      loadingCard.className = "card card-loading";
      loadingCard.textContent = state.message;
      container.appendChild(loadingCard);
      break;
    }
    case "failure": {
      const failCard = document.createElement("section");
      failCard.className = "card card-failure";
      
      const failTitle = document.createElement("h2");
      failTitle.textContent = state.title;
      failCard.appendChild(failTitle);

      const failMsg = document.createElement("p");
      failMsg.textContent = state.message;
      failCard.appendChild(failMsg);

      const failSupp = document.createElement("p");
      failSupp.className = "supporting-text";
      failSupp.textContent = state.supportingText;
      failCard.appendChild(failSupp);

      if (onRetry) {
        const retryBtn = document.createElement("button");
        retryBtn.className = "btn-retry";
        retryBtn.type = "button";
        retryBtn.textContent = state.retryLabel;
        retryBtn.addEventListener("click", onRetry);
        failCard.appendChild(retryBtn);
      }
      container.appendChild(failCard);
      break;
    }
    case "unavailable": {
      const unavCard = document.createElement("section");
      unavCard.className = "card card-unavailable";

      const unavTitle = document.createElement("h2");
      unavTitle.textContent = state.title;
      unavCard.appendChild(unavTitle);

      const unavMsg = document.createElement("p");
      unavMsg.textContent = state.message;
      unavCard.appendChild(unavMsg);

      const unavReason = document.createElement("p");
      unavReason.className = "supporting-text";
      unavReason.textContent = state.reason;
      unavCard.appendChild(unavReason);

      const unavAction = document.createElement("p");
      unavAction.className = "next-action";
      unavAction.textContent = state.nextAction;
      unavCard.appendChild(unavAction);

      container.appendChild(unavCard);
      break;
    }
    case "ready":
    case "partial":
    case "stale": {
      const pres = state.presentation;

      // Status Badge Card
      const statusCard = document.createElement("section");
      statusCard.className = `card card-status card-status-${state.kind}`;

      const statusBadge = document.createElement("span");
      statusBadge.className = "badge-kind";
      statusBadge.textContent = `State: ${state.kind.toUpperCase()}`;
      statusCard.appendChild(statusBadge);

      const statusText = document.createElement("h2");
      statusText.textContent = pres.statusLabel;
      statusCard.appendChild(statusText);

      const compText = document.createElement("p");
      compText.textContent = `${pres.completenessLabel} | ${pres.latestCollectionLabel}`;
      statusCard.appendChild(compText);

      if (state.kind === "stale") {
        const staleNotice = document.createElement("p");
        staleNotice.className = "warning-text";
        staleNotice.textContent = `${state.message} (${state.lastUpdatedText})`;
        statusCard.appendChild(staleNotice);
      } else if (state.kind === "partial") {
        const partialNotice = document.createElement("p");
        partialNotice.className = "warning-text";
        partialNotice.textContent = state.message;
        statusCard.appendChild(partialNotice);
      }

      container.appendChild(statusCard);

      // Summary Stats
      const summaryCard = document.createElement("section");
      summaryCard.className = "card card-summary";
      const sumTitle = document.createElement("h3");
      sumTitle.textContent = "Podsumowanie wskaźników importu";
      summaryCard.appendChild(sumTitle);

      const sumGrid = document.createElement("div");
      sumGrid.className = "summary-grid";
      sumGrid.innerHTML = `
        <div><strong>Raporty ogółem:</strong> ${pres.summary.totalReports}</div>
        <div><strong>Aktywne raporty:</strong> ${pres.summary.activeReports}</div>
        <div><strong>Obserwacje ogółem:</strong> ${pres.summary.totalObservations}</div>
        <div><strong>Zweryfikowane:</strong> ${pres.summary.verifiedObservations}</div>
        <div><strong>Nierozpoznane:</strong> ${pres.summary.unresolvedObservations}</div>
        <div><strong>Potencjalne duplikaty:</strong> ${pres.summary.possibleDuplicates}</div>
      `;
      summaryCard.appendChild(sumGrid);
      container.appendChild(summaryCard);

      // Limitations list if present
      if (pres.limitations.length > 0) {
        const limitCard = document.createElement("section");
        limitCard.className = "card card-limitations";
        const limitTitle = document.createElement("h3");
        limitTitle.textContent = "Ograniczenia jakości danych";
        limitCard.appendChild(limitTitle);

        const limitList = document.createElement("ul");
        for (const lim of pres.limitations) {
          const li = document.createElement("li");
          li.textContent = lim;
          limitList.appendChild(li);
        }
        limitCard.appendChild(limitList);
        container.appendChild(limitCard);
      }

      // Categories and Biomarkers
      for (const cat of pres.categories) {
        const catCard = document.createElement("section");
        catCard.className = "card card-category";

        const catHeader = document.createElement("h3");
        catHeader.textContent = `${cat.displayName} (${cat.biomarkers.length})`;
        catCard.appendChild(catHeader);

        const bList = document.createElement("ul");
        bList.className = "biomarker-items-list";

        for (const b of cat.biomarkers) {
          const bLi = document.createElement("li");
          bLi.className = "biomarker-item";
          bLi.innerHTML = `
            <div><strong>${b.name}</strong> (${b.code}): <span>${b.valueLabel} ${b.unitLabel}</span></div>
            <div class="meta-row"><small>${b.referenceLabel} | ${b.trendLabel} | ${b.verificationLabel}</small></div>
          `;
          bList.appendChild(bLi);
        }
        catCard.appendChild(bList);
        container.appendChild(catCard);
      }

      // Unresolved Items if present
      if (pres.unresolvedItems.length > 0) {
        const unresCard = document.createElement("section");
        unresCard.className = "card card-unresolved";

        const unresTitle = document.createElement("h3");
        unresTitle.textContent = `Pozycje do weryfikacji (${pres.unresolvedItems.length})`;
        unresCard.appendChild(unresTitle);

        const uList = document.createElement("ul");
        for (const u of pres.unresolvedItems) {
          const uLi = document.createElement("li");
          uLi.innerHTML = `<strong>${u.name}</strong> [${u.unit}] - <small>${u.reason}</small>`;
          uList.appendChild(uLi);
        }
        unresCard.appendChild(uList);
        container.appendChild(unresCard);
      }
      break;
    }
  }

  return container;
}
