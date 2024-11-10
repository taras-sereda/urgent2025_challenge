#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

output_dir="./fma"
mkdir -p "${output_dir}"

echo "=== Preparing FMA data ==="
#################################
# Download data
#################################
# Refer to https://github.com/mdeff/fma
echo "Download FMA data"

if [ ! -e "${output_dir}/download_fma.done" ]; then
    wget -c -P ${output_dir}  https://os.unil.cloud.switch.ch/fma/fma_metadata.zip
    7z x "${output_dir}/fma_metadata.zip" -o"${output_dir}"

    wget -c -P ${output_dir} https://os.unil.cloud.switch.ch/fma/fma_medium.zip
    echo "c67b69ea232021025fca9231fc1c7c1a063ab50b  ${output_dir}/fma_medium.zip"   | sha1sum -c -
    7z x "${output_dir}/fma_medium.zip" -o"${output_dir}"

    rm "${output_dir}/fma_medium.zip" "${output_dir}/fma_metadata.zip"
else
    echo "Skip downloading FMA as it has already finished"
fi
touch "${output_dir}"/download_fma.done


#################################
# Data preprocessing
#################################

echo "FMA preparing data files"

mkdir -p tmp

BW_EST_FILE=tmp/fma_noise.json
BW_EST_FILE_JSON_GZ="datafiles/fma/fma_noise.json.gz"
if [ -f ${BW_EST_FILE} ]; then
    gunzip -c $BW_EST_FILE_JSON_GZ > $BW_EST_FILE
fi
if [ ! -f ${BW_EST_FILE} ]; then
    echo "[FMA noise] estimating audio bandwidth"
    OMP_NUM_THREADS=1 python utils/estimate_audio_bandwidth.py \
        --audio_dir ${output_dir}/fma_medium \
        --audio_format mp3 \
        --chunksize 1000 \
        --nj 8 \
        --outfile "${BW_EST_FILE}"
else
    echo "Estimated bandwidth file already exists. Delete ${BW_EST_FILE} if you want to re-estimate."
fi

BW_EST_FILE_TRAIN=tmp/fma_noise_train.json
BW_EST_FILE_VALID=tmp/fma_noise_validation.json
if [[ ! -f ${BW_EST_FILE_TRAIN} || ! -f ${BW_EST_FILE_VALID} ]]; then
    echo "[FMA noise] split training and validation data"
    python utils/get_fma_subset_split.py \
            --json_path "${BW_EST_FILE}" \
            --csv_path "${output_dir}/fma_metadata/tracks.csv" \
            --output_dir ./tmp
else
    echo "Train/validation data are already split. Delete ${BW_EST_FILE_TRAIN} and/or ${BW_EST_FILE_VALID} if you want to run again."
fi

RESAMP_SCP_FILE_TRAIN=fma_noise_resampled_train.scp
if [ ! -f ${RESAMP_SCP_FILE_TRAIN} ]; then
    echo "[FMA noise] resampling to estimated audio bandwidth"
    OMP_NUM_THREADS=1 python utils/resample_to_estimated_bandwidth.py \
        --bandwidth_data "${BW_EST_FILE_TRAIN}" \
        --out_scpfile "${RESAMP_SCP_FILE_TRAIN}" \
        --outdir "${output_dir}/resampled/fma_medium" \
        --nj 8 \
        --chunksize 1000
    # add dataset name to make utt-ids unique
    awk -v additional="fma_" '{print additional $1, $2, $3}' $RESAMP_SCP_FILE_TRAIN > ./temp && mv ./temp $RESAMP_SCP_FILE_TRAIN
else
    echo "Resampled scp file already exists. Delete ${RESAMP_SCP_FILE_TRAIN} if you want to re-resample."
fi

RESAMP_SCP_FILE_VALID=fma_noise_resampled_validation.scp
if [ ! -f ${RESAMP_SCP_FILE_VALID} ]; then
    echo "[FMA noise] resampling to estimated audio bandwidth"
    OMP_NUM_THREADS=1 python utils/resample_to_estimated_bandwidth.py \
        --bandwidth_data "${BW_EST_FILE_VALID}" \
        --out_scpfile "${RESAMP_SCP_FILE_VALID}" \
        --outdir "${output_dir}/resampled/fma_medium" \
        --nj 8 \
        --chunksize 1000
    # add dataset name to make utt-ids unique
    awk -v additional="fma_" '{print additional $1, $2, $3}' $RESAMP_SCP_FILE_VALID > ./temp && mv ./temp $RESAMP_SCP_FILE_VALID
else
    echo "Resampled scp file already exists. Delete ${RESAMP_SCP_FILE_VALID} if you want to re-resample."
fi

#--------------------------------
# Output file:
# -------------------------------
# fma_noise_resampled_train.scp
#    - scp file containing resampled noise samples for training
# fma_noise_resampled_validation.scp
#    - scp file containing resampled noise samples for validation