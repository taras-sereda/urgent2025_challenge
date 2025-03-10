# urgent2025_challenge
Official data preparation scripts for the [URGENT 2025 Challenge](https://urgent-challenge.github.io/urgent2025/)

## Notes

❗️❗️ Please note that the default generated `data/speech_train` subset is only intended for **dynamic mixing (on-the-fly simulation)** in the ESPnet framework. It has the same content in `spk1.scp` (clean reference speech) and `wav.scp` (noisy speech) files to facilitate on-the-fly simulation of different distortions. So this subset must be used in conjunction with a dynamic mixing configuration (an unofficial example using dynamic mixing can be found at [here](https://github.com/Emrys365/espnet/blob/urgent2024/egs2/urgent24/enh1/conf/tuning/train_enh_bsrnn_large_noncausal_dynamic_mixing.yaml#L34-L64)).
<!-- 
* To use a fixed simulation training set (without dynamic mixing), you could follow the [commented lines](https://github.com/urgent-challenge/urgent2024_challenge/blob/main/prepare_espnet_data.sh#L188-L210) in the [`prepare_espnet_data.sh`](https://github.com/urgent-challenge/urgent2024_challenge/blob/main/prepare_espnet_data.sh) script to generate `data/train`.
-->

## Requirements

- `>8` Cores
<!-- - At least `1` GPU (4 or 8 GPUs are recommended for speedup in DNSMOS or other DNN-based metric calculation) -->
- At least ?? TB of free disk space for the track 1 and ??? TB for the track 2
  - Speech
    - DNS5 speech (original 131 GB + resampled 187 GB): 318 GB
    - LibriTTS (original 44 GB + resampled 7 GB): 51 GB
    - VCTK: 12 GB
    - WSJ (original sph 24GB + converted 31 GB): 55 GB
    - EARS: ??? GB
    - CommonVoice 19.0 speech (original mp3 ?? GB + resampled ??? GB): ??? GB (??? GB)
    - MLS: ??? GB (???GB)
  - Noise
    - DNS5 noise (original 58 GB + resampled 35 GB): 93 GB
    - WHAM! noise (48 kHz): 76 GB
    - FSD50K: ?? GB
    - FMA: ??GB
  - RIR
    - DNS5 RIRs (48 kHz): 6 GB
  - Others
    - default simulated validation data: ~?? GB

With minimum specs, expects the whole process to take YYY hours.

## Instructions

0. After cloning this repository, run the following command to initialize the submodules:
    ```bash
    git submodule update --init --recursive
    ```

1. Install environmemnt. Python 3.10 and Torch 2.0.1+ are recommended.
   With Conda, just run

    ```bash
    conda env create -f environment.yaml
    conda activate urgent2025
    ```

    > In case of the following error
    > ```
    >   ERROR: Failed building wheel for pypesq
    > ERROR: Could not build wheels for pypesq, which is required to install pyproject.toml-based projects
    > ```
    > you could manually install [`pypesq`](https://github.com/vBaiCai/python-pesq) in advance via: 
    > (make sure you have `numpy` installed before trying this to avoid compilation errors)
    > ```bash
    > python -m pip install https://github.com/vBaiCai/python-pesq/archive/master.zip
    > ```

2. Get the download link of Commonvoice dataset v19.0 from https://commonvoice.mozilla.org/en/datasets

    For German, English, Spanish, French, and Chinese (China), please do the following.

    a. Select `Common Voice Corpus 19.0`

    b. Enter your email and check the two mandatory boxes

    c. Right-click the `Download Dataset Bundle` button and select "Copy link"

    d. Paste the link to [utils/prepare_CommonVoice19_speech.sh](https://github.com/kohei0209/urgnet2025/blob/a2fa5ef53f9ef8eab527a37dcb8aca5aae76ac71/utils/prepare_CommonVoice19_speech.sh#L16-L19)

3. Make a symbolic link to wsj0 and wsj1 data

    a. Make a directory `./wsj`

    b. Make a symbolic link to wsj0 and wsj1 under `./wsj` (`./wsj/wsj0/` and `./wsj/wsj1/`)

<!--
3. Download WSJ0 and WSJ1 datasets from LDC
    > You will need a LDC license to access the data.
    >
    > For URGENT Challenge participants who want to use the data during the challenge period, please contact the organizers for a temporary LDC license.

    a. Download WSJ0 from https://catalog.ldc.upenn.edu/LDC93s6a

    b. Download WSJ1 from https://catalog.ldc.upenn.edu/LDC94S13A

    c. Uncompress and store the downloaded data to the directories `./wsj/wsj0/` and `./wsj/wsj1/`, respectively.
-->

4. FFmpeg-related

    To simulate wind noise and codec artifacts, our scripts utilize FFmpeg.

    a. Activate your python environment

    b. Get the path to FFmpeg by `which ffmpeg`
    
    c. Change `/path/to/ffmpeg` in [simulation/simulate_data_from_param.py](https://github.com/kohei0209/urgnet2025/blob/a2fa5ef53f9ef8eab527a37dcb8aca5aae76ac71/simulation/simulate_data_from_param.py#L19) to the path to your ffmpeg.

5. Run the script

    ```bash
    ./prepare_espnet_data.sh
    ```

    **NOTE**: Please do not change `output_dir` in each shell script called in `prepare_{dataset}.sh`. If you want to download datasets to somewhere else, make a symbolic link to there. 
    ```bash
    # example when you want to download FSD50K noise to /path/to/somewhere
    # prepare_fsd50k_noise.sh specifies ./fsd50k as output_dir, so make a symbolic link from /path/to/somewhere to ./fsd50k
    mkdir -p /path/to/somewhere
    ln -s /path/to/somewhere ./fsd50k
    ```


6. Install eSpeak-NG (used for the phoneme similarity metric computation)
   - Follow the instructions in https://github.com/espeak-ng/espeak-ng/blob/master/docs/guide.md#linux

<!--
## Optional: Prepare webdataset

The script `./utils/prepare_wds.py` can store the audio files in a collection
of tar files each containing a predefined number of audio files. This is useful
to reduce the number of IO operations during training. Please see the
[documentation](https://github.com/webdataset/webdataset) of `webdataset` for
more information.

```bash
OMP_NUM_THREADS=1 python ./utils/prepare_wds.py \
    /path/to/urgent_train_24k_wds \
    --files-per-tar 250 \
    --max-workers 8 \
    --scps data/tmp/commonvoice_11.0_en_resampled_filtered_train.scp \
    data/tmp/dns5_clean_read_speech_resampled_filtered_train.scp \
    data/tmp/vctk_train.scp \
    data/tmp/libritts_resampled_train.scp
```
The script can also resample the whole dataset to a unified sampling frequency
with `--sampling-rate <freq_hz>`. This option will not include samples with
sampling frequency lower than the prescribed frequency.
-->