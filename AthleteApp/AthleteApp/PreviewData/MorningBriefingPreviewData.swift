import Foundation

enum MorningBriefingPreviewData {
    static let marcin = MorningBriefingPresentation(
        greeting: "Dzień dobry",
        athleteName: "Marcin",
        dateText: "Poniedziałek, 3 sierpnia",
        coachMessage: """
        Dzień zapowiada się bardzo dobrze.

        Po dwóch dniach regeneracji organizm jest gotowy na trening jakościowy.

        Największą korzyść przyniesie jakość, nie objętość.
        """,
        decision: .init(
            title: "Trening progowy",
            duration: "60–75 min",
            intensity: "Strefa 3–4"
        ),
        reasons: [
            "HRV wróciło do normy",
            "Sen był lepszy niż zwykle",
            "Zmęczenie spadło",
        ],
        planItems: [
            .init(id: "training", title: "Trening progowy", systemImage: "figure.run"),
            .init(id: "nutrition", title: "80 g węglowodanów", systemImage: "fork.knife"),
            .init(id: "sleep", title: "Sen przed 23:00", systemImage: "moon.stars.fill"),
        ],
        goal: .init(
            title: "Budowa wydolności",
            progress: 0.75,
            timeline: "Tydzień 3 z 12"
        )
    )
}
