"""Check a 45-second tank replay exported with -- --passing=<scratch prefix>."""
import argparse
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def verify(prefix: Path) -> bool:
    counts = np.loadtxt(prefix.with_suffix(".ids"), dtype=int, ndmin=1)
    schools = np.repeat(np.arange(len(counts)), counts)
    poses = np.memmap(prefix.with_suffix(".bin"), dtype="<f4", mode="r").reshape(-1, len(schools), 2, 3)
    if len(poses) != 91 or len(counts) != 40 or len(schools) != 19999:
        return False
    position, forward = poses[:, :, 0], poses[:, :, 1]
    heading = np.arctan2(forward[:, :, 2], forward[:, :, 0])
    turns = np.rad2deg(np.diff(np.unwrap(heading, axis=0), axis=0))
    # A fish first turns one way and then back by more than 12 degrees in each
    # half-second. A gradual change of course does not count as a reversal.
    reversal = (turns[:-1] * turns[1:] < 0) & (np.minimum(abs(turns[:-1]), abs(turns[1:])) > 12)
    occupied = np.zeros((len(poses), len(schools)), dtype=bool)
    observations, peak_pairs = 0, 0
    for t, p in enumerate(position):
        i, j = cKDTree(p).query_pairs(.68, output_type="ndarray").T
        axis = forward[t]
        size = np.linalg.norm(axis, axis=1)
        close = np.linalg.norm(p[i] - p[j], axis=1) < .55 * (size[i] + size[j])
        crossing = np.einsum("ij,ij->i", axis[i], axis[j]) < .45 * size[i] * size[j]
        mask = (schools[i] != schools[j]) & close & crossing
        i, j = i[mask], j[mask]
        occupied[t, i] = occupied[t, j] = True
        encounters = np.minimum(schools[i], schools[j]) * len(counts) + np.maximum(schools[i], schools[j])
        if len(encounters):
            peak_pairs = max(peak_pairs, np.bincount(encounters).max())
        observations += len(encounters)
    # Include neighbours on either side of the turn, even if they leave the
    # distance threshold by the second half of the manoeuvre.
    turnbacks = reversal & (occupied[:-2] | occupied[1:-1] | occupied[2:])
    peak_turnbacks = turnbacks.sum(axis=1).max()
    print(f"crossing_pair_samples={observations} peak_one_shoal_pair={peak_pairs} "
          f"close_fish_turnbacks={turnbacks.sum()} peak_turnbacks_in_one_second={peak_turnbacks}")
    # Keep both streams moving through the naturally occurring crossings.
    boundaries = np.r_[0, np.cumsum(counts)]
    progress = []
    for g in (10, 13, 14, 19, 20, 21):
        centres = position[:, boundaries[g]:boundaries[g+1]].mean(axis=1)
        progress.append(np.linalg.norm(np.diff(centres[:, [0, 2]], axis=0), axis=1).sum())
    print(f"minimum_horizontal_travel_m={min(progress):.2f}")
    return peak_turnbacks <= 3 and observations < 2000 and min(progress) > 2.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", type=Path)
    raise SystemExit(0 if verify(parser.parse_args().prefix) else 1)
