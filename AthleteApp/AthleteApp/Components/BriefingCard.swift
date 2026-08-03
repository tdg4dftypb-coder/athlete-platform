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
            .background(
                AthleteTheme.cardBackground,
                in: RoundedRectangle(
                    cornerRadius: AthleteTheme.cardRadius,
                    style: .continuous
                )
            )
            .overlay {
                RoundedRectangle(
                    cornerRadius: AthleteTheme.cardRadius,
                    style: .continuous
                )
                .stroke(AthleteTheme.cardBorder, lineWidth: 1)
            }
            .shadow(color: .black.opacity(0.04), radius: 10, y: 4)
    }
}
