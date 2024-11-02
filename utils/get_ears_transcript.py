from pathlib import Path
import json


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audio_scp",
        type=str,
        required=True,
        help="Path to the scp file containing VCTK audio IDs in the first column",
    )
    parser.add_argument(
        "--transcript_json_path",
        type=str,
        required=True,
        help="Path to the root directory of the VCTK corpus",
    )
    parser.add_argument(
        "--outfile",
        type=str,
        required=True,
        help="Path to the output text file for writing transcripts for all samples",
    )
    args = parser.parse_args()

    with open(args.transcript_json_path, "r") as f:
        transcripts = json.load(f)

    outdir = Path(args.outfile).parent
    outdir.mkdir(parents=True, exist_ok=True)
    with open(args.outfile, "w") as out:
        with open(args.audio_scp, "r") as f:
            for line in f:
                # e.g., uid=p001_rainbow_07_loud
                uid, _ = line.strip().split(maxsplit=1)
                # remove spkID
                id_ = uid.split("_", 1)[-1]

                # transcripts are available only for subsets
                if id_ in transcripts:
                    transcript = transcripts[id_]
                else:
                    transcript = "<not-available>"

                out.write(f"{uid} {transcript}\n")
