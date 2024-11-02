#!/usr/bin/bash
# Automatically download the MLS dataset

output_dir=$1

mkdir -p ${output_dir}

# get audiobook link from segments.txt (original ones, not 64kb-compressed files)
n_jobs=16
if [ ! -e "${output_dir}/download_mls.done" ]; then
    # for lang in english german dutch french spanish italian portuguese polish; do
    for lang in english; do
        for stage in train; do
            echo "Download ${lang} ${stage}-subset"

            this_dir=${output_dir}/${lang}/${stage}
            audio_output_dir="${this_dir}/orig_audio"

            mp3links_dir="${this_dir}/mp3links"

            # Process each split file
            # done: 0-89, 9000-9086
            for split_num in $(seq 34 89); do

                if [ "$split_num" -lt 10 ]; then
                    split_num=$(printf "%02d" "$split_num")
                fi

                # split_file="${mp3links_dir}/mp3links_${split_num}.txt"
                split_file="${audio_output_dir}/download_failed_data${split_num}.txt"
                echo "Download $split_file"

                # Create a corresponding audio output directory
                split_audio_output_dir="${audio_output_dir}/${split_num}"
                mkdir -p ${split_audio_output_dir}

                # touch "${audio_output_dir}/download_failed_data${split_num}.txt"

                # Download mp3 files for the current split
                cat "$split_file" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget -q -nc -P "$0" "$1" || echo "Error: Failed to download $1"' "${split_audio_output_dir}" {}
                # cat "$split_file" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget -q -nc -P "$0" "$1" || echo "$1" >> "$2"' "${split_audio_output_dir}" {} "${audio_output_dir}/download_failed_data${split_num}.txt"

            done

        done
    done
fi


