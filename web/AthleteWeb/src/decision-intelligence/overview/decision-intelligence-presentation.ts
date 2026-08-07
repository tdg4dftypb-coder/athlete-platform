import type { DecisionIntelligenceViewState } from './decision-intelligence-types';
import type { DecisionAuditRecordWire } from '../api/decision-intelligence-api-types';

export function createDecisionIntelligencePresentation(
  state: DecisionIntelligenceViewState,
  onRetry: () => void,
  onBack: () => void
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'decision-intelligence-view';

  // 1. Header
  const header = document.createElement('header');
  header.className = 'page-header';

  const backBtn = document.createElement('button');
  backBtn.type = 'button';
  backBtn.className = 'btn-back';
  backBtn.setAttribute('aria-label', 'Wróć do poprzedniego widoku');
  backBtn.innerHTML = '←';
  backBtn.addEventListener('click', onBack);

  const titleHeading = document.createElement('h1');
  titleHeading.tabIndex = -1;
  titleHeading.textContent = 'AI Coach';

  const subtitle = document.createElement('p');
  subtitle.className = 'page-subtitle';
  subtitle.textContent = 'Decision Intelligence 2.0';

  header.appendChild(backBtn);
  header.appendChild(titleHeading);
  header.appendChild(subtitle);
  container.appendChild(header);

  // Focus h1 on enter
  setTimeout(() => titleHeading.focus(), 50);

  const contentSection = document.createElement('section');
  contentSection.className = 'decision-content-section';
  container.appendChild(contentSection);

  // Render State
  switch (state.kind) {
    case 'loading': {
      const loadingEl = document.createElement('div');
      loadingEl.className = 'decision-loading-skeleton';
      loadingEl.setAttribute('role', 'status');
      loadingEl.setAttribute('aria-live', 'polite');
      loadingEl.innerHTML = `
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <p>Wczytywanie aktualnej decyzji AI Coach...</p>
      `;
      contentSection.appendChild(loadingEl);
      break;
    }

    case 'empty': {
      const emptyEl = document.createElement('div');
      emptyEl.className = 'decision-empty-state';
      emptyEl.innerHTML = `
        <h2>No decision is available yet.</h2>
        <p>Decyzja pojawi się automatycznie po przetworzeniu danych ze wszystkich źródeł.</p>
      `;
      contentSection.appendChild(emptyEl);
      break;
    }

    case 'failure':
    case 'network_error':
    case 'invalid_data': {
      const errEl = document.createElement('div');
      errEl.className = 'decision-error-state';
      errEl.setAttribute('role', 'alert');

      let msg = 'Wystąpił błąd podczas pobierania decyzji.';
      if (state.kind === 'network_error') {
        msg = 'Błąd połączenia z serwerem. Sprawdź połączenie internetowe.';
      } else if (state.kind === 'invalid_data') {
        msg = 'Decision data could not be loaded.';
      } else if (state.kind === 'failure') {
        msg = state.message;
      }

      errEl.innerHTML = `<h2>Błąd wczytywania</h2><p>${msg}</p>`;

      const retryBtn = document.createElement('button');
      retryBtn.type = 'button';
      retryBtn.className = 'btn-retry';
      retryBtn.setAttribute('aria-label', 'Spróbuj ponownie wczytać decyzję');
      retryBtn.textContent = 'Spróbuj ponownie';
      retryBtn.addEventListener('click', onRetry);

      errEl.appendChild(retryBtn);
      contentSection.appendChild(errEl);
      break;
    }

    case 'ready': {
      renderReadyDecision(contentSection, state.record);
      break;
    }
  }

  return container;
}

