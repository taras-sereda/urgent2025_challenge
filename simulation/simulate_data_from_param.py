import re
from functools import partial
from pathlib import Path
import subprocess
import ast
from copy import deepcopy

import librosa
import numpy as np
import scipy
import soundfile as sf
from tqdm.contrib.concurrent import process_map

from espnet2.train.preprocessor import detect_non_silence

from generate_data_param2 import get_parser
from rir_utils import estimate_early_rir

from pedalboard import (
    Bitcrush,
    Clipping,
    Convolution,
    Delay,
    Distortion,
    Gain,
    GSMFullRateCompressor,
    HighpassFilter,
    HighShelfFilter,
    IIRFilter,
    Invert,
    LowpassFilter,
    LowShelfFilter,
    MP3Compressor,
    NoiseGate,
    PeakFilter,
    Pedalboard,
    Phaser,
    PitchShift,
    Resample,
)

ffmpeg = "/home/saijo/anaconda3/envs/urgent/bin/ffmpeg"


def buildFFmpegCommand(params):

    filter_commands = ""
    filter_commands += "[1:a]asplit=2[sc][mix];"
    filter_commands += (
        "[0:a][sc]sidechaincompress="
        + f"threshold={params['threshold']}:"
        + f"ratio={params['ratio']}:"
        + f"level_sc={params['sc_gain']}"
        + f":release={params['release']}"
        + f":attack={params['attack']}"
        + "[compr];"
    )
    filter_commands += "[compr][mix]amix"

    commands_list = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "quiet",
        "-i",
        params["speech_path"],
        "-i",
        params["noise_path"],
        "-filter_complex",
        filter_commands,
        params["output_path"],
    ]

    # return (" ").join(commands_list)
    return commands_list


#############################
# Augmentations per sample
#############################
def mix_noise(speech_sample, noise_sample, snr=5.0, rng=None):
    """Mix the speech sample with an additive noise sample at a given SNR.

    Args:
        speech_sample (np.ndarray): a single speech sample (Channel, Time)
        noise_sample (np.ndarray): a single noise sample (Channel, Time)
        snr (float): signal-to-nosie ratio (SNR) in dB
        rng (np.random.Generator): random number generator
    Returns:
        noisy_sample (np.ndarray): output noisy sample (Channel, Time)
        noise (np.ndarray): scaled noise sample (Channel, Time)
    """
    len_speech = speech_sample.shape[-1]
    len_noise = noise_sample.shape[-1]
    if len_noise < len_speech:
        offset = rng.integers(0, len_speech - len_noise)
        # Repeat noise
        noise_sample = np.pad(
            noise_sample,
            [(0, 0), (offset, len_speech - len_noise - offset)],
            mode="wrap",
        )
    elif len_noise > len_speech:
        offset = rng.integers(0, len_noise - len_speech)
        noise_sample = noise_sample[:, offset : offset + len_speech]

    power_speech = (speech_sample[detect_non_silence(speech_sample)] ** 2).mean()
    power_noise = (noise_sample[detect_non_silence(noise_sample)] ** 2).mean()
    scale = 10 ** (-snr / 20) * np.sqrt(power_speech) / np.sqrt(max(power_noise, 1e-10))
    noise = scale * noise_sample
    noisy_speech = speech_sample + noise
    return noisy_speech, noise


