#!/usr/bin/bash
# Compress the MLS dataset to .tar.gz files

mls_dir=$1
output_dir=$2

for lang in german; do
    for stage in train dev test; do
        audio_dir="${mls_dir}/${lang}/${stage}/audio"
        audio_output_dir="${output_dir}/${lang}/${stage}/audio"

        mkdir -p $audio_output_dir

        # for subdir in "${audio_dir}"/*/; do
            # id=$(basename "$subdir")
            # output_path="${audio_output_dir}/${id}.tar.gz"

            # archive to tar.gz file
            # echo "Compress ${subdir} -> ${output_path}"
            # tar zcf ${output_path} "${subdir}"
        # done

        # Find all subdirectories in audio_dir and compress them in parallel
        find "$audio_dir" -mindepth 1 -maxdepth 1 -type d | xargs -I {} -P 16 bash -c '
            subdir="{}"
            id=$(basename "$subdir")
            output_path="$1/${id}.tar.gz"

            echo "Compress $subdir -> $output_path"
            tar -zcvf "$output_path" "$subdir"
        ' _ "$audio_output_dir"
    done
done