function renderReadyDecision(parent: HTMLElement, record: DecisionAuditRecordWire): void {
  const plan = record.recommendation_plan;
  const ctx = record.context;

  // 1. Hero Decision Card
  const heroCard = document.createElement('div');
  heroCard.className = `decision-hero-card severity-${plan.severity}`;

  const actionTextMap: Record<string, string> = {
    proceed: 'Proceed as planned',
    reduce: 'Reduce training load',
    replace_with_recovery: 'Replace with recovery',
    rest: 'Prioritize rest',
    review: 'Review before training',
  };

  const actionHeadline = actionTextMap[plan.action] ?? plan.action;
  const confidencePercent = Math.round(plan.confidence * 100);

  heroCard.innerHTML = `
    <div class="decision-hero-header">
      <span class="severity-badge">${plan.severity.toUpperCase()}</span>
      <span class="confidence-badge">${confidencePercent}% Confidence</span>
    </div>
    <h2 class="decision-hero-action">${actionHeadline}</h2>
    <div class="decision-hero-meta">
      <span>Wygenerowano: ${new Date(plan.generated_at).toLocaleString()}</span>
      <span>Policy v${plan.policy_version}</span>
    </div>
  `;
  parent.appendChild(heroCard);

  // 2. Recommendations Section
  const recsSection = document.createElement('section');
  recsSection.className = 'decision-section';
  recsSection.innerHTML = `<h2>Recommendations</h2>`;

  const recsList = document.createElement('ul');
  recsList.className = 'recommendations-list';

  for (const rec of plan.recommendations) {
    const li = document.createElement('li');
    li.className = `recommendation-card priority-${rec.priority}`;
    li.innerHTML = `
      <div class="rec-header">
        <span class="category-tag">${rec.category}</span>
        <span class="priority-tag">${rec.priority}</span>
      </div>
      <h3 class="rec-title">${rec.title}</h3>
      <p class="rec-desc">${rec.description}</p>
      <div class="rec-sources">Sygnały: ${rec.source_signal_codes.join(', ')}</div>
    `;
    recsList.appendChild(li);
  }
  recsSection.appendChild(recsList);
  parent.appendChild(recsSection);

  // 3. Explainability Section
  const expSection = document.createElement('section');
  expSection.className = 'decision-section';
  expSection.innerHTML = `
    <h2>Why this decision?</h2>
    <h3 class="explanation-headline">${plan.explanation.headline}</h3>
    <p class="explanation-summary">${plan.explanation.summary}</p>
  `;

  const expList = document.createElement('ul');
  expList.className = 'explanation-items-list';

  for (const item of plan.explanation.items) {
    const li = document.createElement('li');
    li.className = `explanation-item severity-${item.severity}`;
    li.innerHTML = `
      <div class="exp-item-header">
        <span class="exp-source">${item.source}</span>
        <span class="exp-severity">${item.severity}</span>
      </div>
      <p class="exp-summary">${item.summary}</p>
      <span class="exp-code">Kod sygnału: ${item.signal_code}</span>
    `;
    expList.appendChild(li);
  }
  expSection.appendChild(expList);
  parent.appendChild(expSection);

  // 4. Context Sources Section
  const ctxSection = document.createElement('section');
  ctxSection.className = 'decision-section';
  ctxSection.innerHTML = `<h2>Decision context</h2>`;

  const ctxGrid = document.createElement('div');
  ctxGrid.className = 'context-grid';

  // Recovery
  const recov = ctx.recovery;
  ctxGrid.appendChild(createContextSourceCard('Recovery', recov.status, [
    { label: 'Recovery score', val: recov.recovery_score !== null ? `${recov.recovery_score}/100` : 'Unavailable' },
    { label: 'Recovery status', val: recov.recovery_status ?? 'Unavailable' },
    { label: 'HRV status', val: recov.hrv_status ?? 'Unavailable' },
    { label: 'Resting HR', val: recov.resting_heart_rate_status ?? 'Unavailable' },
    { label: 'Sleep status', val: recov.sleep_status ?? 'Unavailable' },
  ]));

  // Training
  const tr = ctx.training;
  ctxGrid.appendChild(createContextSourceCard('Training', tr.status, [
    { label: 'Planned session', val: tr.planned_session_type ?? 'Unavailable' },
    { label: 'Duration', val: tr.planned_duration_minutes !== null ? `${tr.planned_duration_minutes} min` : 'Unavailable' },
    { label: 'Intensity', val: tr.planned_intensity ?? 'Unavailable' },
    { label: 'Training load', val: tr.recent_training_load !== null ? `${tr.recent_training_load}` : 'Unavailable' },
    { label: 'Fatigue status', val: tr.fatigue_status ?? 'Unavailable' },
  ]));

  // Biomarkers
  const bio = ctx.biomarkers;
  const bioSignalsStr = bio.signals.length > 0
    ? bio.signals.map(s => `${s.canonical_code}: ${s.interpretation}`).join(', ')
    : 'Brak niepokojących sygnałów';
  ctxGrid.appendChild(createContextSourceCard('Biomarkers', bio.status, [
    { label: 'Attention count', val: `${bio.attention_count}` },
    { label: 'Critical count', val: `${bio.critical_count}` },
    { label: 'Biomarker signals', val: bioSignalsStr },
  ]));

  // Performance
  const perf = ctx.performance;
  const lt1Str = perf.lt1 ? `${perf.lt1.status} (${perf.lt1.power_watts ?? '-'}W)` : 'Unavailable';
  const lt2Str = perf.lt2 ? `${perf.lt2.status} (${perf.lt2.power_watts ?? '-'}W)` : 'Unavailable';

  ctxGrid.appendChild(createContextSourceCard('Performance Lab', perf.status, [
    { label: 'Latest test ID', val: perf.latest_test_id ?? 'Unavailable' },
    { label: 'Test type', val: perf.latest_test_type ?? 'Unavailable' },
    { label: 'LT1 Threshold', val: lt1Str },
    { label: 'LT2 Threshold', val: lt2Str },
  ]));

  ctxSection.appendChild(ctxGrid);
  parent.appendChild(ctxSection);
}

function createContextSourceCard(title: string, status: string, metrics: Array<{ label: string; val: string }>): HTMLElement {
  const card = document.createElement('div');
  card.className = 'context-source-card';
  let html = `
    <div class="source-header">
      <h3 class="source-title">${title}</h3>
      <span class="status-badge status-${status}">${status}</span>
    </div>
    <dl class="source-metrics">
  `;
  for (const m of metrics) {
    html += `<dt>${m.label}</dt><dd>${m.val}</dd>`;
  }
  html += `</dl>`;
  card.innerHTML = html;
  return card;
}
