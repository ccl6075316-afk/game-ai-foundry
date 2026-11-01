"""Pure, strict pose-inventory contracts for canonical and opt-in gait exports."""
from collections import Counter
import math


def validate_runtime_pose_coverage(export):
    samples = export["samples"]
    counts = dict(Counter(row["action"] for row in samples))
    if "native_cycle_revision" in export:
        if export["native_cycle_revision"] != 1 or not export.get("expected_fins"):
            raise ValueError("Unknown native cycle contract or missing fin inventory")
        if any(k in export for k in ["candidate_gait_revision", "motion_range_revision", "fin_membrane_revision"]):
            raise ValueError("Native-only evidence cannot impersonate runtime or membrane coverage")
        duration = export.get("native_clip_seconds", 0)
        if not math.isfinite(duration) or duration <= 0 or counts != {"Static": 1, "Native": 25}:
            raise ValueError("Incomplete native cycle coverage")
        if samples[0]["action"] != "Static" or samples[0]["seconds"] != 0:
            raise ValueError("Native cycle requires static baseline first")
        for phase, row in enumerate(samples[1:]):
            if row["action"] != "Native" or not math.isfinite(row["seconds"]) or abs(row["seconds"] - duration * phase / 25) > 1e-6:
                raise ValueError("Native cycle missing or duplicated phase")
        return counts
    if "candidate_gait_revision" in export:
        if export["candidate_gait_revision"] != 132:
            raise ValueError("Unknown candidate gait revision")
        if not export.get("expected_fins"):
            raise ValueError("Candidate gait requires a complete explicit fin inventory")
        membranes = export.get("fin_membrane_revision") == 1
        if len(samples) != (490 if membranes else 206):
            raise ValueError("Incomplete candidate gait sample count")
        if export.get("motion_range_revision") is not None:
            raise ValueError("Candidate gait cannot impersonate canonical range coverage")

        def row_at(index, label, seconds):
            row = samples[index]
            if row["action"] != label or not math.isfinite(row["seconds"]) or abs(row["seconds"] - seconds) > 1e-6:
                raise ValueError("Invalid candidate sequence/clock at sample %d" % index)

        row_at(0, "Static", 0.0)
        cursor = 1
        if membranes:
            previous = -1.0
            for row in samples[cursor:cursor + 25]:
                if row["action"] != "Native" or not math.isfinite(row["seconds"]) or row["seconds"] <= previous:
                    raise ValueError("Incomplete or nonmonotonic native coverage")
                previous = row["seconds"]
            if samples[cursor]["seconds"] != 0.0:
                raise ValueError("Native coverage must begin at zero")
            cursor += 25
        for segment, action in enumerate(["Swim", "Turn", "Ascend", "Dive", "Swim"]):
            row_at(cursor, "GaitTransition:" + action, segment * 4.0)
            cursor += 1
            phases = set()
            for k in range(40):
                label = samples[cursor]["action"]
                pieces = label.split(":")
                if len(pieces) != 3 or pieces[:2] != ["Gait", action] or pieces[2] not in {"propel", "coast"}:
                    raise ValueError("Invalid candidate action/phase label")
                phases.add(pieces[2])
                row_at(cursor, label, segment * 4.0 + (k + 1) * 0.1)
                cursor += 1
            if phases != {"propel", "coast"}:
                raise ValueError("Missing propel/coast candidate action coverage")
        if membranes:
            phases = {action:set() for action in ["Turn", "Dive", "Ascend", "Swim"]}
            for k in range(259):
                action = ["Turn", "Dive", "Ascend", "Swim"][min(3, k // 65)]
                pieces = samples[cursor]["action"].split(":")
                if len(pieces) != 3 or pieces[:2] != ["GaitDense", action] or pieces[2] not in {"propel", "coast"}:
                    raise ValueError("Invalid dense candidate action/phase label")
                phases[action].add(pieces[2])
                row_at(cursor, samples[cursor]["action"], 20.0 + (k + 1) * 0.05)
                cursor += 1
            if any(value != {"propel", "coast"} for value in phases.values()):
                raise ValueError("Missing dense candidate propel/coast action coverage")
        return counts
    # Preserve canonical legacy coverage exactly.
    expected = ({"Static":1, **{a:16 for a in ["Swim", "Turn", "Ascend", "Dive"]}, **{"Transition:"+a:4 for a in ["Swim", "Turn", "Ascend", "Dive"]}}
                if export.get("expected_fins") else {a:8 for a in ["Swim", "Turn", "Ascend", "Dive"]})
    if export.get("motion_range_revision") == 1:
        expected.update({"Range:"+a:16 for a in ["Neutral", "WideSlow", "WideFast", "FinsOnly", "BodyOnly"]})
        expected.update({"RangeTransition:"+a:4 for a in ["Neutral", "WideSlow", "WideFast", "FinsOnly"]})
    if export.get("fin_membrane_revision") == 1:
        expected["Native"] = 25
        expected.update({"Clearance:"+a:64 for a in ["MixedLow", "MixedMid", "Independent", "MaxDense"]})
        expected["Clearance:ControlSweep"] = 32
    if counts != expected:
        raise ValueError("Incomplete runtime pose coverage: " + str(counts))
    return counts
