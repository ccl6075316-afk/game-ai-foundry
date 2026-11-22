"""Measure excess motion in a paused 1080p wheel replay.

Run verify_croaker_zoom_motion.gd with -- --pixels=<scratch prefix>, then pass
that same prefix here. The .gray and .csv files may be removed after checking.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np


def verify(prefix: Path) -> bool:
    meta = np.loadtxt(prefix.with_suffix(".csv"), delimiter=",")
    frames = np.memmap(prefix.with_suffix(".gray"), dtype=np.uint8, mode="r",
                       shape=(len(meta), 1080, 1920))
    # Relative screen scale of the subject includes both lens and eye position.
    scale = 1 / (np.tan(np.radians(meta[:, 2]) / 2) * meta[:, 3])
    center = np.array([959.5, 539.5], np.float32)
    mask = np.zeros((1080, 1920), np.uint8)
    mask[72:1000, 60:1860] = 255  # Omit window edges, controls and HUD.
    track = dict(winSize=(25, 25), maxLevel=3)
    median_errors, tail_errors = [], []
    feature_count = 0
    for i in range(15, len(frames)):
        before, after = frames[i - 1], frames[i]
        features = cv2.goodFeaturesToTrack(before, 240, .02, 20, mask=mask)
        if features is None:
            continue
        expected = (features - center) * (scale[i] / scale[i - 1]) + center
        found, ok, _ = cv2.calcOpticalFlowPyrLK(
            before, after, features, expected.astype(np.float32).copy(),
            flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **track)
        back, recovered, _ = cv2.calcOpticalFlowPyrLK(after, before, found, None, **track)
        valid = ((ok[:, 0] != 0) & (recovered[:, 0] != 0)
                 & (np.linalg.norm(back[:, 0] - features[:, 0], axis=1) < .7))
        errors = np.linalg.norm(found[:, 0] - expected[:, 0], axis=1)[valid]
        if len(errors) >= 20:
            median_errors.append(np.median(errors))
            tail_errors.append(np.percentile(errors, 90))
            feature_count += len(errors)
    if not median_errors:
        return False
    print(f"frames={len(median_errors)} features={feature_count} "
          f"eye_travel_m={meta[:, 1].max():.5f} "
          f"worst_frame_median_px={max(median_errors):.3f} "
          f"worst_frame_p90_px={max(tail_errors):.3f}")
    return (len(median_errors) == 149 and feature_count > 10_000
            and scale.max() / scale.min() > 4 and meta[:, 1].max() < .00001
            and max(median_errors) < .5 and max(tail_errors) < 1.)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", type=Path)
    cv2.setNumThreads(2)
    raise SystemExit(0 if verify(parser.parse_args().prefix) else 1)
