import SwiftUI

struct MorningBriefingView: View {
    @StateObject private var viewModel: MorningBriefingViewModel

    init(viewModel: MorningBriefingViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: AthleteTheme.screenSpacing) {
                    greeting
                    heroBriefing
                    todayDecision
                    reasons
                    todayPlan
                    goal
                }
                .padding(.horizontal, 20)
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
            .background(AthleteTheme.pageBackground)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                BottomNavigationBar()
            }
            .toolbar(.hidden, for: .navigationBar)
        }
        .tint(AthleteTheme.accent)
    }

    private var greeting: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("\(viewModel.briefing.greeting), \(viewModel.briefing.athleteName)")
                .font(.largeTitle.bold())
                .foregroundStyle(.primary)
            Text(viewModel.briefing.dateText)
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
    }

    private var heroBriefing: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label("AI Coach", systemImage: "sparkles")
                .font(.headline.weight(.semibold))
                .foregroundStyle(AthleteTheme.secondaryAccent)

            Text(viewModel.briefing.coachMessage)
                .font(.title3)
                .fontWeight(.medium)
                .foregroundStyle(.white)
                .lineSpacing(5)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(24)
        .background(
            LinearGradient(
                colors: [AthleteTheme.coachBackground, AthleteTheme.coachBackground.opacity(0.88)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: AthleteTheme.cardRadius)
        )
        .shadow(color: AthleteTheme.coachBackground.opacity(0.18), radius: 16, y: 8)
    }

    private var todayDecision: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: "Dzisiejsza decyzja")
            BriefingCard {
                VStack(alignment: .leading, spacing: 14) {
                    Label(viewModel.briefing.decision.title, systemImage: "bolt.heart.fill")
                        .font(.title2.bold())
                        .foregroundStyle(AthleteTheme.accent)

                    ViewThatFits(in: .horizontal) {
                        HStack(spacing: 10) {
                            decisionDetails
                        }
                        VStack(alignment: .leading, spacing: 10) {
                            decisionDetails
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var decisionDetails: some View {
        DecisionPill(text: viewModel.briefing.decision.duration, systemImage: "clock")
        DecisionPill(text: viewModel.briefing.decision.intensity, systemImage: "gauge.with.dots.needle.50percent")
    }

    private var reasons: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: "Dlaczego właśnie taki plan?")
            BriefingCard {
                VStack(alignment: .leading, spacing: 16) {
                    ForEach(viewModel.briefing.reasons, id: \.self) { reason in
                        Label(reason, systemImage: "checkmark.circle.fill")
                            .font(.body)
                            .foregroundStyle(.primary)
                            .symbolRenderingMode(.hierarchical)
                            .tint(AthleteTheme.accent)
                    }
                }
            }
        }
    }

    private var todayPlan: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: "Plan na dziś")
            BriefingCard {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(viewModel.briefing.planItems.enumerated()), id: \.element.id) { index, item in
                        Label(item.title, systemImage: item.systemImage)
                            .font(.body.weight(.medium))
                            .foregroundStyle(.primary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 12)

                        if index < viewModel.briefing.planItems.count - 1 {
                            Divider()
                        }
                    }
                }
            }
        }
    }

    private var goal: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeading(title: "Twój cel")
            BriefingCard {
                VStack(alignment: .leading, spacing: 14) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(viewModel.briefing.goal.title)
                            .font(.headline)
                        Spacer()
                        Text(viewModel.briefing.goal.progress, format: .percent.precision(.fractionLength(0)))
                            .font(.title2.bold())
                            .foregroundStyle(AthleteTheme.accent)
                    }

                    ProgressView(value: viewModel.briefing.goal.progress)
                        .tint(AthleteTheme.accent)
                        .accessibilityLabel("Postęp celu")

                    Text(viewModel.briefing.goal.timeline)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

private struct DecisionPill: View {
    let text: String
    let systemImage: String

    var body: some View {
        Label(text, systemImage: systemImage)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 12)
            .padding(.vertical, 9)
            .background(.tertiary, in: Capsule())
    }
}

private struct BottomNavigationBar: View {
    private let destinations = [
        ("Dzisiaj", "sun.max.fill", true),
        ("Trening", "figure.run", false),
        ("Postępy", "chart.line.uptrend.xyaxis", false),
        ("Więcej", "ellipsis", false),
    ]

    var body: some View {
        HStack(spacing: 4) {
            ForEach(destinations, id: \.0) { title, systemImage, isActive in
                Button(action: {}) {
                    VStack(spacing: 5) {
                        Image(systemName: systemImage)
                            .font(.body.weight(.semibold))
                        Text(title)
                            .font(.caption2.weight(.semibold))
                    }
                    .frame(maxWidth: .infinity)
                    .frame(minHeight: 44)
                    .foregroundStyle(isActive ? AthleteTheme.accent : Color.secondary)
                    .padding(.vertical, 8)
                }
                .buttonStyle(.plain)
                .disabled(!isActive)
                .accessibilityAddTraits(isActive ? .isSelected : [])
                .accessibilityHint(isActive ? "Aktualna karta" : "Funkcja będzie dostępna w przyszłości")
            }
        }
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .background(.bar)
        .overlay(alignment: .top) { Divider() }
    }
}

#Preview("Morning Briefing") {
    MorningBriefingView(
        viewModel: MorningBriefingViewModel(
            briefing: MorningBriefingPreviewData.marcin
        )
    )
}
