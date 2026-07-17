from decision.sports import Sport
from decision.workout_template import WorkoutTemplate


REST = WorkoutTemplate(

    sport=Sport.REST,

    recommendation="REST",

    duration=0,

    target_tss=0,

    intensity="REST",

)

RECOVERY = WorkoutTemplate(

    sport=Sport.CYCLING,

    recommendation="RECOVERY",

    duration=45,

    target_tss=25,

    intensity="Z1",

)

ENDURANCE = WorkoutTemplate(

    sport=Sport.CYCLING,

    recommendation="ENDURANCE",

    duration=90,

    target_tss=55,

    intensity="Z2",

)

TEMPO = WorkoutTemplate(

    sport=Sport.CYCLING,

    recommendation="TEMPO",

    duration=90,

    target_tss=70,

    intensity="Z3",

)

THRESHOLD = WorkoutTemplate(

    sport=Sport.CYCLING,

    recommendation="THRESHOLD",

    duration=75,

    target_tss=90,

    intensity="Z4",

)

VO2 = WorkoutTemplate(

    sport=Sport.CYCLING,

    recommendation="VO2",

    duration=75,

    target_tss=100,

    intensity="VO2",

)