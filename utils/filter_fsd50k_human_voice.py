import argparse
import json
from pathlib import Path

import pandas as pd


def remove_speech(df, ontology):

    speech_ancestors = [
        "/m/09l8g",
        "/m/09hlz4",
        "/t/dd00012",
    ]  # Human Voice, Respiratory sounds, Human group actions

    def collect_all_child_ids(ids, ontology):
        result = []

        def recursive_collect(current_id):
            if current_id in ontology:
                children = ontology[current_id]["child_ids"]
                result.extend(children)
                for child in children:
                    recursive_collect(child)

        for id in ids:
            recursive_collect(id)
        return result

    speech_children = collect_all_child_ids(speech_ancestors, ontology)
    # speech_names = [ontology[mid]["name"] for mid in speech_children]
    # print(speech_names)

    def filter_with_id(row):
        mids = row["mids"].split(",")
        for mid in mids:
            if mid in speech_children:
                return True
        return False

    df = df[~df.apply(filter_with_id, axis=1)]
    print(f"Number of samples without speech: {len(df)}")
    return df


def split_train_val(df_one_label):
    df_train = df_one_label[df_one_label["split"] == "train"]
    df_valid = df_one_label[df_one_label["split"] == "val"]
    return df_train, df_valid


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", type=Path, required=True)
    parser.add_argument("--csv_path", type=Path, required=True)
    parser.add_argument("--ontology_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    args = parser.parse_args()

    # read csv
    df = pd.read_csv(args.csv_path)

    # read ontology
    with open(args.ontology_path) as f:
        ontology = json.load(f)
    ontology = {d["id"]: d for d in ontology}

    # remove speech samples
    df = remove_speech(df, ontology)

    # TODO: write a scp file after removing speech
    df_train, df_valid = split_train_val(df)

    # read json file
    with open(args.json_path, "r") as f:
        json_data = json.load(f)

    train_fname = list(df_train["fname"])
    train_json = {}
    for fname in train_fname:
        if str(fname) in json_data.keys():
            train_json[str(fname)] = json_data[str(fname)]

    with open(args.output_dir / "fsd50k_noise_train.json", "w") as f:
        json.dump(train_json, f, indent=2)

    valid_fname = list(df_valid["fname"])
    valid_json = {}
    for fname in valid_fname:
        if str(fname) in json_data.keys():
            valid_json[str(fname)] = json_data[str(fname)]

    with open(args.output_dir / "fsd50k_noise_validation.json", "w") as f:
        json.dump(valid_json, f, indent=2)
