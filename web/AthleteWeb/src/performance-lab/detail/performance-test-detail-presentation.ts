import type {
  PerformanceHistoryEntryWire,
  PerformanceStageWire,
  LactateCurvePointWire,
  DetectedThresholdWire,
} from '../api/performance-lab-api-types';
import type { DetailViewState } from './performance-test-detail-types';
import { formatThresholdStatusBadge } from './performance-test-detail-types';
import {
  formatDateLabel,
  formatModalityLabel,
  formatSessionStatusLabel,
  formatTestTypeLabel,
} from '../history/performance-lab-history-types';

export interface PerformanceTestDetailPresentationOptions {
  state: DetailViewState;
  onBack?: () => void;
  onRetry?: () => void;
}

export function createPerformanceTestDetailPresentation(
  options: PerformanceTestDetailPresentationOptions
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'pl-detail';

  const { state, onBack, onRetry } = options;

  const headerNav = document.createElement('div');
  headerNav.className = 'pl-detail__header-nav';

  if (onBack) {
    const backBtn = document.createElement('button');
    backBtn.type = 'button';
    backBtn.className = 'pl-detail__back-btn';
    backBtn.setAttribute('aria-label', 'Powrót do historii testów');
    backBtn.textContent = '← Powrót do historii';
    backBtn.addEventListener('click', () => onBack());
    headerNav.appendChild(backBtn);
  }

  container.appendChild(headerNav);

  const content = document.createElement('div');
  content.className = 'pl-detail__content';

  switch (state.kind) {
    case 'loading':
      content.appendChild(renderLoadingState());
      break;
    case 'not_found':
      content.appendChild(renderNotFoundState());
      break;
    case 'ready':
      content.appendChild(renderReadyDetail(state.entry));
      break;
    case 'failure':
      content.appendChild(renderErrorState('Błąd serwera', state.message, onRetry));
      break;
    case 'network_error':
      content.appendChild(
        renderErrorState(
          'Błąd połączenia',
          'Nie można połączyć się z serwerem. Sprawdź połączenie.',
          onRetry
        )
      );
      break;
    case 'invalid_data':
      content.appendChild(
        renderErrorState(
          'Nieprawidłowe dane',
          'Otrzymano niepoprawną strukturę danych szczegółów testu.',
          onRetry
        )
      );
      break;
  }

  container.appendChild(content);
  return container;
}

function renderLoadingState(): HTMLElement {
  const el = document.createElement('div');
  el.className = 'pl-detail__state pl-detail__state--loading';
  el.setAttribute('role', 'status');

  const spinner = document.createElement('div');
  spinner.className = 'pl-detail__spinner';

  const label = document.createElement('span');
  label.textContent = 'Wczytywanie szczegółów testu...';

  el.appendChild(spinner);
  el.appendChild(label);
  return el;
}

function renderNotFoundState(): HTMLElement {
  const el = document.createElement('div');
  el.className = 'pl-detail__state pl-detail__state--not-found';

  const h2 = document.createElement('h2');
  h2.textContent = 'Nie znaleziono testu';

  const p = document.createElement('p');
  p.textContent = 'Żądany test nie istnieje lub został usunięty.';

  el.appendChild(h2);
  el.appendChild(p);
  return el;
}

function renderErrorState(title: string, message: string, onRetry?: () => void): HTMLElement {
  const el = document.createElement('div');
  el.className = 'pl-detail__state pl-detail__state--error';
  el.setAttribute('role', 'alert');

  const h3 = document.createElement('h3');
  h3.textContent = title;

  const p = document.createElement('p');
  p.textContent = message;

  el.appendChild(h3);
  el.appendChild(p);

  if (onRetry) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pl-detail__retry-btn';
    btn.setAttribute('aria-label', 'Spróbuj ponownie pobrać szczegóły testu');
    btn.textContent = 'Spróbuj ponownie';
    btn.addEventListener('click', () => onRetry());
    el.appendChild(btn);
  }

  return el;
}

