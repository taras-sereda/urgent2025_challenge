import soundfile as sf
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from pydub import AudioSegment


def ensure_dir(directory):
    directory.mkdir(parents=True, exist_ok=True)


def sec_to_sample(seconds, sample_rate):
    return int(float(seconds) * sample_rate)


def sec_to_ms(seconds):
    return int(float(seconds) * 1000)


def process_audio(audio, sample_rate, ids, start, end, output_dir):
    # stereo -> monaural
    audio = audio[:, 0]

    start_sample = sec_to_sample(start, sample_rate)
    end_sample = sec_to_sample(end, sample_rate)

    segment = audio[start_sample:end_sample]

    ids_split = ids.split("_")
    output_subdir = output_dir / ids_split[0] / ids_split[1]
    output_filename = f"{ids}.flac"
    output_path = output_subdir / output_filename

    ensure_dir(output_subdir)

    sf.write(output_path, segment, sample_rate)


# Function to trim and save the audio segment
def process_audiosegment(audio, sample_rate, ids, start, end, output_dir):
    # If the audio has multiple channels, extract the first channel to make it mono
    if audio.channels > 1:
        audio = audio.split_to_mono()[0]  # Get the first channel

    # Convert start and end times to milliseconds
    start_ms = sec_to_ms(start)
    end_ms = sec_to_ms(end)

    # Trim the audio to the specified segment
    segment = audio[start_ms:end_ms]

    # Split the id by "_" and create the output path
    ids_split = ids.split("_")
    output_subdir = output_dir / ids_split[0] / ids_split[1]
    output_filename = f"{ids}.flac"
    output_path = output_subdir / output_filename

    ensure_dir(output_subdir)

    # Export the trimmed audio as FLAC
    segment.export(output_path, format="flac")


def process_line(line, output_dir):
    # parts = line.strip().split()
    parts = line

    path = parts[0]
    # print(path, flush=True)
    audio, sample_rate = sf.read(path, always_2d=True)

    # Load the audio file
    # audio = AudioSegment.from_file(path)
    # sample_rate = audio.frame_rate

    # 各id, start, end のペアを処理
    for i in range(1, len(parts), 3):
        id = parts[i]
        start = parts[i + 1]
        end = parts[i + 2]

        # process_audiosegment(audio, sample_rate, id, start, end, output_dir)
        process_audio(audio, sample_rate, id, start, end, output_dir)


def main(args):
    # audio_path_list = list(args.input_dir.iterdir())
    audio_path_list = list(Path(args.input_dir).rglob("*.mp3"))
    audio_path_dict = {}
    for path in audio_path_list:
        key = path.name
        audio_path_dict[key] = str(path)

    with open(args.segment_file, "r") as file:
        lines = file.readlines()

    nonexisting_data_idx = []
    for i in range(len(lines)):
        parts = lines[i].strip().split()
        # audio_path = [p for p in audio_path_list if parts[0] == p.name]
        # assert len(audio_path) == 1
        # audio_path = audio_path[0]

        # some data could not be downloaded and not included in audio_path_dict
        if parts[0] in audio_path_dict:
            audio_path = audio_path_dict[parts[0]]
            parts[0] = audio_path
            lines[i] = parts
        else:
            nonexisting_data_idx.append(i)

    for idx in nonexisting_data_idx[::-1]:
        del lines[idx]

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        executor.map(process_line, lines, [args.output_dir] * len(lines))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_dir",
        type=Path,
        required=True,
        help="",
    )

    parser.add_argument(
        "--segment_file",
        type=Path,
        required=True,
        help="",
    )

    parser.add_argument(
        "--output_dir",
        type=Path,
        required=True,
        help="",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="",
    )

    args = parser.parse_args()

    main(args)
