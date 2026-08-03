export interface MappingContext {
  readonly now: Date;
  readonly staleAfterMs: number;
  readonly athleteName: string;
  readonly locale?: string;
  readonly timeZone?: string;
}
