import json
from pathlib import Path

from tqdm import tqdm

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audio_dir",
        type=str,
        required=True,
        help="Path to the directory containing audio files",
    )
    parser.add_argument(
        "--json_file",
        type=str,
        required=True,
        help="Path to the json file containing audio paths and "
        "the corresponding bandwidth inforamtion",
    )
    parser.add_argument(
        "--outfile", type=str, required=True, help="Path to the output json file"
    )
    parser.add_argument(
        "--audio_format", type=str, required=True, help="Path to the output json file"
    )

    args = parser.parse_args()

    audio_paths = {}  # key: filename, value: path
    paths_list = Path(args.audio_dir).rglob(f"*.{args.audio_format}")
    for path in paths_list:
        audio_paths[path.stem] = str(path)

    if Path(args.json_file).suffix == ".json":
        with open(args.json_file, "r") as f:
            data = json.load(f)
    else:
        raise RuntimeError("Give .json file as json_file")

    new_data = {}
    for key in tqdm(data):
        this_data = data[key]
        if key in audio_paths:
            this_data[0] = audio_paths[key]
        else:
            # print(key)
            continue
        new_data[key] = this_data

    with open(args.outfile, "w") as f:
        json.dump(new_data, f, indent=2)