def wind_noise(
    speech_sample,
    noise_sample,
    fs,
    uid,
    threshold,
    ratio,
    attack,
    release,
    sc_gain,
    clipping,
    clipping_threshold,
    snr,
    rng=None,
):
    len_speech = speech_sample.shape[-1]
    len_noise = noise_sample.shape[-1]
    if len_noise < len_speech:
        offset = rng.integers(0, len_speech - len_noise)
        # Repeat noise
        noise_sample = np.pad(
            noise_sample,
            [(0, 0), (offset, len_speech - len_noise - offset)],
            mode="wrap",
        )
    elif len_noise > len_speech:
        offset = rng.integers(0, len_noise - len_speech)
        noise_sample = noise_sample[:, offset : offset + len_speech]

    power_speech = (speech_sample[detect_non_silence(speech_sample)] ** 2).mean()
    power_noise = (noise_sample[detect_non_silence(noise_sample)] ** 2).mean()
    scale = 10 ** (-snr / 20) * np.sqrt(power_speech) / np.sqrt(max(power_noise, 1e-10))
    noise = scale * noise_sample

    # to use ffmpeg for simulation, speech and noise have to be saved once
    tmp_dir = Path("./simulation_tmp")
    tmp_dir.mkdir(exist_ok=True)
    speech_tmp_path = tmp_dir / f"speech_{uid}.wav"
    noise_tmp_path = tmp_dir / f"noise_{uid}.wav"
    mix_tmp_path = tmp_dir / f"mix_{uid}.wav"

    scale = 0.9 / max(
        np.max(np.abs(speech_sample)),
        np.max(np.abs(noise)),
    )
    speech_sample *= scale
    noise *= scale

    save_audio(speech_sample, speech_tmp_path, fs)
    save_audio(noise, noise_tmp_path, fs)

    commands = buildFFmpegCommand(
        {
            "speech_path": speech_tmp_path,
            "noise_path": noise_tmp_path,
            "output_path": mix_tmp_path,
            "threshold": threshold,
            "ratio": ratio,
            "attack": attack,
            "release": release,
            "sc_gain": sc_gain,
        }
    )

    if subprocess.run(commands).returncode != 0:
        print("There was an error running your FFmpeg script")

    # Clipper
    mix, sr = sf.read(mix_tmp_path)
    noise, sr = sf.read(noise_tmp_path)

    mix /= scale
    noise /= scale

    if clipping:
        mix = np.maximum(clipping_threshold * np.min(mix) * np.ones_like(mix), mix)
        mix = np.minimum(clipping_threshold * np.max(mix) * np.ones_like(mix), mix)

    return mix[None], noise[None]


def add_reverberation(speech_sample, rir_sample):
    """Mix the speech sample with an additive noise sample at a given SNR.

    Args:
        speech_sample (np.ndarray): a single speech sample (1, Time)
        rir_sample (np.ndarray): a single room impulse response (RIR) (Channel, Time)
    Returns:
        reverberant_sample (np.ndarray): output noisy sample (Channel, Time)
    """
    reverberant_sample = scipy.signal.convolve(speech_sample, rir_sample, mode="full")
    return reverberant_sample[:, : speech_sample.shape[1]]


def bandwidth_limitation(speech_sample, fs: int, fs_new: int, res_type="kaiser_best"):
    """Apply the bandwidth limitation distortion to the input signal.

    Args:
        speech_sample (np.ndarray): a single speech sample (1, Time)
        fs (int): sampling rate in Hz
        fs_new (int): effective sampling rate in Hz
        res_type (str): resampling method

    Returns:
        ret (np.ndarray): bandwidth-limited speech sample (1, Time)
    """
    opts = {"res_type": res_type}
    if fs == fs_new:
        return speech_sample
    assert fs > fs_new, (fs, fs_new)
    ret = librosa.resample(speech_sample, orig_sr=fs, target_sr=fs_new, **opts)
    # resample back to the original sampling rate
    ret = librosa.resample(ret, orig_sr=fs_new, target_sr=fs, **opts)
    return ret[:, : speech_sample.shape[1]]


def clipping(speech_sample, min_quantile: float = 0.0, max_quantile: float = 0.9):
    """Apply the clipping distortion to the input signal.

    Args:
        speech_sample (np.ndarray): a single speech sample (1, Time)
        min_quantile (float): lower bound on the quantile of samples to be clipped
        max_quantile (float): upper bound on the quantile of samples to be clipped

    Returns:
        ret (np.ndarray): clipped speech sample (1, Time)
    """
    q = np.array([min_quantile, max_quantile])
    min_, max_ = np.quantile(speech_sample, q, axis=-1, keepdims=False)
    # per-channel clipping
    ret = np.stack(
        [
            np.clip(speech_sample[i], min_[i], max_[i])
            for i in range(speech_sample.shape[0])
        ],
        axis=0,
    )
    return ret