function renderReadyDetail(entry: PerformanceHistoryEntryWire): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'pl-detail__ready-wrapper';

  const session = entry.session;

  // 1. Header Section
  const headerCard = document.createElement('header');
  headerCard.className = 'pl-detail__header-card';

  const title = document.createElement('h1');
  title.className = 'pl-detail__title';
  title.tabIndex = -1;
  title.textContent = formatTestTypeLabel(session.test_type);
  headerCard.appendChild(title);

  const metaRow = document.createElement('div');
  metaRow.className = 'pl-detail__header-meta';

  const dateSpan = document.createElement('span');
  dateSpan.textContent = formatDateLabel(session.performed_at);

  const statusBadge = document.createElement('span');
  statusBadge.className = `pl-history-card__status-badge pl-history-card__status-badge--${session.status}`;
  statusBadge.textContent = formatSessionStatusLabel(session.status);

  const modalitySpan = document.createElement('span');
  modalitySpan.textContent = formatModalityLabel(session.modality);

  metaRow.appendChild(dateSpan);
  metaRow.appendChild(document.createTextNode(' • '));
  metaRow.appendChild(modalitySpan);
  metaRow.appendChild(document.createTextNode(' • '));
  metaRow.appendChild(statusBadge);

  if (session.protocol_name) {
    const protoSpan = document.createElement('span');
    protoSpan.textContent = ` • Protokół: ${session.protocol_name}`;
    metaRow.appendChild(protoSpan);
  }

  headerCard.appendChild(metaRow);
  wrapper.appendChild(headerCard);

  // 2. Session Summary Card
  const summaryCard = document.createElement('section');
  summaryCard.className = 'pl-detail__section-card';

  const summaryHeading = document.createElement('h2');
  summaryHeading.className = 'pl-detail__section-heading';
  summaryHeading.textContent = 'Podsumowanie sesji';
  summaryCard.appendChild(summaryHeading);

  const summaryGrid = document.createElement('div');
  summaryGrid.className = 'pl-detail__summary-grid';

  summaryGrid.appendChild(renderSummaryMetric('Masa ciała', session.body_mass_kg !== null ? `${session.body_mass_kg} kg` : '—'));
  summaryGrid.appendChild(renderSummaryMetric('Temp. otoczenia', session.ambient_temperature_c !== null ? `${session.ambient_temperature_c} °C` : '—'));
  summaryGrid.appendChild(renderSummaryMetric('Liczba etapów', `${session.stages.length}`));

  summaryCard.appendChild(summaryGrid);

  if (session.notes) {
    const notesBox = document.createElement('div');
    notesBox.className = 'pl-detail__notes-box';
    notesBox.textContent = `Uwagi: ${session.notes}`;
    summaryCard.appendChild(notesBox);
  }

  wrapper.appendChild(summaryCard);

  // 3. Threshold Cards (LT1 & LT2)
  if (entry.threshold_analysis) {
    const threshSection = document.createElement('section');
    threshSection.className = 'pl-detail__section-card';

    const threshHeading = document.createElement('h2');
    threshHeading.className = 'pl-detail__section-heading';
    threshHeading.textContent = 'Progi fizjologiczne';
    threshSection.appendChild(threshHeading);

    const threshGrid = document.createElement('div');
    threshGrid.className = 'pl-detail__thresh-grid';

    threshGrid.appendChild(renderThresholdCard(entry.threshold_analysis.lt1));
    threshGrid.appendChild(renderThresholdCard(entry.threshold_analysis.lt2));

    threshSection.appendChild(threshGrid);
    wrapper.appendChild(threshSection);
  }

  // 4. Lactate Curve Chart / Visualization
  if (entry.lactate_curve && entry.lactate_curve.points.length > 0) {
    const curveSection = document.createElement('section');
    curveSection.className = 'pl-detail__section-card';

    const curveHeading = document.createElement('h2');
    curveHeading.className = 'pl-detail__section-heading';
    curveHeading.textContent = 'Krzywa mleczanowa';
    curveSection.appendChild(curveHeading);

    curveSection.appendChild(
      renderLactateCurveSvg(entry.lactate_curve.points, session.modality, entry.threshold_analysis)
    );

    wrapper.appendChild(curveSection);
  }

  // 5. Stages Table
  const stagesSection = document.createElement('section');
  stagesSection.className = 'pl-detail__section-card';

  const stagesHeading = document.createElement('h2');
  stagesHeading.className = 'pl-detail__section-heading';
  stagesHeading.textContent = 'Etapy testu';
  stagesSection.appendChild(stagesHeading);

  stagesSection.appendChild(renderStagesTable(session.stages));
  wrapper.appendChild(stagesSection);

  return wrapper;
}

function renderSummaryMetric(label: string, value: string): HTMLElement {
  const item = document.createElement('div');
  item.className = 'pl-detail__summary-item';

  const l = document.createElement('span');
  l.className = 'pl-detail__summary-label';
  l.textContent = label;

  const v = document.createElement('span');
  v.className = 'pl-detail__summary-value';
  v.textContent = value;

  item.appendChild(l);
  item.appendChild(v);
  return item;
}

