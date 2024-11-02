import argparse
import ast
import json
import os
from pathlib import Path

import pandas as pd

partitions = {"training": "train", "validation": "validation", "test": "test"}


def load(filepath):
    """
    Ported from https://github.com/mdeff/fma/blob/master/utils.py#L183
    """

    filename = os.path.basename(filepath)

    if "features" in filename:
        return pd.read_csv(filepath, index_col=0, header=[0, 1, 2])

    if "echonest" in filename:
        return pd.read_csv(filepath, index_col=0, header=[0, 1, 2])

    if "genres" in filename:
        return pd.read_csv(filepath, index_col=0)

    if "tracks" in filename:
        tracks = pd.read_csv(filepath, index_col=0, header=[0, 1])

        COLUMNS = [
            ("track", "tags"),
            ("album", "tags"),
            ("artist", "tags"),
            ("track", "genres"),
            ("track", "genres_all"),
        ]
        for column in COLUMNS:
            tracks[column] = tracks[column].map(ast.literal_eval)

        COLUMNS = [
            ("track", "date_created"),
            ("track", "date_recorded"),
            ("album", "date_created"),
            ("album", "date_released"),
            ("artist", "date_created"),
            ("artist", "active_year_begin"),
            ("artist", "active_year_end"),
        ]
        for column in COLUMNS:
            tracks[column] = pd.to_datetime(tracks[column])

        SUBSETS = ("small", "medium", "large")
        try:
            tracks["set", "subset"] = tracks["set", "subset"].astype(
                "category", categories=SUBSETS, ordered=True
            )
        except (ValueError, TypeError):
            # the categories and ordered arguments were removed in pandas 0.25
            tracks["set", "subset"] = tracks["set", "subset"].astype(
                pd.CategoricalDtype(categories=SUBSETS, ordered=True)
            )

        COLUMNS = [
            ("track", "genre_top"),
            ("track", "license"),
            ("album", "type"),
            ("album", "information"),
            ("artist", "bio"),
        ]
        for column in COLUMNS:
            tracks[column] = tracks[column].astype("category")

        return tracks


def collect_metadata(tracks: pd.DataFrame):
    ret = dict(train=[], validation=[], test=[])

    tracks = tracks[
        (tracks[("set", "subset")] == "medium") | (tracks[("set", "subset")] == "small")
    ]

    for split in partitions:
        tracks_split = tracks[tracks[("set", "split")] == split]

        tracks_split.reset_index(inplace=True)
        ret[partitions[split]] = tracks_split["track_id"]

    return ret


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--json_path", type=Path, required=True)
    parser.add_argument("--csv_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)

    args = parser.parse_args()

    with open(args.json_path) as f:
        json_data = json.load(f)

    tracks = load(args.csv_path)
    tracks_split = collect_metadata(tracks)

    for partition in ["training", "validation"]:
        split_dict = {}

        fnames = list(tracks_split[partitions[partition]])
        for fname in fnames:
            fname = str(fname).zfill(6)
            if fname in json_data.keys():
                split_dict[fname] = json_data[fname]

        with open(
            args.output_dir / f"fma_noise_{partitions[partition]}.json", "w"
        ) as f:
            json.dump(split_dict, f, indent=2)