def nonflat_frequency_response(
    speech_sample,
    fs: int,
    low_shelf_hz: int,
    high_shelf_hz: int,
    low_shelf_db: float,
    high_shelf_db: float,
    peak_hz_list: list,
    peak_db_list: list,
):
    response_modules = [
        LowShelfFilter(cutoff_frequency_hz=low_shelf_hz, gain_db=low_shelf_db),
        HighShelfFilter(cutoff_frequency_hz=high_shelf_hz, gain_db=high_shelf_db),
    ]

    for peak_hz, peak_db in zip(peak_hz_list, peak_db_list):
        response_modules.append(
            PeakFilter(cutoff_frequency_hz=peak_hz, gain_db=peak_db)
        )

    response_modules = Pedalboard(response_modules)
    output = response_modules(speech_sample, fs)
    return output


def loudness_transition(
    speech_sample,
    fs: int,
    start_list: list,
    peak_list: list,
    end_list: list,
    gain_db_list: list,
):

    gain_envelope = np.ones(speech_sample.shape)
    for start, peak, end, gain_db in zip(start_list, peak_list, end_list, gain_db_list):
        start, peak, end, gain_db = int(start), int(peak), int(end), float(gain_db)

        # gain increases (or decreases) from 0.0 to gain_db, between, start and peak
        gain_start_to_peak_db = np.linspace(0.0, gain_db, peak - start)
        gain_start_to_peak = 10.0 ** (gain_start_to_peak_db / 20.0)
        gain_envelope[:, start:peak] = gain_start_to_peak

        # gain decreases (or increases) from gain_db to 0.0, betwee, peak and end
        gain_peak_to_end_db = np.linspace(gain_db, 0.0, end - peak)
        gain_peak_to_end = 10.0 ** (gain_peak_to_end_db / 20.0)
        gain_envelope[:, peak:end] = gain_peak_to_end

    # Apply the gain envelope to the audio signal
    speech_sample = speech_sample * gain_envelope
    return speech_sample


def codec_compression(speech_sample, fs: int, vbr_quality: float):
    # if random.random() > 0.5:
    #     module = Pedalboard([GSMFullRateCompressor()])
    # else:
    #     module = Pedalboard([MP3Compressor()])
    # vbr_quality = random.uniform(
    #     params["mp3_vbr_quality"][0], params["mp3_vbr_quality"][1]
    # )
    # print(vbr_quality)
    assert 0.0 <= vbr_quality <= 10.0
    module = Pedalboard([MP3Compressor(vbr_quality=vbr_quality)])
    output = module(speech_sample, fs)
    return output


def packet_loss(
    speech_sample, fs: int, packet_loss_indices: list, packet_duration_ms: int = 20
):
    for idx in packet_loss_indices:
        start = idx * packet_duration_ms * fs // 1000
        end = (idx + 1) * packet_duration_ms * fs // 1000
        speech_sample[:, start:end] = 0

    return speech_sample


#############################
# Audio utilities
#############################
def read_audio(filename, force_1ch=False, fs=None):
    audio, fs_ = sf.read(filename, always_2d=True)
    audio = audio[:, :1].T if force_1ch else audio.T
    if fs is not None and fs != fs_:
        audio = librosa.resample(audio, orig_sr=fs_, target_sr=fs, res_type="soxr_hq")
        return audio, fs
    return audio, fs_


def save_audio(audio, filename, fs):
    if audio.ndim != 1:
        audio = audio[0] if audio.shape[0] == 1 else audio.T
    sf.write(filename, audio, samplerate=fs)


