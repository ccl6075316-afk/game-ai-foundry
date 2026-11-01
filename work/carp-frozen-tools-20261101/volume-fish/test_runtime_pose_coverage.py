import copy
import unittest
from runtime_pose_coverage import validate_runtime_pose_coverage


def candidate(membranes=False):
    rows = [{"action":"Static", "seconds":0.0}]
    if membranes:
        rows += [{"action":"Native", "seconds":k / 25.0} for k in range(25)]
    for segment, action in enumerate(["Swim", "Turn", "Ascend", "Dive", "Swim"]):
        rows.append({"action":"GaitTransition:" + action, "seconds":segment * 4.0})
        rows += [{"action":"Gait:%s:%s" % (action, "propel" if k % 2 else "coast"), "seconds":segment * 4.0 + (k + 1) * 0.1} for k in range(40)]
    if membranes:
        rows += [{"action":"GaitDense:%s:%s" % (["Turn", "Dive", "Ascend", "Swim"][min(3, k // 65)], "propel" if k % 2 else "coast"), "seconds":20.0 + (k + 1) * 0.05} for k in range(259)]
    return {"candidate_gait_revision":132, "expected_fins":["all-explicit-fins"], "samples":rows, **({"fin_membrane_revision":1} if membranes else {})}


class CoverageTests(unittest.TestCase):
    def test_valid_candidate_inventories(self):
        for membranes in [False, True]: validate_runtime_pose_coverage(candidate(membranes))

    def test_candidate_rejects_missing_or_wrong_samples(self):
        for fault in ["sample", "action", "coast", "revision", "time", "inventory", "dense"]:
            data = candidate(True)
            if fault == "sample": data["samples"].pop()
            elif fault == "action": data["samples"][27]["action"] = "Gait:Unknown:coast"
            elif fault == "coast":
                for row in data["samples"]: row["action"] = row["action"].replace(":coast", ":propel")
            elif fault == "revision": data["candidate_gait_revision"] = 133
            elif fault == "time": data["samples"][27]["seconds"] = float("nan")
            elif fault == "inventory": data["expected_fins"] = []
            elif fault == "dense": data["samples"][-1]["action"] = "Range:WideFast"
            with self.subTest(fault=fault), self.assertRaises(ValueError): validate_runtime_pose_coverage(data)

    def test_canonical_177_contract_unchanged(self):
        counts = {"Static":1, **{a:16 for a in ["Swim", "Turn", "Ascend", "Dive"]}, **{"Transition:"+a:4 for a in ["Swim", "Turn", "Ascend", "Dive"]}, **{"Range:"+a:16 for a in ["Neutral", "WideSlow", "WideFast", "FinsOnly", "BodyOnly"]}, **{"RangeTransition:"+a:4 for a in ["Neutral", "WideSlow", "WideFast", "FinsOnly"]}}
        data = {"expected_fins":["fin"], "motion_range_revision":1, "samples":[{"action":a} for a, count in counts.items() for _ in range(count)]}
        self.assertEqual(validate_runtime_pose_coverage(data), counts)
        broken = copy.deepcopy(data)
        broken["samples"].pop()
        with self.assertRaises(ValueError): validate_runtime_pose_coverage(broken)


if __name__ == "__main__": unittest.main()
