#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

if [ ! -e "./simulation/sc_wind_noise_generator.py" ]; then
    cd ./simulation
    git clone https://github.com/audiolabs/SC-Wind-Noise-Generator.git
    cd SC-Wind-Noise-Generator && pip install -r requirements.txt && cd ../../

    mv simulation/SC-Wind-Noise-Generator/sc_wind_noise_generator.py simulation
fi

WIND_NOISE_TRAIN_SCP=wind_noise_train.scp
if [ ! -e ${WIND_NOISE_TRAIN_SCP} ]; then
    echo "[Simulate wind noise for training]"
    python ./simulation/simulate_wind_noise.py \
        --output_dir ./simulation_train/wind_noise \
        --config ./conf/wind_noise_simulation_train.yaml
    mv simulation_train/wind_noise/wind_noise.scp $WIND_NOISE_TRAIN_SCP
fi

WIND_NOISE_VALIDATION_SCP=wind_noise_validation.scp
if [ ! -e ${WIND_NOISE_VALIDATION_SCP} ]; then
    echo "[Simulate wind noise for validation]"
    python ./simulation/simulate_wind_noise.py \
        --output_dir ./simulation_validation/wind_noise \
        --config ./conf/wind_noise_simulation_validation.yaml
    mv simulation_validation/wind_noise/wind_noise.scp $WIND_NOISE_VALIDATION_SCP
fi
