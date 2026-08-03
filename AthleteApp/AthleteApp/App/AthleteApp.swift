import SwiftUI

@main
struct AthleteApp: App {
    var body: some Scene {
        WindowGroup {
            MorningBriefingView(
                viewModel: MorningBriefingViewModel(
                    briefing: MorningBriefingPreviewData.marcin
                )
            )
        }
    }
}
