import Foundation

/// UI-ready content for the Morning Briefing feature.
///
/// This is intentionally a presentation model rather than a domain or transport
/// model. A future mapper will translate AthleteDashboard into this shape.
struct MorningBriefingPresentation: Equatable, Sendable {
    struct Decision: Equatable, Sendable {
        let title: String
        let duration: String
        let intensity: String
    }

    struct PlanItem: Equatable, Identifiable, Sendable {
        let id: String
        let title: String
        let systemImage: String
    }

    struct Goal: Equatable, Sendable {
        let title: String
        let progress: Double
        let timeline: String
    }

    let greeting: String
    let athleteName: String
    let dateText: String
    let coachMessage: String
    let decision: Decision
    let reasons: [String]
    let planItems: [PlanItem]
    let goal: Goal
}
