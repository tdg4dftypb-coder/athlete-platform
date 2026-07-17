from planner.composer.templates import WorkoutTemplate


RECOVERY = WorkoutTemplate(

    warmup=0,

    cooldown=0,

    interval_duration=45 * 60,

    recovery_duration=0,

    repeats=1,

    power=0.50,

    recovery_power=0.50,

)

ENDURANCE = WorkoutTemplate(

    warmup=10 * 60,

    cooldown=10 * 60,

    interval_duration=70 * 60,

    recovery_duration=0,

    repeats=1,

    power=0.68,

    recovery_power=0.50,

)

TEMPO = WorkoutTemplate(

    warmup=15 * 60,

    cooldown=15 * 60,

    interval_duration=20 * 60,

    recovery_duration=5 * 60,

    repeats=3,

    power=0.85,

    recovery_power=0.55,

)

THRESHOLD = WorkoutTemplate(

    warmup=15 * 60,

    cooldown=15 * 60,

    interval_duration=10 * 60,

    recovery_duration=5 * 60,

    repeats=4,

    power=0.98,

    recovery_power=0.55,

)

VO2 = WorkoutTemplate(

    warmup=20 * 60,

    cooldown=15 * 60,

    interval_duration=4 * 60,

    recovery_duration=4 * 60,

    repeats=6,

    power=1.15,

    recovery_power=0.50,

)