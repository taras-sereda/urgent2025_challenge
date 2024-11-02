#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
# set -e
set -u
set -o pipefail

output_dir="./fsd50k"
mkdir -p "${output_dir}"

echo "=== Preparing FSD50K data ==="
#################################
# Download data
#################################
echo "Download FSD50K data"

if [ ! -e "${output_dir}/download_fsd50k.done" ]; then
    org_dir=${PWD}
    cd ${output_dir}

    # download meta data
    wget -O FSD50K.ground_truth.zip https://zenodo.org/records/4060432/files/FSD50K.ground_truth.zip?download=1 && unzip FSD50K.ground_truth.zip
    wget -O FSD50K.metadata.zip https://zenodo.org/records/4060432/files/FSD50K.metadata.zip?download=1 && unzip FSD50K.metadata.zip
    wget -O FSD50K.doc.zip https://zenodo.org/records/4060432/files/FSD50K.doc.zip?download=1 && unzip FSD50K.doc.zip
    
    # download audio data
    wget -O FSD50K.dev_audio.zip https://zenodo.org/records/4060432/files/FSD50K.dev_audio.zip?download=1
    seq -w 1 5 | xargs -I {} -P 5 bash -c '
        ii="{}"
        wget -O FSD50K.dev_audio.z0${ii} https://zenodo.org/records/4060432/files/FSD50K.dev_audio.z0${ii}?download=1
    '

    # uncompress the zip file
    zip -s 0 FSD50K.dev_audio.zip --out unsplit.zip && unzip unsplit.zip

    # delete zip files
    rm FSD50K.metadata.zip FSD50K.ground_truth.zip FSD50K.doc.zip unsplit.zip FSD50K.dev_audio.z??

    cd ${org_dir}

    # downaload AudioSet ontology"
    git clone https://github.com/audioset/ontology.git "${output_dir}/ontology"
else
    echo "Skip downloading FSD50K as it has already finished"
fi
touch "${output_dir}"/download_fsd50k.done

echo "FSD50K preparing data files"

#################################
# Data preprocessing
#################################
mkdir -p tmp

# NØTE: three files are removed here. They are silent files.
BW_EST_FILE=tmp/fsd50k_noise.json
if [ ! -f ${BW_EST_FILE} ]; then
    echo "[FSD50K noise] estimating audio bandwidth"
    OMP_NUM_THREADS=1 python utils/estimate_audio_bandwidth.py \
        --audio_dir ${output_dir}/FSD50K.dev_audio \
        --audio_format wav \
        --chunksize 1000 \
        --nj 8 \
        --outfile "${BW_EST_FILE}"

else
    echo "Estimated bandwidth file already exists. Delete ${BW_EST_FILE} if you want to re-estimate."
fi

BW_EST_FILE_TRAIN=tmp/fsd50k_noise_train.json
BW_EST_FILE_VALID=tmp/fsd50k_noise_validation.json
if [[ ! -f ${BW_EST_FILE_TRAIN} || ! -f ${BW_EST_FILE_VALID} ]]; then
    echo "[FSD50K noise] filter human voice and split training and validation data."
    python utils/filter_fsd50k_human_voice.py \
            --json_path "${BW_EST_FILE}" \
            --csv_path "${output_dir}/FSD50K.ground_truth/dev.csv" \
            --ontology_path "${output_dir}/ontology/ontology.json" \
            --output_dir ./tmp
else
    echo "Human voices are already filtered. Delete ${BW_EST_FILE_TRAIN} and/or ${BW_EST_FILE_VALID} if you want to re-estimate."
fi


RESAMP_SCP_FILE_TRAIN=tmp/fsd50k_noise_resampled_train.scp
if [ ! -f ${RESAMP_SCP_FILE_TRAIN} ]; then
    echo "[FSD50K-train noise] resampling to estimated audio bandwidth"
    OMP_NUM_THREADS=1 python utils/resample_to_estimated_bandwidth.py \
        --bandwidth_data "${BW_EST_FILE_TRAIN}" \
        --out_scpfile "${RESAMP_SCP_FILE_TRAIN}" \
        --outdir "${output_dir}/resampled/FSD50K.dev_audio" \
        --nj 8 \
        --chunksize 1000
else
    echo "Resampled scp file already exists. Delete ${RESAMP_SCP_FILE_TRAIN} if you want to re-resample."
fi


RESAMP_SCP_FILE_VALID=tmp/fsd50k_noise_resampled_validation.scp
if [ ! -f ${RESAMP_SCP_FILE_VALID} ]; then
    echo "[FSD50K-validation noise] resampling to estimated audio bandwidth"
    OMP_NUM_THREADS=1 python utils/resample_to_estimated_bandwidth.py \
        --bandwidth_data "${BW_EST_FILE_VALID}" \
        --out_scpfile "${RESAMP_SCP_FILE_VALID}" \
        --outdir "${output_dir}/resampled/FSD50K.dev_audio" \
        --nj 8 \
        --chunksize 1000
else
    echo "Resampled scp file already exists. Delete ${RESAMP_SCP_FILE_VALID} if you want to re-resample."
fi



#--------------------------------
# Output file:
# -------------------------------
# fsd50k_noise_resampled_train.scp
#    - scp file containing resampled noise samples for training
# fsd50k_noise_resampled_validation.scp
#    - scp file containing resampled noise samples for validation
