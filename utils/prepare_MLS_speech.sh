#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

track=$1  # track1 or track2

output_dir="./mls_segments"  # please do not change output_dir
mkdir -p "${output_dir}"

if [ $track == "track1" ]; then
    # we do not include MLS English data in the track1
    langs=("german" "french" "spanish")
else
    langs=("german" "french" "spanish" "english")
fi

echo "=== Preparing MLS data for ${track} ==="

for lang in "${langs[@]}"; do
    for split in train dev; do
        echo "=== Preparing MLS ${lang} ${split} data ==="

        if [ $split == "train" ]; then
            split_track="${split}_${track}"
            split_name=$split_track
        else
            split_track=$split
            split_name=validation
        fi

        output_dir_lang="${output_dir}/${lang}/${split_track}"
        mkdir -p "${output_dir_lang}/audio"
        if [ ! -f "${output_dir}/download_mls_${lang}_${split_track}.done" ]; then
            echo "[MLS-${lang}-${split_track}] downloading data"
            # download data from huggingface
            filelist=./datafiles/mls/mls_${lang}_${split_track}_data.txt
            if [ $split_name == "train_track1" ]; then
                cat $filelist | xargs -P 8 -n 1 -I {} sh -c '
                    filename=$(echo "{}" | sed -E "s|.*/([0-9]+)/([0-9]+\.tar\.gz)$|\1_\2|")
                    wget -q -c "https://huggingface.co/datasets/kohei0209/mls_hq_urgent_track1/resolve/main/{}?download=true" -O "$0/${filename}"
                ' "$output_dir_lang" {}
            else
                cat $filelist | xargs -P 8 -n 1 -I {} sh -c '
                    filename=$(echo "{}" | sed -E "s|.*/([0-9]+)/([0-9]+\.tar\.gz)$|\1_\2|")
                    wget -q -c "https://huggingface.co/datasets/kohei0209/mls_hq/resolve/main/data/{}?download=true" -O "$0/${filename}"
                ' "$output_dir_lang" {}
            fi
            # untar
            find "${output_dir_lang}" -name "*.tar.gz" | xargs -P 8 -n 1 -I {} sh -c '
                tar -xzf {} -C "$0/audio"
            ' "$output_dir_lang" {}

            touch "${output_dir}/download_mls_${lang}_${split_track}.done"
        fi

        BW_EST_FILE="tmp/mls_${lang}_${split_track}.json"
        if [ ! -f ${BW_EST_FILE} ]; then
            # .json.gz file containing bandwidth information for the 1st-track data is provided
            BW_EST_FILE_JSON_GZ="./datafiles/mls/mls_${lang}_${split_track}.json.gz"
            gunzip -c $BW_EST_FILE_JSON_GZ > $BW_EST_FILE
        else
            echo "Estimated bandwidth file already exists ${BW_EST_FILE}."
        fi

        RESAMP_SCP_FILE=tmp/mls_${lang}_resampled_${split_track}.scp
        if [ ! -f ${RESAMP_SCP_FILE} ]; then
            echo "[MLS-${lang}-${split_track}] resampling to estimated audio bandwidth"
            OMP_NUM_THREADS=1 python utils/resample_to_estimated_bandwidth.py \
            --bandwidth_data ${BW_EST_FILE} \
            --out_scpfile ${RESAMP_SCP_FILE} \
            --outdir "${output_dir_lang}/resampled/${split_track}" \
            --max_files 1000 \
            --nj 8 \
            --chunksize 1000
        else
            echo "Resampled scp file already exists. Delete ${RESAMP_SCP_FILE} if you want to re-resample."
        fi

        echo "[MLS-${lang}-${split_track}] preparing data files"
        transcript_file_path=./mls/${lang}/${split}/transcripts.txt

        # organize the scp file
        FINAL_SCP_FILE=mls_${lang}_resampled_${split_name}.scp
        sort -k1 $RESAMP_SCP_FILE -o $FINAL_SCP_FILE
        utils/filter_scp.pl $FINAL_SCP_FILE $transcript_file_path > mls_${lang}_resampled_${split_name}.text
        awk '{split($1, arr, "_"); print($1" "arr[1])}' $FINAL_SCP_FILE > mls_${lang}_resampled_${split_name}.utt2spk

        # add language name to make utt-ids unique
        awk -v additional="mls_${lang}_" '{print additional $1, $2, $3}' $FINAL_SCP_FILE > ./temp && mv ./temp $FINAL_SCP_FILE
        awk -v additional="mls_${lang}_" '{print additional $1, substr($0, index($0,$2))}' mls_${lang}_resampled_${split_name}.text > ./temp && mv ./temp mls_${lang}_resampled_${split_name}.text
        awk -v additional="mls_${lang}_" '{print additional $1, $2, $3}' mls_${lang}_resampled_${split_name}.utt2spk > ./temp && mv ./temp mls_${lang}_resampled_${split_name}.utt2spk
    done
done


#--------------------------------
# Output file (for each ${lang} and ${track}):
# -------------------------------
# mls_${lang}_resampled_train_${track}.scp
#    - scp file containing samples (after resampling) for training
# mls_${lang}_resampled_train_${track}.utt2spk
#    - speaker mapping for training samples
# mls_${lang}_resampled_train_${track}.text
#    - transcript for training samples
# mls_${lang}_resampled_validation.scp
#    - scp file containing samples (after resampling) for validation
# mls_${lang}_resampled_validation.utt2spk
#    - speaker mapping for validation samples
# mls_${lang}_resampled_validation.text
#    - transcript for validation samples