#############################
# Main entry
#############################
def main(args):
    speech_dic = {}
    for scp in args.speech_scps:
        with open(scp, "r") as f:
            for line in f:
                uid, fs, audio_path = line.strip().split()
                assert uid not in speech_dic, (uid, fs)
                speech_dic[uid] = audio_path

    noise_dic = {}
    for scp in args.noise_scps:
        with open(scp, "r") as f:
            for line in f:
                uid, fs, audio_path = line.strip().split()
                assert uid not in noise_dic, (uid, fs)
                noise_dic[uid] = audio_path
    noise_dic = dict(noise_dic)

    wind_noise_dic = {}
    for scp in args.wind_noise_scps:
        with open(scp, "r") as f:
            for line in f:
                uid, fs, audio_path = line.strip().split()
                assert uid not in wind_noise_dic, (uid, fs)
                wind_noise_dic[uid] = audio_path
    wind_noise_dic = dict(wind_noise_dic)
    noise_dic.update(wind_noise_dic)

    rir_dic = None
    if args.rir_scps is not None:
        rir_dic = {}
        for scp in args.rir_scps:
            with open(scp, "r") as f:
                for line in f:
                    uid, fs, audio_path = line.strip().split()
                    assert uid not in rir_dic, (uid, fs)
                    rir_dic[uid] = audio_path
    rir_dic = dict(rir_dic)

    meta = []
    with open(Path(args.log_dir) / "meta.tsv", "r") as f:
        headers = next(f).strip().split("\t")
        for line in f:
            meta.append(dict(zip(headers, line.strip().split("\t"))))
    process_map(
        partial(
            process_one_sample,
            store_noise=args.store_noise,
            speech_dic=speech_dic,
            noise_dic=noise_dic,
            rir_dic=rir_dic,
        ),
        meta,
        max_workers=args.nj,
        chunksize=args.chunksize,
    )


