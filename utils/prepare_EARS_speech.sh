#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

output_dir="./ears"
mkdir -p "${output_dir}"

echo "=== Preparing EARS data ==="
#################################
# Download data
#################################

echo "Download EARS data"
if [ ! -e "${output_dir}/download_ears.done" ]; then
    seq -w 001 101 | xargs -I {} -P 8 bash -c '
        X="{}"
        output_dir="$1"
        echo "Downloading EARS p${X}.zip"
        curl -s -L https://github.com/facebookresearch/ears_dataset/releases/download/dataset/p${X}.zip -o p${X}.zip
        unzip -q p${X}.zip -d "$output_dir"
        rm p${X}.zip
    ' _ "$output_dir"

    git clone https://github.com/facebookresearch/ears_dataset.git "${output_dir}/ears_scripts"
else
    echo "Skip downloading EARS as it has already finished"
fi
touch "${output_dir}"/download_ears.done



# Note: train/val split follows the paper (train: p001-p099, val: p100-p101)
# https://arxiv.org/abs/2406.06185
echo "[EARS] preparing data files"

# Train data
for x in $(seq 1 99); do
    xx=$(printf "%03d" "$x")
    find "${output_dir}/p$xx" -iname '*.wav'
done | awk -F '/' '{print($(NF-1)"_"$NF" 48000 "$0)}' | sed -e 's/\.wav / /g' | sort -u > ears_train.scp.tmp

# filter some non-speech data
grep -vE '(interjection|melodic|nonverbal|vegetative)' ears_train.scp.tmp > ears_train.scp
rm ears_train.scp.tmp

# utt2spk
awk '{split($1, arr, "_"); print($1" ears_"arr[1])}' ears_train.scp > ears_train.utt2spk

# transcription
python utils/get_ears_transcript.py \
    --audio_scp ears_train.scp \
    --transcript_json_path "${output_dir}/ears_scripts/transcripts.json" \
    --outfile ears_train.text


# Validation data
for x in $(seq 100 101); do
    xx=$(printf "%03d" "$x")
    find "${output_dir}/p$xx" -iname '*.wav'
done | awk -F '/' '{print($(NF-1)"_"$NF" 48000 "$0)}' | sed -e 's/\.wav / /g' | sort -u > ears_validation.scp.tmp

# filter some non-speech data, following the original paper
grep -vE '(interjection|melodic|nonverbal|vegetative)' ears_validation.scp.tmp > ears_validation.scp
rm ears_validation.scp.tmp

# utt2spk
awk '{split($1, arr, "_"); print($1" ears_"arr[1])}' ears_validation.scp > ears_validation.utt2spk

# transcription
python utils/get_ears_transcript.py \
    --audio_scp ears_validation.scp \
    --transcript_json_path "${output_dir}/ears_scripts/transcripts.json" \
    --outfile ears_validation.text

#--------------------------------
# Output file:
# -------------------------------
# ears_train.scp
#    - scp file for training
# ears_train.utt2spk
#    - speaker mapping for training samples
# ears_train.text
#    - transcripts for training samples
# ears_validation.scp
#    - scp file for validation
# ears_validation.utt2spk
#    - speaker mapping for filtered validation samples
# ears_validation.text
#    - transcripts for validation samples
