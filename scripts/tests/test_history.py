from training.history.workout_history_builder import WorkoutHistoryBuilder


history = WorkoutHistoryBuilder().last_days(365)

print()

print("Workouts :", history.count)
print("Duration :", history.total_duration)
print("Distance :", round(history.total_distance / 1000, 1), "km")
print("Calories :", history.total_calories)
print("Avg Power:", round(history.average_power))
print("Avg NP   :", round(history.average_np))

print()