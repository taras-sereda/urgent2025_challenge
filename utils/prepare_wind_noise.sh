#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
# set -e
set -u
set -o pipefail

if [ ! -e "./simulation/SC-Wind-Noise-Generator" ]; then
    cd ./simulation
    git clone https://github.com/audiolabs/SC-Wind-Noise-Generator.git
    cd SC-Wind-Noise-Generator && pip install -r requirements.txt && cd ../../

    mv simulation/SC-Wind-Noise-Generator/sc_wind_noise_generator.py simulation
fi

python ./simulation/simulate_wind_noise.py \
    --output_dir ./simulation_validation/wind_noise \
    --config ./conf/wind_noise_simulation_validation.yaml