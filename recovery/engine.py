from recovery.models import RecoveryResult


class RecoveryEngine:

    def analyze(self, context):

        score = 100

        reasons = []

        #
        # HRV
        #

        if context.hrv.delta_percent is not None:

            if context.hrv.delta_percent <= -15:

                score -= 25

                reasons.append(
                    f"HRV {context.hrv.delta_percent:.1f}%"
                )

            elif context.hrv.delta_percent <= -5:

                score -= 10

                reasons.append(
                    f"HRV {context.hrv.delta_percent:.1f}%"
                )

            elif context.hrv.delta_percent >= 5:

                score += 5

                reasons.append(
                    f"HRV +{context.hrv.delta_percent:.1f}%"
                )

        #
        # Resting HR
        #

        if context.resting_hr.delta is not None:

            if context.resting_hr.delta >= 8:

                score -= 20

                reasons.append(
                    f"RHR +{context.resting_hr.delta:.0f} bpm"
                )

            elif context.resting_hr.delta >= 4:

                score -= 10

                reasons.append(
                    f"RHR +{context.resting_hr.delta:.0f} bpm"
                )

            elif context.resting_hr.delta <= -2:

                score += 5

                reasons.append(
                    f"RHR {context.resting_hr.delta:.0f} bpm"
                )

        #
        # Sleep
        #

        if context.today.sleep_duration is not None:

            hours = context.today.sleep_duration / 60

            if hours < 6:

                score -= 20

                reasons.append(
                    f"Sen {hours:.1f} h"
                )

            elif hours < 7:

                score -= 10

                reasons.append(
                    f"Sen {hours:.1f} h"
                )

            elif hours >= 8:

                score += 5

                reasons.append(
                    f"Sen {hours:.1f} h"
                )

        score = max(0, min(100, score))

        if score >= 85:
            status = "🟢 ŚWIETNA"

        elif score >= 70:
            status = "🟡 DOBRA"

        elif score >= 50:
            status = "🟠 OBNIŻONA"

        else:
            status = "🔴 SŁABA"

        return RecoveryResult(
            score=score,
            status=status,
            reasons=reasons,
        )