function renderThresholdCard(thresh: DetectedThresholdWire): HTMLElement {
  const card = document.createElement('div');
  card.className = `pl-detail-thresh-card pl-detail-thresh-card--${thresh.status}`;

  const header = document.createElement('div');
  header.className = 'pl-detail-thresh-card__header';

  const title = document.createElement('h3');
  title.className = 'pl-detail-thresh-card__title';
  title.textContent = thresh.name;

  const statusBadge = document.createElement('span');
  statusBadge.className = `pl-detail-thresh-card__badge pl-detail-thresh-card__badge--${thresh.status}`;
  statusBadge.textContent = formatThresholdStatusBadge(thresh.status);

  header.appendChild(title);
  header.appendChild(statusBadge);
  card.appendChild(header);

  if (thresh.status === 'detected') {
    const grid = document.createElement('div');
    grid.className = 'pl-detail-thresh-card__grid';

    if (thresh.power_watts !== null) {
      grid.appendChild(renderThreshMetric('Moc', `${thresh.power_watts} W`));
    }
    if (thresh.speed_kph !== null) {
      grid.appendChild(renderThreshMetric('Prędkość', `${thresh.speed_kph} km/h`));
    }
    if (thresh.heart_rate_bpm !== null) {
      grid.appendChild(renderThreshMetric('Tętno', `${thresh.heart_rate_bpm} bpm`));
    }
    if (thresh.lactate_mmol_l !== null) {
      grid.appendChild(renderThreshMetric('Mleczan', `${thresh.lactate_mmol_l} mmol/L`));
    }
    if (thresh.confidence !== null) {
      grid.appendChild(renderThreshMetric('Pewność', `${Math.round(thresh.confidence * 100)}%`));
    }

    card.appendChild(grid);
  } else {
    const info = document.createElement('p');
    info.className = 'pl-detail-thresh-card__info';
    info.textContent = `Próg ${thresh.name} (${thresh.target_lactate_mmol_l} mmol/L) — ${formatThresholdStatusBadge(thresh.status)}.`;
    card.appendChild(info);
  }

  const methodFoot = document.createElement('div');
  methodFoot.className = 'pl-detail-thresh-card__method';
  methodFoot.textContent = `Metoda: ${thresh.method}`;
  card.appendChild(methodFoot);

  return card;
}

function renderThreshMetric(label: string, value: string): HTMLElement {
  const d = document.createElement('div');
  d.className = 'pl-detail-thresh-card__metric';

  const l = document.createElement('span');
  l.className = 'pl-detail-thresh-card__metric-label';
  l.textContent = label;

  const v = document.createElement('span');
  v.className = 'pl-detail-thresh-card__metric-value';
  v.textContent = value;

  d.appendChild(l);
  d.appendChild(v);
  return d;
}

// ── Pure SVG Lactate Curve Visualization ──────────────────────────────────────

