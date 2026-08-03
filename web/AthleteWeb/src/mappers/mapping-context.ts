export const MORNING_BRIEFING_MAX_AGE_MS = 6 * 60 * 60 * 1000;

export interface MappingContext {
  readonly now: Date;
  readonly staleAfterMs: number;
  readonly athleteName: string;
  readonly locale?: string;
  readonly timeZone?: string;
}
