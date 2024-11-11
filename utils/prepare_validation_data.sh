#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

export PATH=$PATH:$PWD/utils
output_dir="./data"

scp_output_dir=${output_dir}/tmp/speech_validation_subset
mkdir -p $scp_output_dir
mkdir -p simulation_validation/log

echo ["Prepare validation set"]

# randomly select speech data
python ./utils/extract_random_subset.py \
    --config ./conf/validation_data_selection.yaml \
    --outfile ${scp_output_dir}/speech_validation_subset.scp
sort -k1 ${scp_output_dir}/speech_validation_subset.scp -o ${scp_output_dir}/speech_validation_subset.scp

# concatenate files and filter them    
ls data/tmp/*validation.utt2spk | grep -v "noise" | grep -v "11.0" | xargs cat > ${scp_output_dir}/speech_validation_subset.utt2spk.tmp
utils/filter_scp.pl ${scp_output_dir}/speech_validation_subset.scp ${scp_output_dir}/speech_validation_subset.utt2spk.tmp > ${scp_output_dir}/speech_validation_subset.utt2spk
sort -k1 ${scp_output_dir}/speech_validation_subset.utt2spk -o ${scp_output_dir}/speech_validation_subset.utt2spk
rm ${scp_output_dir}/speech_validation_subset.utt2spk.tmp
ls data/tmp/*validation.text | grep -v "noise" | grep -v "11.0" | xargs cat > ${scp_output_dir}/speech_validation_subset.text.tmp
utils/filter_scp.pl ${scp_output_dir}/speech_validation_subset.scp ${scp_output_dir}/speech_validation_subset.text.tmp > ${scp_output_dir}/speech_validation_subset.text
sort -k1 ${scp_output_dir}/speech_validation_subset.text -o ${scp_output_dir}/speech_validation_subset.text
rm ${scp_output_dir}/speech_validation_subset.text.tmp

# generate simulation parameters
if [ ! -f "simulation_validation/log/meta.tsv" ]; then
    python simulation/generate_data_param.py --config conf/simulation_validation.yaml
fi

# simulate noisy speech for validation
# It takes ~30 minutes to finish simulation with nj=8
OMP_NUM_THREADS=1 python simulation/simulate_data_from_param.py \
    --config conf/simulation_validation.yaml \
    --meta_tsv simulation_validation/log/meta.tsv \
    --nj 8 \
    --chunksize 100