function renderLactateCurveSvg(
  points: LactateCurvePointWire[],
  modality: string,
  analysis: { lt1: DetectedThresholdWire; lt2: DetectedThresholdWire } | null
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'pl-curve-chart';

  const chartTitle = `Wykres krzywej mleczanowej (${points.length} punktów)`;
  container.setAttribute('aria-label', chartTitle);
  container.setAttribute('role', 'img');

  const width = 600;
  const height = 280;
  const padding = 40;

  // Determine X metric: power_watts if cycling, speed_kph if running/rowing, else stage_number fallback
  const getX = (p: LactateCurvePointWire): number => {
    if (modality === 'cycling' && p.power_watts !== null) return p.power_watts;
    if ((modality === 'running' || modality === 'rowing') && p.speed_kph !== null) return p.speed_kph;
    if (p.power_watts !== null) return p.power_watts;
    if (p.speed_kph !== null) return p.speed_kph;
    return p.stage_number;
  };

  const xVals = points.map(getX);
  const yVals = points.map((p) => p.lactate_mmol_l);

  const minX = Math.min(...xVals);
  const maxXRaw = Math.max(...xVals);
  const maxX = maxXRaw === minX ? minX + 1 : maxXRaw;

  const minY = 0;
  const maxYRaw = Math.max(...yVals);
  const maxY = Math.max(6, maxYRaw === 0 ? 6 : maxYRaw * 1.1);

  const scaleX = (val: number) => padding + ((val - minX) / (maxX - minX)) * (width - 2 * padding);
  const scaleY = (val: number) => height - padding - ((val - minY) / (maxY - minY)) * (height - 2 * padding);


  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('class', 'pl-curve-chart__svg');

  const titleSvg = document.createElementNS('http://www.w3.org/2000/svg', 'title');
  titleSvg.textContent = chartTitle;
  svg.appendChild(titleSvg);

  // Axes lines
  const axisX = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  axisX.setAttribute('x1', `${padding}`);
  axisX.setAttribute('y1', `${height - padding}`);
  axisX.setAttribute('x2', `${width - padding}`);
  axisX.setAttribute('y2', `${height - padding}`);
  axisX.setAttribute('stroke', 'var(--color-border, #334155)');
  svg.appendChild(axisX);

  const axisY = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  axisY.setAttribute('x1', `${padding}`);
  axisY.setAttribute('y1', `${padding}`);
  axisY.setAttribute('x2', `${padding}`);
  axisY.setAttribute('y2', `${height - padding}`);
  axisY.setAttribute('stroke', 'var(--color-border, #334155)');
  svg.appendChild(axisY);

  // Polyline for points
  const pointsString = points.map((p) => `${scaleX(getX(p))},${scaleY(p.lactate_mmol_l)}`).join(' ');
  const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  polyline.setAttribute('fill', 'none');
  polyline.setAttribute('stroke', 'var(--color-accent, #0284c7)');
  polyline.setAttribute('stroke-width', '2.5');
  polyline.setAttribute('points', pointsString);
  svg.appendChild(polyline);

  // LT Markers if detected
  if (analysis) {
    if (analysis.lt1.status === 'detected' && analysis.lt1.stage_number !== null) {
      const lt1Pt = points.find((pt) => pt.stage_number === analysis.lt1.stage_number);
      if (lt1Pt) {
        const cx = scaleX(getX(lt1Pt));
        const cy = scaleY(lt1Pt.lactate_mmol_l);
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('cx', `${cx}`);
        marker.setAttribute('cy', `${cy}`);
        marker.setAttribute('r', '7');
        marker.setAttribute('fill', '#38bdf8');
        marker.setAttribute('stroke', '#ffffff');
        marker.setAttribute('stroke-width', '2');
        svg.appendChild(marker);
      }
    }

    if (analysis.lt2.status === 'detected' && analysis.lt2.stage_number !== null) {
      const lt2Pt = points.find((pt) => pt.stage_number === analysis.lt2.stage_number);
      if (lt2Pt) {
        const cx = scaleX(getX(lt2Pt));
        const cy = scaleY(lt2Pt.lactate_mmol_l);
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('cx', `${cx}`);
        marker.setAttribute('cy', `${cy}`);
        marker.setAttribute('r', '7');
        marker.setAttribute('fill', '#f43f5e');
        marker.setAttribute('stroke', '#ffffff');
        marker.setAttribute('stroke-width', '2');
        svg.appendChild(marker);
      }
    }
  }

  // Data point dots
  for (const p of points) {
    const cx = scaleX(getX(p));
    const cy = scaleY(p.lactate_mmol_l);

    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('cx', `${cx}`);
    dot.setAttribute('cy', `${cy}`);
    dot.setAttribute('r', '4');
    dot.setAttribute('fill', 'var(--color-accent, #0284c7)');
    svg.appendChild(dot);
  }

  container.appendChild(svg);

  // Accessible Text Alternative in DOM
  const textAlt = document.createElement('div');
  textAlt.className = 'pl-curve-chart__alt-text';
  textAlt.textContent = `Punkty krzywej (${points.map((p) => `${getX(p)}: ${p.lactate_mmol_l} mmol/L`).join(', ')})`;
  container.appendChild(textAlt);

  return container;
}

// ── Stages Table ─────────────────────────────────────────────────────────────

function renderStagesTable(stages: PerformanceStageWire[]): HTMLElement {
  const tableContainer = document.createElement('div');
  tableContainer.className = 'pl-detail__table-wrapper';

  const table = document.createElement('table');
  table.className = 'pl-detail__table';

  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th>Etap</th>
      <th>Moc</th>
      <th>Prędkość</th>
      <th>Tętno</th>
      <th>Mleczan</th>
      <th>Kadencja</th>
      <th>RPE</th>
      <th>Status</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');

  for (const st of stages) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${st.stage_number}</td>
      <td>${st.power_watts !== null ? `${st.power_watts} W` : '—'}</td>
      <td>${st.speed_kph !== null ? `${st.speed_kph} km/h` : '—'}</td>
      <td>${st.heart_rate_bpm !== null ? `${st.heart_rate_bpm} bpm` : '—'}</td>
      <td>${st.lactate_mmol_l !== null ? `${st.lactate_mmol_l} mmol/L` : '—'}</td>
      <td>${st.cadence_rpm !== null ? `${st.cadence_rpm} rpm` : '—'}</td>
      <td>${st.perceived_exertion !== null ? `${st.perceived_exertion}` : '—'}</td>
      <td>${formatSessionStatusLabel(st.completion_status)}</td>
    `;
    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  tableContainer.appendChild(table);
  return tableContainer;
}
