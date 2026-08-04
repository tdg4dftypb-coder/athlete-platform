import type { MappingContext } from "./mapping-context";

export function parseContractTimestamp(value: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`);
}

export function parseContractDate(value: string): Date {
  return new Date(`${value}T12:00:00Z`);
}

export function dateInTimeZone(date: Date, timeZone?: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone,
  }).formatToParts(date);
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

export function formatContractDateTime(
  date: Date,
  context: MappingContext,
): string {
  return new Intl.DateTimeFormat(context.locale ?? "pl-PL", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: context.timeZone,
  }).format(date);
}