def process_one_sample(
    info,
    force_1ch=True,
    store_noise=False,
    speech_dic=None,
    noise_dic=None,
    rir_dic=None,
):
    uid = info["id"]
    fs = int(info["fs"])
    snr = float(info["snr_dB"])

    speech = speech_dic[info["speech_uid"]]
    noise = noise_dic[info["noise_uid"]]
    speech_sample = read_audio(speech, force_1ch=force_1ch, fs=fs)[0]
    noise_sample = read_audio(noise, force_1ch=force_1ch, fs=fs)[0]

    noisy_speech = deepcopy(speech_sample)

    # augmentation information, split by /
    augmentations = info["augmentation"].split("/")

    # loudness transition of speech
    for augmentation in augmentations:
        if augmentation.startswith("loudness_transition"):
            match = re.fullmatch(
                f"loudness_transition\(start=(.*),peak=(.*),end=(.*),gain_db=(.*)\)",
                augmentation,
            )
            start_, peak_, end_, gain_db_ = match.groups()
            noisy_speech = loudness_transition(
                noisy_speech,
                fs,
                ast.literal_eval(start_),
                ast.literal_eval(peak_),
                ast.literal_eval(end_),
                ast.literal_eval(gain_db_),
            )

    rir_uid = info["rir_uid"]
    if rir_uid != "none":
        rir = rir_dic[rir_uid]
        rir_sample = read_audio(rir, force_1ch=force_1ch, fs=fs)[0]
        noisy_speech = add_reverberation(speech_sample, rir_sample)
        # make sure the clean speech is aligned with the input noisy speech
        early_rir_sample = estimate_early_rir(rir_sample, fs=fs)
        speech_sample = add_reverberation(speech_sample, early_rir_sample)
    else:
        noisy_speech = speech_sample

    rng = np.random.default_rng(int(uid.split("_")[-1]))

    # simulation with non-linear wind-noise mixing
    if info["noise_uid"].startswith("wind_noise"):
        nuid = info["noise_uid"]
        augmentation = [a for a in augmentations if a.startswith("wind_noise")]
        assert (
            len(augmentation) == 1
        ), f"Configuration for the wind-noise simulation is necessary: {augmentation} {nuid}"

        # threshold, ratio, attack, release, sc_gain, snr, clipping, clipping_threshold
        match = re.fullmatch(
            f"wind_noise\(threshold=(.*),ratio=(.*),attack=(.*),release=(.*),sc_gain=(.*),clipping=(.*),clipping_threshold=(.*)\)",
            augmentation[0],
        )
        (
            threshold_,
            ratio_,
            attack_,
            release_,
            sc_gain_,
            clipping_,
            clipping_threshold_,
        ) = match.groups()
        noisy_speech, noise_sample = wind_noise(
            noisy_speech,
            noise_sample,
            fs,
            uid,
            float(threshold_),
            float(ratio_),
            float(attack_),
            float(release_),
            float(sc_gain_),
            bool(clipping_),
            float(clipping_threshold_),
            float(snr),
            rng=rng,
        )
    # just an additive noise
    else:
        noisy_speech, noise_sample = mix_noise(
            noisy_speech, noise_sample, snr=snr, rng=rng
        )

    # apply an additional augmentation
    for augmentation in augmentations:
        if augmentation == "none" or augmentation == "":
            pass
        elif augmentation.startswith("loudness_transition"):
            pass
        elif augmentation.startswith("wind_noise"):
            pass
        elif augmentation.startswith("bandwidth_limitation"):
            match = re.fullmatch(f"bandwidth_limitation-(.*)->(\d+)", augmentation)
            res_type, fs_new = match.groups()
            noisy_speech = bandwidth_limitation(
                noisy_speech, fs=fs, fs_new=int(fs_new), res_type=res_type
            )
        elif augmentation.startswith("clipping"):
            match = re.fullmatch(f"clipping\(min=(.*),max=(.*)\)", augmentation)
            min_, max_ = map(float, match.groups())
            noisy_speech = clipping(noisy_speech, min_quantile=min_, max_quantile=max_)
        elif augmentation.startswith("nonflat_freq_res"):
            match = re.fullmatch(
                f"nonflat_freq_res\(low_shelf_hz=(.*),high_shelf_hz=(.*),low_shelf_db=(.*),high_shelf_db=(.*),peak_hz=(.*),peak_db=(.*)\)",
                augmentation,
            )
            (
                low_shelf_hz_,
                high_shelf_hz_,
                low_shelf_db_,
                high_shelf_db_,
                peak_hz_list_,
                peak_db_list_,
            ) = match.groups()
            noisy_speech = nonflat_frequency_response(
                noisy_speech,
                fs,
                int(low_shelf_hz_),
                int(high_shelf_hz_),
                float(low_shelf_db_),
                float(high_shelf_db_),
                ast.literal_eval(peak_hz_list_),
                ast.literal_eval(peak_db_list_),
            )
        elif augmentation.startswith("codec"):
            match = re.fullmatch(f"codec\(vbr_quality=(.*)\)", augmentation)
            vbr_quality_ = match.groups()[0]
            noisy_speech = codec_compression(noisy_speech, fs, float(vbr_quality_))
        elif augmentation.startswith("packet_loss"):
            match = re.fullmatch(
                f"packet_loss\(packet_loss_indices=(.*),packet_duration_ms=(.*)\)",
                augmentation,
            )
            packet_loss_indices_, packet_duration_ms_ = match.groups()
            packet_loss_indices_ = ast.literal_eval(
                packet_loss_indices_
            )  # convert string to list
            noisy_speech = packet_loss(
                noisy_speech, fs, packet_loss_indices_, int(packet_duration_ms_)
            )
        else:
            raise NotImplementedError(augmentation)

    length = int(info["length"])
    assert noisy_speech.shape[-1] == length, (info, noisy_speech.shape)

    # normalization
    scale = 0.9 / max(
        np.max(np.abs(noisy_speech)),
        np.max(np.abs(speech_sample)),
        np.max(np.abs(noise_sample)),
    )

    save_audio(speech_sample * scale, info["clean_path"], fs)
    save_audio(noisy_speech * scale, info["noisy_path"], fs)
    if store_noise:
        save_audio(noise_sample * scale, info["noise_path"], fs)


if __name__ == "__main__":
    parser = get_parser()
    group = parser.add_argument_group(description="New arguments")
    group.add_argument(
        "--meta_tsv",
        type=str,
        required=True,
        help="Path to the tsv file containing meta information for simulation",
    )
    group.add_argument(
        "--nj",
        type=int,
        default=8,
        help="Number of parallel workers to speed up simulation",
    )
    group.add_argument(
        "--chunksize",
        type=int,
        default=1000,
        help="Chunk size used in process_map",
    )
    args = parser.parse_args()
    print(args)

    main(args)
