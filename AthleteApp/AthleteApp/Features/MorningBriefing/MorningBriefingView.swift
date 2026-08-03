import SwiftUI

struct MorningBriefingView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @StateObject private var viewModel: MorningBriefingViewModel
    @State private var hasAppeared = false
    @State private var displayedGoalProgress = 0.0

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
                .padding(.horizontal, 24)
                .padding(.top, 24)
                .padding(.bottom, 40)
                .opacity(hasAppeared ? 1 : 0)
                .offset(y: reduceMotion || hasAppeared ? 0 : 8)
            }
            .background(AthleteTheme.pageBackground)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                BottomNavigationBar()
            }
            .toolbar(.hidden, for: .navigationBar)
        }
        .tint(AthleteTheme.accent)
        .onAppear {
            guard !hasAppeared else { return }

            if reduceMotion {
                hasAppeared = true
                displayedGoalProgress = viewModel.briefing.goal.progress
            } else {
                withAnimation(.easeOut(duration: 0.35)) {
                    hasAppeared = true
                }
                withAnimation(.easeOut(duration: 0.65).delay(0.15)) {
                    displayedGoalProgress = viewModel.briefing.goal.progress
                }
            }
        }
    }

    private var greeting: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(viewModel.briefing.greeting), \(viewModel.briefing.athleteName)")
                .font(.largeTitle.weight(.bold))
                .tracking(-0.6)
                .foregroundStyle(.primary)
            Text(viewModel.briefing.dateText)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
    }

    private var heroBriefing: some View {
        VStack(alignment: .leading, spacing: 20) {
            Label("AI Coach", systemImage: "sparkles")
                .font(.caption.weight(.bold))
                .textCase(.uppercase)
                .tracking(0.8)
                .foregroundStyle(AthleteTheme.secondaryAccent)

            Text(viewModel.briefing.coachMessage)
                .font(.title3.weight(.regular))
                .foregroundStyle(.white)
                .lineSpacing(6)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(26)
        .background(
            AthleteTheme.coachBackground,
            in: RoundedRectangle(
                cornerRadius: AthleteTheme.cardRadius,
                style: .continuous
            )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Odprawa AI Coacha. \(viewModel.briefing.coachMessage)")
    }

    private var todayDecision: some View {
        VStack(alignment: .leading, spacing: 14) {
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
            .accessibilityElement(children: .combine)
            .accessibilityLabel(
                "\(viewModel.briefing.decision.title), \(viewModel.briefing.decision.duration), \(viewModel.briefing.decision.intensity)"
            )
        }
    }

    @ViewBuilder
    private var decisionDetails: some View {
        DecisionPill(text: viewModel.briefing.decision.duration, systemImage: "clock")
        DecisionPill(text: viewModel.briefing.decision.intensity, systemImage: "gauge.with.dots.needle.50percent")
    }

    private var reasons: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeading(title: "Dlaczego właśnie taki plan?")
            BriefingCard {
                VStack(alignment: .leading, spacing: 18) {
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
        VStack(alignment: .leading, spacing: 14) {
            SectionHeading(title: "Plan na dziś")
            BriefingCard {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(viewModel.briefing.planItems.enumerated()), id: \.element.id) { index, item in
                        Label(item.title, systemImage: item.systemImage)
                            .font(.body.weight(.medium))
                            .foregroundStyle(.primary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 14)

                        if index < viewModel.briefing.planItems.count - 1 {
                            Divider()
                        }
                    }
                }
            }
        }
    }

    private var goal: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionHeading(title: "Twój cel")
            BriefingCard {
                VStack(alignment: .leading, spacing: 16) {
                    ViewThatFits(in: .horizontal) {
                        HStack(alignment: .firstTextBaseline) {
                            goalHeader
                        }
                        VStack(alignment: .leading, spacing: 8) {
                            goalHeader
                        }
                    }

                    ProgressView(value: displayedGoalProgress)
                        .tint(AthleteTheme.accent)
                        .accessibilityLabel("Postęp celu")
                        .accessibilityValue(
                            viewModel.briefing.goal.progress,
                            format: .percent.precision(.fractionLength(0))
                        )

                    Text(viewModel.briefing.goal.timeline)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    private var goalHeader: some View {
        Text(viewModel.briefing.goal.title)
            .font(.headline)
        Spacer()
        Text(viewModel.briefing.goal.progress, format: .percent.precision(.fractionLength(0)))
            .font(.title2.bold())
            .foregroundStyle(AthleteTheme.accent)
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
                .accessibilityLabel(title)
                .accessibilityValue(isActive ? "Wybrano" : "Niedostępne")
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

#Preview("Morning Briefing — Dark") {
    MorningBriefingView(
        viewModel: MorningBriefingViewModel(
            briefing: MorningBriefingPreviewData.marcin
        )
    )
    .preferredColorScheme(.dark)
}

#Preview("Morning Briefing — Accessibility Text") {
    MorningBriefingView(
        viewModel: MorningBriefingViewModel(
            briefing: MorningBriefingPreviewData.marcin
        )
    )
    .environment(\.dynamicTypeSize, .accessibility2)
}
