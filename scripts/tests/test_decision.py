from athlete.state_builder import AthleteStateBuilder
from decision.engine import DecisionEngine


athlete = AthleteStateBuilder().build()

decision = DecisionEngine().decide(athlete)

print()

print("Recommendation :", decision.recommendation)

print("Duration       :", decision.duration)

print("Target TSS     :", decision.target_tss)

print("Intensity      :", decision.intensity)

print()

print("Reasons")

for reason in decision.reasons:

    print("-", reason)

print()