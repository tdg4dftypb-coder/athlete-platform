import SwiftUI

struct BriefingCard<Content: View>: View {
    private let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AthleteTheme.cardPadding)
            .background(AthleteTheme.cardBackground, in: RoundedRectangle(cornerRadius: AthleteTheme.cardRadius))
            .shadow(color: .black.opacity(0.05), radius: 12, y: 5)
    }
}
