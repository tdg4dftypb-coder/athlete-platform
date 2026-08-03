import Combine
import Foundation

@MainActor
final class MorningBriefingViewModel: ObservableObject {
    let briefing: MorningBriefingPresentation

    init(briefing: MorningBriefingPresentation) {
        self.briefing = briefing
    }
}
