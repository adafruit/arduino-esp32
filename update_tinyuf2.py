import os
import shutil
import urllib.request
import zipfile
from multiprocessing import Pool

version = '0.18.1'
print('version {}'.format(version))

# variant name, tinyuf2 bootloader name

# all_variant = [
#     ['adafruit_feather_esp32s3', ''],
# ]

# [variant name, download name]
# Alphabetical order
all_variant = [
    ['adafruit_camera_esp32s3', ''],
    ['adafruit_feather_esp32s2', ''],
    ['adafruit_feather_esp32s2_reversetft', 'adafruit_feather_esp32s2_reverse_tft'],
    ['adafruit_feather_esp32s2_tft', ''],
    ['adafruit_feather_esp32s3', ''],
    ['adafruit_feather_esp32s3_nopsram', ''],
    ['adafruit_feather_esp32s3_reversetft', 'adafruit_feather_esp32s3_reverse_tft'],
    ['adafruit_feather_esp32s3_tft', ''],
    ['adafruit_funhouse_esp32s2', ''],
    ['adafruit_magtag29_esp32s2', 'adafruit_magtag_29gray'],
    ['adafruit_matrixportal_esp32s3', 'adafruit_matrixportal_s3'],
    ['adafruit_metro_esp32s2', ''],
    ['adafruit_metro_esp32s3', ''],
    ['adafruit_qtpy_esp32s2', ''],
    ['adafruit_qtpy_esp32s3_n4r2', ''],
    ['adafruit_qtpy_esp32s3_nopsram', 'adafruit_qtpy_esp32s3'],
    ['adafruit_qualia_s3_rgb666', ''],
]


def update_variant(v):
    variant = v[0]
    dl_name = v[1] if v[1] else v[0]

    # Download from bootloader release
    name = 'tinyuf2-{}-{}.zip'.format(dl_name, version)
    url = 'https://github.com/adafruit/tinyuf2/releases/download/{}/tinyuf2-{}-{}.zip'.format(
        version, dl_name, version)
    print("Downloading TinyUF2 for", variant)
    urllib.request.urlretrieve(url, variant)

    variant_path = 'variants/{}'.format(variant)

    # unzip (will overwrite old files)
    with zipfile.ZipFile(variant, "r") as zf:
        zf.extract("bootloader.bin", variant_path)
        os.renames(os.path.join(variant_path, "bootloader.bin"),
                   os.path.join(variant_path, "bootloader-tinyuf2.bin"))
        zf.extract("tinyuf2.bin", variant_path)

    # remove zip file
    os.remove(variant)


with Pool(processes=os.cpu_count()) as pool:
    pool.map(update_variant, all_variant)
