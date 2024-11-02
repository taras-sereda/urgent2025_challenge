#!/usr/bin/bash

output_dir="./commonvoice"

# fill in these info
lang="chinese"
URL="https://storage.googleapis.com/common-voice-prod-prod-datasets/cv-corpus-11.0-2022-09-21/cv-corpus-11.0-2022-09-21-zh-CN.tar.gz?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=gke-prod%40moz-fx-common-voice-prod.iam.gserviceaccount.com%2F20241030%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20241030T115150Z&X-Goog-Expires=43200&X-Goog-SignedHeaders=host&X-Goog-Signature=64245774d3bdad1f7944101ad6df3a6c44347dd0f87d28387f3f6b25cdb8e507df646019e95f14543ed935e8bc276210c12649ba72500015aacf8e1ca0a9d4c2552d91b06ddec5e391e6b22a076f6b511a4bb6192da77a8e254a67ccc2276654694eaaab519d933aef133118e29764a9b591f6768d253d488843a105334ad825013effa686dc0b3e2cfe4610eec82ecb4cb86650d6e42aa0036d833f6fdf05df0d404ab4c45d0f431d85278fe96b1fdc4f9a57d8cdbe5b0c0bd10b785fc9216ce1a156188b8ef1018c8980d47b0cb0ea53d24267808ff9126692c9c902e3a4082a4864b113150433c18c57e4032e9fd51ed32bc1d4eeae80f342bcf0cc7ada5a"

wget $URL -O "${output_dir}/cv11.0-${lang}.tar.gz"
python ./utils/tar_extractor.py -m 1000 \
    -i ${output_dir}/cv11.0-${lang}.tar.gz \
    -o ${output_dir} \
    --skip_existing --skip_errors