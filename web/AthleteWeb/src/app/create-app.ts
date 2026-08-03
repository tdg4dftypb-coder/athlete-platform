import type { MorningBriefingPresentation } from "../models/morning-briefing-presentation";
import { renderMorningBriefing } from "../features/morning-briefing/morning-briefing-view";

export function createApp(model: MorningBriefingPresentation): HTMLElement {
  return renderMorningBriefing(model);
}
