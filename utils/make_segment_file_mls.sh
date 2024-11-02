#!/usr/bin/bash
# Automatically download the MLS dataset

segment_file_output_dir=$1
audio_output_dir=$2

mkdir -p ${segment_file_output_dir}
mkdir -p ${audio_output_dir}


# TODO: add scripts to download segment.txt files

# get audiobook link from segments.txt (original ones, not 64kb-compressed files)
if [ ! -e "${segment_file_output_dir}/download_mls.done" ]; then

    touch "${audio_output_dir}/num_files.txt"

    # for lang in english german dutch french spanish italian portuguese polish; do
    for lang in english; do
        for stage in train dev test; do
            echo "Make a segment file for ${lang} ${stage}-subset"

            this_dir=${segment_file_output_dir}/${lang}/${stage}
            input_file="${this_dir}/segments.txt"
            output_file="${this_dir}/segments2.txt"

: << 'COMMENT'

            if [ -e "$output_file" ]; then
                rm $output_file
            fi

            declare -A url_map
            url_map=()

            # Read input.txt line by line
            while IFS=$'\t' read -r col1 url col3 col4; do
                # Extract the file name from the URL and remove "_64kb" if present
                file_name=$(basename "$url" | sed 's/_64kb//')
                
                # Append the data to the corresponding file name
                url_map["$file_name"]+="$col1 $col3 $col4 "

                # echo "${file_name} $col1 $col3 $col4"
            done < "$input_file"

            # Write the results to output.txt
            for key in "${!url_map[@]}"; do
                # echo "$key"
                echo "$key ${url_map[$key]}" >> "$output_file"
            done

            sort -k1 "$output_file" -o "$output_file"

COMMENT

            # segment files
            echo "Segment audio files for ${lang} ${stage}-subset"

            python utils/segment_mls.py \
                --input_dir ${this_dir}/orig_audio \
                --segment_file ${output_file} \
                --output_dir ${audio_output_dir}/${lang}/${stage}/audio \
                --workers 16

            num_orig_files=$(wc -l < "$input_file")
            num_segmented_files=$(find "${audio_output_dir}/${lang}/${stage}/audio" -type f -name "*.flac" | wc -l)

            echo "${lang} ${stage}: MLS ${num_orig_files} files, HQ-MLS ${num_segmented_files} files" >> "${audio_output_dir}/num_files.txt"

        done
    done
fi


