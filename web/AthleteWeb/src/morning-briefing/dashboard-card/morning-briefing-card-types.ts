import type { MorningBriefing, MorningBriefingStatus, MorningBriefingPriority } from '../api/morning-briefing-api-types';

// ── Priority ordering ─────────────────────────────────────────────────────────

const PRIORITY_ORDER: Record<MorningBriefingPriority, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

export type TopRecommendation = {
  title: string;
  priority: MorningBriefingPriority;
};

export function pickTopRecommendation(briefing: MorningBriefing): TopRecommendation | null {
  let top: TopRecommendation | null = null;

  for (const section of briefing.sections) {
    for (const rec of section.recommendations) {
      if (!top || PRIORITY_ORDER[rec.priority] > PRIORITY_ORDER[top.priority]) {
        top = { title: rec.title, priority: rec.priority };
      }
    }
  }

  return top;
}

export function statusLabel(status: MorningBriefingStatus): string {
  switch (status) {
    case 'ready': return 'Your briefing is ready.';
    case 'partial': return 'Some briefing data is unavailable.';
    case 'unavailable': return 'Morning briefing is not available yet.';
    case 'stale': return 'Some briefing data may be outdated.';
  }
}

export function formatGeneratedAt(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

// ── Card State types ──────────────────────────────────────────────────────────

export type CardState =
  | { kind: 'loading' }
  | { kind: 'ready'; briefing: MorningBriefing; topRec: TopRecommendation | null }
  | { kind: 'partial'; briefing: MorningBriefing; topRec: TopRecommendation | null }
  | { kind: 'unavailable'; briefing: MorningBriefing }
  | { kind: 'stale'; briefing: MorningBriefing; topRec: TopRecommendation | null }
  | { kind: 'failure'; errorMessage: string }
  | { kind: 'network_error'; errorMessage: string }
  | { kind: 'invalid_data'; errorMessage: string };
