import json
import pickle
from pathlib import Path

import soundfile as sf
from tqdm.contrib.concurrent import process_map


def estimate_bandwidth(audios):
    uid, audio_path = audios

    try:
        audio, fs = sf.read(audio_path)
    except:
        # Some of the downloaded DNS5 speech audio files may be broken (extracted from
        # dns5_fullband/Track1_Headset/read_speech.tgz.part*) according to our tests.
        print(f"Error: cannot open audio file '{audio_path}'. Skipping it", flush=True)
        return

    audio_path = audio_path.resolve()
    audio_path2 = Path(str(audio_path).replace("segment", "segment_sf")).resolve()

    try:
        audio2, fs = sf.read(audio_path2)
    except:
        # Some of the downloaded DNS5 speech audio files may be broken (extracted from
        # dns5_fullband/Track1_Headset/read_speech.tgz.part*) according to our tests.
        print(f"Error: cannot open audio file '{audio_path}'. Skipping it", flush=True)
        return

    if audio.shape[-1] == audio2.shape[-1]:
        abs_ = abs(audio - audio2).sum()
        if abs_ > 1.0:
            print(abs_, audio_path, audio_path2, flush=True)
    else:
        abs_ = 0.0
    return abs_


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audio_dir",
        type=str,
        required=True,
        nargs="+",
        help="Path to the directory containing audios or "
        "path to the wav.scp file containing paths to audios",
    )
    parser.add_argument(
        "--audio_format", type=str, default="wav", help="Suffix of the audio files"
    )
    parser.add_argument("--nj", type=int, default=8, help="Number of parallel workers")
    parser.add_argument(
        "--chunksize", type=int, default=1000, help="Chunk size for each worker"
    )
    args = parser.parse_args()

    all_audios = []
    for audio_dir in args.audio_dir:
        if Path(audio_dir).is_dir():
            audios = list(Path(audio_dir).rglob("*." + args.audio_format))
            audios = list(zip([p.stem for p in audios], audios))
        elif Path(audio_dir).is_file() and Path(audio_dir).suffix == ".scp":
            audios = []
            with open(audio_dir, "r") as f:
                for line in f:
                    uid, path = line.strip().split(maxsplit=1)
                    audios.append((uid, path))
        elif Path(audio_dir).is_file() and Path(audio_dir).suffix == ".json":
            audios = []
            with open(audio_dir, "r") as f:
                for uid, dic in json.load(f).items():
                    audios.append((uid, dic))
        else:
            raise ValueError(f"Invalid format: {audio_dir}")
        all_audios.extend(audios)

        ret0 = process_map(
            estimate_bandwidth,
            audios,
            chunksize=args.chunksize,
            max_workers=args.nj,
        )
