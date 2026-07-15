from performance.engine import PerformanceEngine


state = PerformanceEngine().analyze()

print()

print("Weekly")

print(" Workouts :", state.weekly.workouts)

print(" Total TSS:", round(state.weekly.total_tss, 1))

print(" Avg TSS  :", round(state.weekly.average_tss, 1))

print()

print("Monthly")

print(" Workouts :", state.monthly.workouts)

print(" Total TSS:", round(state.monthly.total_tss, 1))

print(" Avg TSS  :", round(state.monthly.average_tss, 1))

print()

print("ATL :", round(state.atl, 1))

print("CTL :", round(state.ctl, 1))

print("TSB :", round(state.tsb, 1))

print()