from recovery.models import (
    RecoveryMetric,
    RecoveryMetricStatus,
    RecoveryResult,
)


class RecoveryEngine:

    def analyze(self, context):

        score = 100

        reasons = []

        #
        # HRV
        #

        hrv_score = 100
        hrv_status = RecoveryMetricStatus.UNAVAILABLE

        if context.hrv.delta_percent is not None:

            if context.hrv.delta_percent <= -15:

                hrv_score -= 25
                score -= 25
                hrv_status = RecoveryMetricStatus.LIMITING

                reasons.append(
                    f"HRV {context.hrv.delta_percent:.1f}%"
                )

            elif context.hrv.delta_percent <= -5:

                hrv_score -= 10
                score -= 10
                hrv_status = RecoveryMetricStatus.CAUTION

                reasons.append(
                    f"HRV {context.hrv.delta_percent:.1f}%"
                )

            elif context.hrv.delta_percent >= 5:

                hrv_score += 5
                score += 5
                hrv_status = RecoveryMetricStatus.SUPPORTIVE

                reasons.append(
                    f"HRV +{context.hrv.delta_percent:.1f}%"
                )

            else:
                hrv_status = RecoveryMetricStatus.NEUTRAL

        hrv_score = max(0, min(100, hrv_score))

        hrv = RecoveryMetric(

            value=context.hrv.today,

            baseline=context.hrv.average_7,

            delta=context.hrv.delta,

            delta_percent=context.hrv.delta_percent,

            score=hrv_score,

            status=hrv_status,

        )

        #
        # Resting HR
        #

        rhr_score = 100
        rhr_status = RecoveryMetricStatus.UNAVAILABLE

        if context.resting_hr.delta is not None:

            if context.resting_hr.delta >= 8:

                rhr_score -= 20
                score -= 20
                rhr_status = RecoveryMetricStatus.LIMITING

                reasons.append(
                    f"RHR +{context.resting_hr.delta:.0f} bpm"
                )

            elif context.resting_hr.delta >= 4:

                rhr_score -= 10
                score -= 10
                rhr_status = RecoveryMetricStatus.CAUTION

                reasons.append(
                    f"RHR +{context.resting_hr.delta:.0f} bpm"
                )

            elif context.resting_hr.delta <= -2:

                rhr_score += 5
                score += 5
                rhr_status = RecoveryMetricStatus.SUPPORTIVE

                reasons.append(
                    f"RHR {context.resting_hr.delta:.0f} bpm"
                )

            else:
                rhr_status = RecoveryMetricStatus.NEUTRAL

        rhr_score = max(0, min(100, rhr_score))

        resting_hr = RecoveryMetric(

            value=context.resting_hr.today,

            baseline=context.resting_hr.average_7,

            delta=context.resting_hr.delta,

            delta_percent=context.resting_hr.delta_percent,

            score=rhr_score,

            status=rhr_status,

        )

        #
        # Sleep
        #

        sleep_score = 100

        hours = None
        sleep_status = RecoveryMetricStatus.UNAVAILABLE

        if context.today.sleep_duration is not None:

            hours = context.today.sleep_duration / 60

            if hours < 6:

                sleep_score -= 20
                score -= 20
                sleep_status = RecoveryMetricStatus.LIMITING

                reasons.append(
                    f"Sen {hours:.1f} h"
                )

            elif hours < 7:

                sleep_score -= 10
                score -= 10
                sleep_status = RecoveryMetricStatus.CAUTION

                reasons.append(
                    f"Sen {hours:.1f} h"
                )

            elif hours >= 8:

                sleep_score += 5
                score += 5
                sleep_status = RecoveryMetricStatus.SUPPORTIVE

                reasons.append(
                    f"Sen {hours:.1f} h"
                )

            else:
                sleep_status = RecoveryMetricStatus.NEUTRAL

        sleep_score = max(0, min(100, sleep_score))

        sleep = RecoveryMetric(

            value=hours,

            baseline=context.sleep.average_7 / 60 if context.sleep.average_7 else None,

            delta=context.sleep.delta / 60 if context.sleep.delta else None,

            delta_percent=context.sleep.delta_percent,

            score=sleep_score,

            status=sleep_status,

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

            hrv=hrv,

            resting_hr=resting_hr,

            sleep=sleep,

        )