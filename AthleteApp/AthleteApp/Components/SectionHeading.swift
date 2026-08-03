import SwiftUI

struct SectionHeading: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.title3.weight(.semibold))
            .foregroundStyle(.primary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityAddTraits(.isHeader)
    }
}
