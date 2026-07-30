from athlete.models import AthleteState

from decision.engine import DecisionEngine

from execution.timeline_matcher import TimelineMatcher

from optimizer.engine import OptimizerEngine

from planner.engine import PlannerEngine

from simulator.engine import SimulatorEngine

from timeline.builder import TimelineBuilder


class PlatformEngine:

    def __init__(self):

        self.decision = DecisionEngine()

        self.planner = PlannerEngine()

        self.optimizer = OptimizerEngine()

        self.simulator = SimulatorEngine()

        self.timeline = TimelineBuilder()

        self.timeline_matcher = TimelineMatcher()


    def run(
        self,
        athlete: AthleteState,
    ):

        plan = self.decision.decide(
            athlete,
        )

        decision = plan.decision

        workout = self.planner.build(
            decision,
            athlete,
        )

        optimized_workout = self.optimizer.optimize(
            workout,
        )

        simulation = self.simulator.simulate(
            optimized_workout,
        )

        timeline = self.timeline.build(
            optimized_workout,
        )

        return {
            "plan": decision,
            "workout": optimized_workout,
            "simulation": simulation,
            "timeline": timeline,
        }