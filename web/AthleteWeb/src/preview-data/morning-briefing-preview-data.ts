import type { MorningBriefingPresentation } from "../models/morning-briefing-presentation";

export const morningBriefingPreviewData: MorningBriefingPresentation = Object.freeze({
  greeting: "Dzień dobry",
  athleteName: "Marcin",
  dateText: "Poniedziałek, 3 sierpnia",
  timeText: "07:30",
  coachMessage: Object.freeze([
    "Dzień zapowiada się bardzo dobrze.",
    "Po dwóch dniach spokojniejszego treningu organizm dobrze się zregenerował.",
    "Dzisiaj warto wykonać trening progowy.",
    "Największą korzyść przyniesie jakość, nie objętość.",
  ]),
  decision: Object.freeze({
    title: "Trening progowy",
    duration: "60–75 min",
    intensity: "Strefa 3–4",
  }),
  reasons: Object.freeze([
    "HRV wróciło do normy",
    "Sen był lepszy niż zwykle",
    "Zmęczenie spadło",
  ]),
  changesSinceYesterday: Object.freeze([
    "HRV poprawiło się",
    "Sen był dłuższy",
    "Zmęczenie jest niższe",
  ]),
  todayPlan: Object.freeze([
    "Trening progowy",
    "80 g węglowodanów przed treningiem",
    "Sen przed 23:00",
  ]),
  goal: Object.freeze({
    title: "Budowa wydolności",
    progressLabel: "75%",
    progressValue: 0.75,
    timeline: "Tydzień 3 z 12",
  }),
  shortcuts: Object.freeze([
    Object.freeze({ id: "recovery", label: "Regeneracja" }),
    Object.freeze({ id: "training", label: "Trening" }),
    Object.freeze({ id: "nutrition", label: "Odżywianie" }),
    Object.freeze({ id: "history", label: "Historia" }),
  ]),
});
