#!/usr/bin/bash
# Automatically download the MLS dataset

output_dir=$1
download_opus=false

mkdir -p ${output_dir}

# script to download the 16kHz MLS
# for lang in english german dutch french spanish italian portuguese polish; do
#     if $download_opus; then
#         url=https://dl.fbaipublicfiles.com/mls/mls_${lang}_opus.tar.gz
#     else
#         url=https://dl.fbaipublicfiles.com/mls/mls_${lang}.tar.gz
#     fi
# 
#     filename=$(basename "${url}")
#     wget $url -O "${output_dir}/${filename}"
# 
#     tar xvzf "${output_dir}/${filename}"
# 
# done

# TODO: add scripts to download segment.txt files

# get audiobook link from segments.txt (original ones, not 64kb-compressed files)
n_jobs=16
if [ ! -e "${output_dir}/download_mls.done" ]; then
    # for lang in english german dutch french spanish italian portuguese polish; do
    for lang in english; do
        for stage in dev test; do
            echo "Download ${lang} ${stage}-subset"

            this_dir=${output_dir}/${lang}/${stage}
            audio_output_dir="${this_dir}/orig_audio"
            mkdir -p ${audio_output_dir}

            mp3links_dir="${this_dir}/mp3links"
            mkdir -p ${mp3links_dir}
            
            # get audiobook link from segments.txt (original ones, not 64kb-compressed files)
            # awk '{print $2}' "${this_dir}/segments.txt" | sed 's/_64kb//g' | sort | uniq > "${this_dir}/mp3links.txt"

            # check if all the links are valid (faster due to --spider option)
            # cat "${output_dir}/${lang}/${stage}/mp3links.txt" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget --spider -q -P "${audio_output_dir}" {} || echo "Error: Failed to download {}"'

            # download mp3 files
            # cat "${output_dir}/${lang}/${stage}/mp3links.txt" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget -q -nc -P "$0" "$1" || echo "Error: Failed to download $1"' "${audio_output_dir}" {}

            # Split mp3links.txt into files with 1024 lines each and save them in the mp3links directory
            # split -l 1024 -d --additional-suffix=.txt "${this_dir}/mp3links.txt" "${mp3links_dir}/mp3links_"

            # Process each split file
            for split_file in ${mp3links_dir}/mp3links_*.txt; do
                echo "Download $split_file"

                # Extract the split number (e.g., mp3links_1.txt -> 1)
                split_num=$(echo "$split_file" | grep -oP '(?<=_)\d+(?=\.txt)')

                # Create a corresponding audio output directory
                split_audio_output_dir="${audio_output_dir}/${split_num}"
                mkdir -p ${split_audio_output_dir}

                touch "${audio_output_dir}/download_failed_data${split_num}.txt"

                # Download mp3 files for the current split
                # cat "$split_file" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget -q -nc -P "$0" "$1" || echo "Error: Failed to download $1"' "${split_audio_output_dir}" {}
                # cat "$split_file" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget -q -nc -P "$0" "$1" || echo "$1" >> "$2"' "${split_audio_output_dir}" {} "${audio_output_dir}/download_failed_data.txt"
                cat "$split_file" | xargs -P "$n_jobs" -n 1 -I {} sh -c 'wget -q -nc -P "$0" "$1" || echo "$1" >> "$2"' "${split_audio_output_dir}" {} "${audio_output_dir}/download_failed_data${split_num}.txt"

            done

        done
    done
fi


