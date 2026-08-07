import type { DecisionHistoryViewState, DecisionHistoryEntryPresentation } from './decisionHistoryTypes';
import type { DecisionAuditRecordWire } from '../api/decision-intelligence-api-types';

const ACTION_LABEL_MAP: Record<string, string> = {
  proceed: 'Kontynuuj zgodnie z planem',
  reduce: 'Zmniejsz obciążenie',
  replace_with_recovery: 'Zastąp trening regeneracją',
  rest: 'Odpoczynek',
  review: 'Wymagana ocena',
};

const SEVERITY_LABEL_MAP: Record<string, string> = {
  low: 'Niska',
  medium: 'Średnia',
  high: 'Wysoka',
  critical: 'Krytyczna',
};


export function mapRecordToPresentation(record: DecisionAuditRecordWire): DecisionHistoryEntryPresentation {
  const plan = record.recommendation_plan;
  const actionLabel = ACTION_LABEL_MAP[plan.action] ?? plan.action;
  const severityLabel = SEVERITY_LABEL_MAP[plan.severity] ?? plan.severity;
  const confidencePercent = Math.round(plan.confidence * 100);

  return {
    decisionId: record.decision_id,
    generatedAt: record.context.generated_at,
    recordedAt: record.recorded_at,
    action: plan.action,
    actionLabel,
    severity: plan.severity,
    severityLabel,
    confidencePercent,
    policyVersion: plan.policy_version,
    headline: plan.explanation.headline,
    summary: plan.explanation.summary,
    signalCount: record.policy_result.signals.length,
    recommendationCount: plan.recommendations.length,
    record,
  };
}


export function createDecisionHistoryPresentation(
  state: DecisionHistoryViewState,
  onRefresh: () => void
): HTMLElement {
  const section = document.createElement('section');
  section.className = 'decision-history-section';

  // Header with title and refresh button
  const header = document.createElement('div');
  header.className = 'decision-history-header';

  const titleGroup = document.createElement('div');
  const title = document.createElement('h2');
  title.textContent = 'Historia decyzji';
  const subtitle = document.createElement('p');
  subtitle.className = 'decision-history-subtitle';
  subtitle.textContent = 'Zapisane decyzje AI Coacha i sygnały, które wpłynęły na ich wynik.';
  titleGroup.appendChild(title);
  titleGroup.appendChild(subtitle);

  const refreshBtn = document.createElement('button');
  refreshBtn.type = 'button';
  refreshBtn.className = 'btn-refresh-history';
  refreshBtn.setAttribute('aria-label', 'Odśwież historię decyzji');
  refreshBtn.textContent = 'Odśwież historię';
  if (state.kind === 'loading') {
    refreshBtn.disabled = true;
  }
  refreshBtn.addEventListener('click', onRefresh);

  header.appendChild(titleGroup);
  header.appendChild(refreshBtn);
  section.appendChild(header);

  const body = document.createElement('div');
  body.className = 'decision-history-body';
  section.appendChild(body);

  switch (state.kind) {
    case 'loading': {
      body.setAttribute('role', 'status');
      body.setAttribute('aria-live', 'polite');
      body.innerHTML = `
        <div class="decision-history-loading">
          <div class="skeleton-line"></div>
          <div class="skeleton-line"></div>
          <p>Wczytywanie historii decyzji...</p>
        </div>
      `;
      break;
    }

    case 'empty': {
      body.innerHTML = `
        <div class="decision-history-empty">
          <h3>Brak zapisanych decyzji</h3>
          <p>Historia pojawi się po pierwszym jawnym uruchomieniu Decision Runtime.</p>
        </div>
      `;
      break;
    }

    case 'failure':
    case 'network_error':
    case 'invalid_data': {
      body.setAttribute('role', 'alert');
      let msg = 'Nie udało się pobrać historii decyzji.';
      if (state.kind === 'network_error') {
        msg = 'Brak połączenia z serwerem.';
      } else if (state.kind === 'invalid_data') {
        msg = 'Serwer zwrócił nieprawidłowe dane historii.';
      } else if (state.kind === 'failure') {
        msg = state.message;
      }

      body.innerHTML = `
        <div class="decision-history-error">
          <p>${msg}</p>
        </div>
      `;
      break;
    }

    case 'ready': {
      const records = state.payload.records;
      if (records.length === 0) {
        body.innerHTML = `
          <div class="decision-history-empty">
            <h3>Brak zapisanych decyzji</h3>
            <p>Historia pojawi się po pierwszym jawnym uruchomieniu Decision Runtime.</p>
          </div>
        `;
        break;
      }

      // Reversal UI: API oldest -> newest, UI presentation newest -> oldest
      const entries = [...records].reverse().map(mapRecordToPresentation);

      const countBadge = document.createElement('div');
      countBadge.className = 'history-count-badge';
      countBadge.textContent = `${state.payload.count} ${state.payload.count === 1 ? 'decyzja' : 'decyzji'}`;
      body.appendChild(countBadge);

      const list = document.createElement('ul');
      list.className = 'decision-history-list';

      entries.forEach((entry) => {
        const item = document.createElement('li');
        item.className = `decision-history-item severity-${entry.severity}`;

        const genDate = new Date(entry.generatedAt);
        const formattedDate = genDate.toLocaleDateString('pl-PL', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });

        const shortDecisionId = entry.decisionId.length > 16
          ? `${entry.decisionId.slice(0, 12)}…`
          : entry.decisionId;

        item.innerHTML = `
          <div class="history-item-header">
            <div class="history-item-badges">
              <span class="severity-badge">${entry.severityLabel}</span>
              <span class="confidence-badge">Pewność: ${entry.confidencePercent}%</span>
            </div>
            <time class="history-item-date" dateTime="${entry.generatedAt}">${formattedDate}</time>
          </div>
          <h3 class="history-item-headline">${entry.actionLabel}</h3>
          <p class="history-item-summary">${entry.summary}</p>
          <div class="history-item-counts">
            <span>Sygnały: ${entry.signalCount}</span>
            <span>Rekomendacje: ${entry.recommendationCount}</span>
          </div>
        `;


        // Disclosure details
        const details = document.createElement('details');
        details.className = 'history-item-details';
        const summary = document.createElement('summary');
        summary.textContent = 'Pokaż szczegóły';
        details.appendChild(summary);

        const detailsContent = document.createElement('div');
        detailsContent.className = 'details-content';

        // Signals section
        if (entry.record.policy_result.signals.length > 0) {
          const sigHeader = document.createElement('h4');
          sigHeader.textContent = 'Sygnały polityki';
          detailsContent.appendChild(sigHeader);

          const sigList = document.createElement('ul');
          sigList.className = 'details-signal-list';
          entry.record.policy_result.signals.forEach((sig) => {
            const sigLi = document.createElement('li');
            sigLi.textContent = `[${sig.source.toUpperCase()}] ${sig.code}: ${sig.summary} (${sig.severity})`;
            sigList.appendChild(sigLi);
          });
          detailsContent.appendChild(sigList);
        }

        // Recommendations section
        if (entry.record.recommendation_plan.recommendations.length > 0) {
          const recHeader = document.createElement('h4');
          recHeader.textContent = 'Rekomendacje';
          detailsContent.appendChild(recHeader);

          const recList = document.createElement('ul');
          recList.className = 'details-rec-list';
          entry.record.recommendation_plan.recommendations.forEach((rec) => {
            const recLi = document.createElement('li');
            recLi.innerHTML = `<strong>${rec.title}</strong>: ${rec.description} (priorytet: ${rec.priority})`;
            recList.appendChild(recLi);
          });
          detailsContent.appendChild(recList);
        }

        // Tech metadata
        const recGenDate = new Date(entry.recordedAt);
        const formattedRecordedDate = recGenDate.toLocaleDateString('pl-PL', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });

        const metaDiv = document.createElement('div');
        metaDiv.className = 'details-tech-meta';
        metaDiv.innerHTML = `
          <span>Polityka v${entry.policyVersion}</span> |
          <span>Wygenerowano: <time dateTime="${entry.generatedAt}">${formattedDate}</time></span> |
          <span>Zapisano: <time dateTime="${entry.recordedAt}">${formattedRecordedDate}</time></span> |
          <span title="${entry.decisionId}">ID decyzji: ${shortDecisionId}</span>
        `;
        detailsContent.appendChild(metaDiv);


        details.appendChild(detailsContent);
        item.appendChild(details);
        list.appendChild(item);
      });

      body.appendChild(list);
      break;
    }
  }

  return section;
}
