#!/usr/bin/env python3

mcu_dict = {
    'esp32': {
        'maximum_data_size': 327680,
        'tarch': 'xtensa',
        'target': 'esp32',
        'dual_core': 1,
        'bootloader_addr': '0x1000',
        'f_cpu': 240000000,
        'touch1200': '',
        'usb_mode': 0,
        'native_usb': 0,
        'cdc_on_boot': -1,
        'spi_mode': 'dio',
        'psram_opi': 0,
    },

    'esp32s2': {
        'maximum_data_size': 327680,
        'tarch': 'xtensa',
        'target': 'esp32s2',
        'dual_core': 0,
        'bootloader_addr': '0x1000',
        'f_cpu': 240000000,
        'touch1200': 'true',
        'usb_mode': 0,
        'native_usb': 1,
        'cdc_on_boot': 1,
        'spi_mode': 'qio',
        'psram_opi': 0,
    },

    'esp32s3': {
        'maximum_data_size': 327680,
        'tarch': 'xtensa',
        'target': 'esp32s3',
        'dual_core': 1,
        'bootloader_addr': '0x0',
        'f_cpu': 240000000,
        'touch1200': 'true',
        'usb_mode': 1,
        'native_usb': 1,
        'cdc_on_boot': 1,
        'spi_mode': 'qio',
        'psram_opi': 1,
    },

    'esp32c3': {
        'maximum_data_size': 327680,
        'tarch': 'riscv32',
        'target': 'esp',
        'dual_core': 0,
        'bootloader_addr': '0x0',
        'f_cpu': 160000000,
        'touch1200': 'false',
        'usb_mode': 0,
        'native_usb': 0,
        'cdc_on_boot': 1,
        'spi_mode': 'qio',
        'psram_opi': 0,
    },
}


def build_header(name, vendor, product, vid, pid_list):
    prettyname = vendor + " " + product
    print("##############################################################")
    print(f"# {prettyname}")
    print()
    print(f"{name}.name={prettyname}")

    for i in range(len(pid_list)):
        print(f"{name}.vid.{i}={vid}")
        print(f"{name}.pid.{i}={pid_list[i]}")
    print()


def build_upload(mcu, name, flash_size):
    info = mcu_dict[mcu]

    # Bootloader
    print(f"{name}.bootloader.tool=esptool_py")
    print(f"{name}.bootloader.tool.default=esptool_py")
    print()

    print(f"{name}.upload.tool=esptool_py")
    print(f"{name}.upload.tool.default=esptool_py")
    print(f"{name}.upload.tool.network=esp_ota")
    print()

    print(f"{name}.upload.maximum_size=1310720")
    print(f"{name}.upload.maximum_data_size={info['maximum_data_size']}")
    print(f"{name}.upload.flags=")
    print(f"{name}.upload.extra_flags=")

    if info['touch1200']:
        print(f"{name}.upload.use_1200bps_touch={info['touch1200']}")
        print(f"{name}.upload.wait_for_upload_port={info['touch1200']}")
        print()
        print(f"{name}.serial.disableDTR=false")
        print(f"{name}.serial.disableRTS=false")
    else:
        print()
        print(f"{name}.serial.disableDTR=true")
        print(f"{name}.serial.disableRTS=true")
    print()


def build_build(mcu, name, variant, flash_size, boarddefine, psram_type):
    info = mcu_dict[mcu]

    print(f"{name}.build.tarch={info['tarch']}")
    print(f"{name}.build.bootloader_addr={info['bootloader_addr']}")
    print(f"{name}.build.target={info['target']}")
    print(f"{name}.build.mcu={mcu}")
    print(f"{name}.build.core=esp32")
    print(f"{name}.build.variant={variant}")
    print(f"{name}.build.board={boarddefine}")
    print()

    if info['usb_mode']:
        print(f'{name}.build.usb_mode=0')
    if info['cdc_on_boot'] >= 0:
        print(f"{name}.build.cdc_on_boot={info['cdc_on_boot']}")
    if info['native_usb']:
        print(f"{name}.build.msc_on_boot=0")
        print(f"{name}.build.dfu_on_boot=0")
    print(f"{name}.build.f_cpu={info['f_cpu']}L")
    print(f"{name}.build.flash_size={flash_size}MB")
    print(f"{name}.build.flash_freq=80m")
    print(f"{name}.build.flash_mode=dio")
    print(f"{name}.build.boot={info['spi_mode']}")
    print(f"{name}.build.partitions=default")
    print(f"{name}.build.defines=")

    if info['dual_core']:
        print(f'{name}.build.loop_core=')
        print(f'{name}.build.event_core=')

    if info['psram_opi']:
        print(f'{name}.build.flash_type=qio')
        if psram_type == 'opi':
            print(f'{name}.build.psram_type=opi')
        else:
            print(f'{name}.build.psram_type=qspi')
        print(f'{name}.build.memory_type={{build.flash_type}}_{{build.psram_type}}')

    print()

def build_loop(mcu, name):
    info = mcu_dict[mcu]
    if info['dual_core']:
        print(f'{name}.menu.LoopCore.1=Core 1')
        print(f'{name}.menu.LoopCore.1.build.loop_core=-DARDUINO_RUNNING_CORE=1')
        print(f'{name}.menu.LoopCore.0=Core 0')
        print(f'{name}.menu.LoopCore.0.build.loop_core=-DARDUINO_RUNNING_CORE=0')
        print()

        print(f'{name}.menu.EventsCore.1=Core 1')
        print(f'{name}.menu.EventsCore.1.build.event_core=-DARDUINO_EVENT_RUNNING_CORE=1')
        print(f'{name}.menu.EventsCore.0=Core 0')
        print(f'{name}.menu.EventsCore.0.build.event_core=-DARDUINO_EVENT_RUNNING_CORE=0')
        print()


def build_menu_usb(mcu, name):
    info = mcu_dict[mcu]

    require_otg = ''
    upload_cdc = 'Internal USB'
    upload_uart = 'UART0'

    # ESP32-S3
    if info['usb_mode']:
        require_otg = ' (Requires USB-OTG Mode)'
        upload_cdc = 'USB-OTG CDC (TinyUSB)'
        upload_uart = 'UART0 / Hardware CDC'
        print(f"{name}.menu.USBMode.default=USB-OTG (TinyUSB)")
        print(f"{name}.menu.USBMode.default.build.usb_mode=0")
        print(f"{name}.menu.USBMode.hwcdc=Hardware CDC and JTAG")
        print(f"{name}.menu.USBMode.hwcdc.build.usb_mode=1")
        print()

    if info['cdc_on_boot'] >= 0:
        print(f"{name}.menu.CDCOnBoot.cdc=Enabled")
        print(f"{name}.menu.CDCOnBoot.cdc.build.cdc_on_boot=1")
        print(f"{name}.menu.CDCOnBoot.default=Disabled")
        print(f"{name}.menu.CDCOnBoot.default.build.cdc_on_boot=0")
        print()

    if info['native_usb']:
        print(f"{name}.menu.MSCOnBoot.default=Disabled")
        print(f"{name}.menu.MSCOnBoot.default.build.msc_on_boot=0")
        print(f"{name}.menu.MSCOnBoot.msc=Enabled" + require_otg)
        print(f"{name}.menu.MSCOnBoot.msc.build.msc_on_boot=1")
        print()

        print(f"{name}.menu.DFUOnBoot.default=Disabled")
        print(f"{name}.menu.DFUOnBoot.default.build.dfu_on_boot=0")
        print(f"{name}.menu.DFUOnBoot.dfu=Enabled" + require_otg)
        print(f"{name}.menu.DFUOnBoot.dfu.build.dfu_on_boot=1")
        print()

        print(f"{name}.menu.UploadMode.cdc={upload_cdc}")
        print(f"{name}.menu.UploadMode.cdc.upload.use_1200bps_touch=true")
        print(f"{name}.menu.UploadMode.cdc.upload.wait_for_upload_port=true")
        print(f"{name}.menu.UploadMode.default={upload_uart}")
        print(f"{name}.menu.UploadMode.default.upload.use_1200bps_touch=false")
        print(f"{name}.menu.UploadMode.default.upload.wait_for_upload_port=false")
        print()


def build_menu_psram(mcu, name, psram_size, psram_type):
    info = mcu_dict[mcu]

    enabled_defines = f"{name}.menu.PSRAM.enabled.build.defines=-DBOARD_HAS_PSRAM"
    if mcu == 'esp32':
        enabled_defines += ' -mfix-esp32-psram-cache-issue -mfix-esp32-psram-cache-strategy=memw'

    if psram_size > 0:
        if info['psram_opi']:
            if psram_type == 'opi':
                print(f"{name}.menu.PSRAM.opi=OPI PSRAM")
                print(f"{name}.menu.PSRAM.opi.build.defines=-DBOARD_HAS_PSRAM")
                print(f"{name}.menu.PSRAM.opi.build.psram_type=opi")
                print(f"{name}.menu.PSRAM.disabled=Disabled")
                print(f"{name}.menu.PSRAM.disabled.build.defines=")
                print(f"{name}.menu.PSRAM.disabled.build.psram_type=opi")
            else:
                # print all option qspi/disabled/opi
                print(f"{name}.menu.PSRAM.enabled=QSPI PSRAM")
                print(enabled_defines)
                print(f"{name}.menu.PSRAM.enabled.build.psram_type=qspi")
                print(f"{name}.menu.PSRAM.disabled=Disabled")
                print(f"{name}.menu.PSRAM.disabled.build.defines=")
                print(f"{name}.menu.PSRAM.disabled.build.psram_type=qspi")
                print(f"{name}.menu.PSRAM.opi=OPI PSRAM")
                print(f"{name}.menu.PSRAM.opi.build.defines=-DBOARD_HAS_PSRAM")
                print(f"{name}.menu.PSRAM.opi.build.psram_type=opi")
        else:
            print(f"{name}.menu.PSRAM.enabled=Enabled")
            print(enabled_defines)
            print(f"{name}.menu.PSRAM.disabled=Disabled")
            print(f"{name}.menu.PSRAM.disabled.build.defines=")
        print()


def build_menu_partition(mcu, name, flash_size, noota_first):
    info = mcu_dict[mcu]

    if flash_size == 4:
        if info['native_usb']:
            # TinyUF2 with ota
            tinyuf2_partition = (
                f"{name}.menu.PartitionScheme.tinyuf2=TinyUF2 4MB (1.3MB APP/960KB FATFS)\n"
                f"{name}.menu.PartitionScheme.tinyuf2.build.custom_bootloader=bootloader-tinyuf2\n"
                f"{name}.menu.PartitionScheme.tinyuf2.build.partitions=tinyuf2-partitions-4MB\n"
                f"{name}.menu.PartitionScheme.tinyuf2.upload.maximum_size=1441792\n"
                f'{name}.menu.PartitionScheme.tinyuf2.upload.extra_flags=0x2d0000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            )
            # TinyUF2 without ota
            tinyuf2_noota_partition = (
                f"{name}.menu.PartitionScheme.tinyuf2_noota=TinyUF2 4MB No OTA (2.7MB APP/960KB FATFS)\n"
                f"{name}.menu.PartitionScheme.tinyuf2_noota.build.custom_bootloader=bootloader-tinyuf2\n"
                f"{name}.menu.PartitionScheme.tinyuf2_noota.build.partitions=tinyuf2-partitions-4MB-noota\n"
                f"{name}.menu.PartitionScheme.tinyuf2_noota.upload.maximum_size=2883584\n"
                f'{name}.menu.PartitionScheme.tinyuf2_noota.upload.extra_flags=0x2d0000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            )
            # TinyUF2 4MB with 3MB OTA
            # tinyuf2_ota3mb_partition = (
            #     f"{name}.menu.PartitionScheme.tinyuf2_app3m5=TinyUF2 4MB Large App (3.5MB APP/256KB FATFS)\n"
            #     f"{name}.menu.PartitionScheme.tinyuf2_app3m5.build.custom_bootloader=bootloader-tinyuf2\n"
            #     f"{name}.menu.PartitionScheme.tinyuf2_app3m5.build.partitions=tinyuf2-partitions-4MB-app3M5\n"
            #     f"{name}.menu.PartitionScheme.tinyuf2_app3m5.upload.maximum_size=3604480\n"
            #     f'{name}.menu.PartitionScheme.tinyuf2_app3m5.upload.extra_flags=0x380000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            # )
            if noota_first:
                print(tinyuf2_noota_partition)
                print(tinyuf2_partition)
            else:
                print(tinyuf2_partition)
                print(tinyuf2_noota_partition)
            # print(tinyuf2_ota3mb_partition)

        print(f"{name}.menu.PartitionScheme.default=Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.default.build.partitions=default")
        print(f"{name}.menu.PartitionScheme.defaultffat=Default 4MB with ffat (1.2MB APP/1.5MB FATFS)")
        print(f"{name}.menu.PartitionScheme.defaultffat.build.partitions=default_ffat")
        print(f"{name}.menu.PartitionScheme.minimal=Minimal (1.3MB APP/700KB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.minimal.build.partitions=minimal")
        print(f"{name}.menu.PartitionScheme.no_ota=No OTA (2MB APP/2MB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.no_ota.build.partitions=no_ota")
        print(f"{name}.menu.PartitionScheme.no_ota.upload.maximum_size=2097152")
        print(f"{name}.menu.PartitionScheme.noota_3g=No OTA (1MB APP/3MB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.noota_3g.build.partitions=noota_3g")
        print(f"{name}.menu.PartitionScheme.noota_3g.upload.maximum_size=1048576")
        print(f"{name}.menu.PartitionScheme.noota_ffat=No OTA (2MB APP/2MB FATFS)")
        print(f"{name}.menu.PartitionScheme.noota_ffat.build.partitions=noota_ffat")
        print(f"{name}.menu.PartitionScheme.noota_ffat.upload.maximum_size=2097152")
        print(f"{name}.menu.PartitionScheme.noota_3gffat=No OTA (1MB APP/3MB FATFS)")
        print(f"{name}.menu.PartitionScheme.noota_3gffat.build.partitions=noota_3gffat")
        print(f"{name}.menu.PartitionScheme.noota_3gffat.upload.maximum_size=1048576")
        print(f"{name}.menu.PartitionScheme.huge_app=Huge APP (3MB No OTA/1MB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.huge_app.build.partitions=huge_app")
        print(f"{name}.menu.PartitionScheme.huge_app.upload.maximum_size=3145728")
        print(f"{name}.menu.PartitionScheme.min_spiffs=Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.min_spiffs.build.partitions=min_spiffs")
        print(f"{name}.menu.PartitionScheme.min_spiffs.upload.maximum_size=1966080")
    elif flash_size == 8:
        if info['native_usb']:
            # TinyUF2 with ota
            tinyuf2_partition = (
                f"{name}.menu.PartitionScheme.tinyuf2=TinyUF2 8MB (2MB APP/3.7MB FATFS)\n"
                f"{name}.menu.PartitionScheme.tinyuf2.build.custom_bootloader=bootloader-tinyuf2\n"
                f"{name}.menu.PartitionScheme.tinyuf2.build.partitions=tinyuf2-partitions-8MB\n"
                f"{name}.menu.PartitionScheme.tinyuf2.upload.maximum_size=2097152\n"
                f'{name}.menu.PartitionScheme.tinyuf2.upload.extra_flags=0x410000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            )
            # TinyUF2 without ota
            tinyuf2_noota_partition = (
                f"{name}.menu.PartitionScheme.tinyuf2_noota=TinyUF2 8MB No OTA (4MB APP/3.7MB FATFS)\n"
                f"{name}.menu.PartitionScheme.tinyuf2_noota.build.custom_bootloader=bootloader-tinyuf2\n"
                f"{name}.menu.PartitionScheme.tinyuf2_noota.build.partitions=tinyuf2-partitions-8MB-noota\n"
                f"{name}.menu.PartitionScheme.tinyuf2_noota.upload.maximum_size=4194304\n"
                f'{name}.menu.PartitionScheme.tinyuf2_noota.upload.extra_flags=0x410000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            )
            if noota_first:
                print(tinyuf2_noota_partition)
                print(tinyuf2_partition)
            else:
                print(tinyuf2_partition)
                print(tinyuf2_noota_partition)

        print(f"{name}.menu.PartitionScheme.default_8MB=Default (3MB APP/1.5MB SPIFFS)")
        print(f"{name}.menu.PartitionScheme.default_8MB.build.partitions=default_8MB")
        print(f"{name}.menu.PartitionScheme.default_8MB.upload.maximum_size=3342336")
    elif flash_size == 16:
        if info['native_usb']:
            # TinyUF2 with ota
            tinyuf2_partition = (
                f'{name}.menu.PartitionScheme.tinyuf2=TinyUF2 16MB (2MB APP/11.6MB FATFS)\n'
                f'{name}.menu.PartitionScheme.tinyuf2.build.custom_bootloader=bootloader-tinyuf2\n'
                f'{name}.menu.PartitionScheme.tinyuf2.build.partitions=tinyuf2-partitions-16MB\n'
                f'{name}.menu.PartitionScheme.tinyuf2.upload.maximum_size=2097152\n'
                f'{name}.menu.PartitionScheme.tinyuf2.upload.extra_flags=0x410000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            )
            # TinyUF2 without ota
            tinyuf2_noota_partition = (
                f'{name}.menu.PartitionScheme.tinyuf2_noota=TinyUF2 16MB No OTA(4MB APP/11.6MB FATFS)\n'
                f'{name}.menu.PartitionScheme.tinyuf2_noota.build.custom_bootloader=bootloader-tinyuf2\n'
                f'{name}.menu.PartitionScheme.tinyuf2_noota.build.partitions=tinyuf2-partitions-16MB-noota\n'
                f'{name}.menu.PartitionScheme.tinyuf2_noota.upload.maximum_size=4194304\n'
                f'{name}.menu.PartitionScheme.tinyuf2_noota.upload.extra_flags=0x410000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'
            )
            if noota_first:
                print(tinyuf2_noota_partition)
                print(tinyuf2_partition)
            else:
                print(tinyuf2_partition)
                print(tinyuf2_noota_partition)

        print(f'{name}.menu.PartitionScheme.default_16MB=Default (6.25MB APP/3.43MB SPIFFS)')
        print(f'{name}.menu.PartitionScheme.default_16MB.build.partitions=default_16MB')
        print(f'{name}.menu.PartitionScheme.default_16MB.upload.maximum_size=6553600')
        print(f'{name}.menu.PartitionScheme.large_spiffs=Large SPIFFS (4.5MB APP/6.93MB SPIFFS)')
        print(f'{name}.menu.PartitionScheme.large_spiffs.build.partitions=large_spiffs_16MB')
        print(f'{name}.menu.PartitionScheme.large_spiffs.upload.maximum_size=4718592')
        print(f'{name}.menu.PartitionScheme.app3M_fat9M_16MB=16M Flash (3MB APP/9MB FATFS)')
        print(f'{name}.menu.PartitionScheme.app3M_fat9M_16MB.build.partitions=app3M_fat9M_16MB')
        print(f'{name}.menu.PartitionScheme.app3M_fat9M_16MB.upload.maximum_size=3145728')
        print(f'{name}.menu.PartitionScheme.fatflash=16M Flash (2MB APP/12.5MB FAT)')
        print(f'{name}.menu.PartitionScheme.fatflash.build.partitions=ffat')
        print(f'{name}.menu.PartitionScheme.fatflash.upload.maximum_size=2097152')
    print()


def build_menu_freq(mcu, name):
    info = mcu_dict[mcu]
    wf_bt = '(WiFi/BT)' if mcu == 'esp32' else '(WiFi)'

    if info['f_cpu'] == 240000000:
        print(f"{name}.menu.CPUFreq.240=240MHz {wf_bt}")
        print(f"{name}.menu.CPUFreq.240.build.f_cpu=240000000L")
    print(f"{name}.menu.CPUFreq.160=160MHz {wf_bt}")
    print(f"{name}.menu.CPUFreq.160.build.f_cpu=160000000L")
    print(f"{name}.menu.CPUFreq.80=80MHz {wf_bt}")
    print(f"{name}.menu.CPUFreq.80.build.f_cpu=80000000L")
    print(f"{name}.menu.CPUFreq.40=40MHz")
    print(f"{name}.menu.CPUFreq.40.build.f_cpu=40000000L")
    print(f"{name}.menu.CPUFreq.20=20MHz")
    print(f"{name}.menu.CPUFreq.20.build.f_cpu=20000000L")
    print(f"{name}.menu.CPUFreq.10=10MHz")
    print(f"{name}.menu.CPUFreq.10.build.f_cpu=10000000L")
    print()


def build_menu_flash(mcu, name, flash_size):
    info = mcu_dict[mcu]

    if mcu == 'esp32s3':
        print(f'{name}.menu.FlashMode.qio=QIO 80MHz')
        print(f'{name}.menu.FlashMode.qio.build.flash_mode=dio')
        print(f'{name}.menu.FlashMode.qio.build.boot=qio')
        print(f'{name}.menu.FlashMode.qio.build.boot_freq=80m')
        print(f'{name}.menu.FlashMode.qio.build.flash_freq=80m')
        print(f'{name}.menu.FlashMode.qio120=QIO 120MHz')
        print(f'{name}.menu.FlashMode.qio120.build.flash_mode=dio')
        print(f'{name}.menu.FlashMode.qio120.build.boot=qio')
        print(f'{name}.menu.FlashMode.qio120.build.boot_freq=120m')
        print(f'{name}.menu.FlashMode.qio120.build.flash_freq=80m')
        print(f'{name}.menu.FlashMode.dio=DIO 80MHz')
        print(f'{name}.menu.FlashMode.dio.build.flash_mode=dio')
        print(f'{name}.menu.FlashMode.dio.build.boot=dio')
        print(f'{name}.menu.FlashMode.dio.build.boot_freq=80m')
        print(f'{name}.menu.FlashMode.dio.build.flash_freq=80m')
        print(f'{name}.menu.FlashMode.opi=OPI 80MHz')
        print(f'{name}.menu.FlashMode.opi.build.flash_mode=dout')
        print(f'{name}.menu.FlashMode.opi.build.boot=opi')
        print(f'{name}.menu.FlashMode.opi.build.boot_freq=80m')
        print(f'{name}.menu.FlashMode.opi.build.flash_freq=80m')
    else:
        if (info['spi_mode'] == 'qio'):
            print(f"{name}.menu.FlashMode.qio=QIO")
            print(f"{name}.menu.FlashMode.qio.build.flash_mode=dio")
            print(f"{name}.menu.FlashMode.qio.build.boot=qio")
            print(f"{name}.menu.FlashMode.dio=DIO")
            print(f"{name}.menu.FlashMode.dio.build.flash_mode=dio")
            print(f"{name}.menu.FlashMode.dio.build.boot=dio")
            print()

        print(f"{name}.menu.FlashFreq.80=80MHz")
        print(f"{name}.menu.FlashFreq.80.build.flash_freq=80m")
        print(f"{name}.menu.FlashFreq.40=40MHz")
        print(f"{name}.menu.FlashFreq.40.build.flash_freq=40m")

    print()
    print(f"{name}.menu.FlashSize.{flash_size}M={flash_size}MB ({flash_size*8}Mb)")
    print(f"{name}.menu.FlashSize.{flash_size}M.build.flash_size={flash_size}MB")
    print()


def build_menu_uploadspeed(mcu, name):
    info = mcu_dict[mcu]
    print(f"{name}.menu.UploadSpeed.921600=921600")
    print(f"{name}.menu.UploadSpeed.921600.upload.speed=921600")
    print(f"{name}.menu.UploadSpeed.115200=115200")
    print(f"{name}.menu.UploadSpeed.115200.upload.speed=115200")
    print(f"{name}.menu.UploadSpeed.256000.windows=256000")
    print(f"{name}.menu.UploadSpeed.256000.upload.speed=256000")
    print(f"{name}.menu.UploadSpeed.230400.windows.upload.speed=256000")
    print(f"{name}.menu.UploadSpeed.230400=230400")
    print(f"{name}.menu.UploadSpeed.230400.upload.speed=230400")
    print(f"{name}.menu.UploadSpeed.460800.linux=460800")
    print(f"{name}.menu.UploadSpeed.460800.macosx=460800")
    print(f"{name}.menu.UploadSpeed.460800.upload.speed=460800")
    print(f"{name}.menu.UploadSpeed.512000.windows=512000")
    print(f"{name}.menu.UploadSpeed.512000.upload.speed=512000")
    print()


def build_menu_debug(mcu, name):
    info = mcu_dict[mcu]
    print(f"{name}.menu.DebugLevel.none=None")
    print(f"{name}.menu.DebugLevel.none.build.code_debug=0")
    print(f"{name}.menu.DebugLevel.error=Error")
    print(f"{name}.menu.DebugLevel.error.build.code_debug=1")
    print(f"{name}.menu.DebugLevel.warn=Warn")
    print(f"{name}.menu.DebugLevel.warn.build.code_debug=2")
    print(f"{name}.menu.DebugLevel.info=Info")
    print(f"{name}.menu.DebugLevel.info.build.code_debug=3")
    print(f"{name}.menu.DebugLevel.debug=Debug")
    print(f"{name}.menu.DebugLevel.debug.build.code_debug=4")
    print(f"{name}.menu.DebugLevel.verbose=Verbose")
    print(f"{name}.menu.DebugLevel.verbose.build.code_debug=5")
    print()


def build_menu_erase(mcu, name):
    print(f"{name}.menu.EraseFlash.none=Disabled")
    print(f"{name}.menu.EraseFlash.none.upload.erase_cmd=")
    print(f"{name}.menu.EraseFlash.all=Enabled")
    print(f"{name}.menu.EraseFlash.all.upload.erase_cmd=-e")
    print()


def build_menu_zigbee(mcu, name):
    print(f"{name}.menu.ZigbeeMode.default=Disabled")
    print(f"{name}.menu.ZigbeeMode.default.build.zigbee_mode=")
    print(f"{name}.menu.ZigbeeMode.default.build.zigbee_libs=")
    print(f"{name}.menu.ZigbeeMode.zczr=Zigbee ZCZR (coordinator)")
    print(f"{name}.menu.ZigbeeMode.zczr.build.zigbee_mode=-DZIGBEE_MODE_ZCZR")
    print(f"{name}.menu.ZigbeeMode.zczr.build.zigbee_libs=-lesp_zb_api_zczr -lesp_zb_cli_command -lzboss_stack.zczr.trace -lzboss_stack.zczr -lzboss_port")
    print()


def make_board(mcu, name, variant, boarddefine, flash_size, psram_size, psram_type, noota_first, vendor, product, vid, pid_list):
    if variant == "":
        variant = name
    build_header(name, vendor, product, vid, pid_list)
    build_upload(mcu, name, flash_size)
    build_build(mcu, name, variant, flash_size, boarddefine, psram_type)
    build_loop(mcu, name)
    build_menu_usb(mcu, name)
    build_menu_psram(mcu, name, psram_size, psram_type)
    build_menu_partition(mcu, name, flash_size, noota_first)
    build_menu_freq(mcu, name)
    build_menu_flash(mcu, name, flash_size)
    build_menu_uploadspeed(mcu, name)
    build_menu_debug(mcu, name)
    build_menu_erase(mcu, name)
    build_menu_zigbee(mcu, name)


# ---------------------
# Metro
# ---------------------

make_board("esp32s2", "adafruit_metro_esp32s2", "", "METRO_ESP32S2",
           4, 2, '', False,
           "Adafruit", "Metro ESP32-S2", "0x239A", ["0x80DF", "0x00DF", "0x80E0"])

make_board("esp32s3", "adafruit_metro_esp32s3", "", "METRO_ESP32S3",
           16, 8, 'opi', False,
           "Adafruit", "Metro ESP32-S3", "0x239A", ["0x8145", "0x0145", "0x8146"])

make_board("esp32s2", "adafruit_magtag29_esp32s2", "", "MAGTAG29_ESP32S2",
           4, 2, '', False,
           "Adafruit", 'MagTag 2.9"', "0x239A", ["0x80E5", "0x00E5", "0x80E6"])

make_board("esp32s2", "adafruit_funhouse_esp32s2", "", "FUNHOUSE_ESP32S2",
           4, 2, '', False,
           "Adafruit", 'FunHouse', "0x239A", ["0x80F9", "0x00F9", "0x80FA"])

# ---------------------
# Feather
# ---------------------

# ESP32
make_board("esp32", "featheresp32", "feather_esp32", "FEATHER_ESP32",
           4, 0, '', False,
           "Adafruit", "ESP32 Feather", "", [])

make_board("esp32", "adafruit_feather_esp32_v2", "adafruit_feather_esp32_v2", "ADAFRUIT_FEATHER_ESP32_V2",
           8, 2, '', False,
           "Adafruit", "Feather ESP32 V2", "", [])

# S2
make_board("esp32s2", "adafruit_feather_esp32s2", "", "ADAFRUIT_FEATHER_ESP32S2",
           4, 2, '', False,
           "Adafruit", 'Feather ESP32-S2', "0x239A", ["0x80EB", "0x00EB", "0x80EC"])

make_board("esp32s2", "adafruit_feather_esp32s2_tft", "", "ADAFRUIT_FEATHER_ESP32S2_TFT",
           4, 2, '', False,
           "Adafruit", 'Feather ESP32-S2 TFT', "0x239A", ["0x810F", "0x010F", "0x8110"])

make_board("esp32s2", "adafruit_feather_esp32s2_reversetft", "", "ADAFRUIT_FEATHER_ESP32S2_REVTFT",
           4, 2, '', False,
           "Adafruit", 'Feather ESP32-S2 Reverse TFT', "0x239A", ["0x80ED", "0x00ED", "0x80EE"])

# S3
make_board("esp32s3", "adafruit_feather_esp32s3", "", "ADAFRUIT_FEATHER_ESP32S3",
           4, 2, '', False,
           "Adafruit", 'Feather ESP32-S3 2MB PSRAM', "0x239A", ["0x811B", "0x011B", "0x811C"])

make_board("esp32s3", "adafruit_feather_esp32s3_nopsram", "", "ADAFRUIT_FEATHER_ESP32S3_NOPSRAM",
           8, 0, '', False,
           "Adafruit", 'Feather ESP32-S3 No PSRAM', "0x239A", ["0x8113", "0x0113", "0x8114"])

make_board("esp32s3", "adafruit_feather_esp32s3_tft", "", "ADAFRUIT_FEATHER_ESP32S3_TFT",
           4, 2, '', False,
           "Adafruit", 'Feather ESP32-S3 TFT', "0x239A", ["0x811D", "0x011D", "0x811E"])

make_board("esp32s3", "adafruit_feather_esp32s3_reversetft", "", "ADAFRUIT_FEATHER_ESP32S3_REVTFT",
           4, 2, '', False,
           "Adafruit", 'Feather ESP32-S3 Reverse TFT', "0x239A", ["0x8123", "0x0123", "0x8124"])

# ---------------------
# QT Py
# ---------------------

make_board("esp32", "adafruit_qtpy_esp32_pico", "adafruit_qtpy_esp32", "ADAFRUIT_QTPY_ESP32_PICO",
           8, 2, '', False,
           "Adafruit", "QT Py ESP32", "", [])

make_board("esp32c3", "adafruit_qtpy_esp32c3", "", "ADAFRUIT_QTPY_ESP32C3",
           4, 0, '', False,
           "Adafruit", "QT Py ESP32-C3", "0x303a", ["0x1001"])

make_board("esp32s2", "adafruit_qtpy_esp32s2", "", "ADAFRUIT_QTPY_ESP32S2",
           4, 2, '', False,
           "Adafruit", 'QT Py ESP32-S2', "0x239A", ["0x8111", "0x0111", "0x8112"])

make_board("esp32s3", "adafruit_qtpy_esp32s3_nopsram", "", "ADAFRUIT_QTPY_ESP32S3_NOPSRAM",
           8, 0, '', False,
           "Adafruit", 'QT Py ESP32-S3 No PSRAM', "0x239A", ["0x8119", "0x0119", "0x811A"])

make_board("esp32s3", "adafruit_qtpy_esp32s3_n4r2", "", "ADAFRUIT_QTPY_ESP32S3_N4R2",
           4, 2, '', False,
           "Adafruit", 'QT Py ESP32-S3 (4M Flash 2M PSRAM)', "0x239A", ["0x8143", "0x0143", "0x8144"])

# --
make_board("esp32", "adafruit_itsybitsy_esp32", "", "ADAFRUIT_ITSYBITSY_ESP32",
           8, 2, '', False,
           "Adafruit", "ItsyBitsy ESP32", "", [])

make_board("esp32s3", "adafruit_matrixportal_esp32s3", "", "ADAFRUIT_MATRIXPORTAL_ESP32S3",
           8, 2, '', False,
           "Adafruit", 'MatrixPortal ESP32-S3', "0x239A", ["0x8125", "0x0125", "0x8126"])

make_board("esp32s3", "adafruit_camera_esp32s3", "", "ADAFRUIT_CAMERA_ESP32S3",
           4, 2, 'qspi', True,
           "Adafruit", 'pyCamera S3', "0x239A", ["0x0117", "0x8117", "0x8118"])

make_board("esp32s3", "adafruit_qualia_s3_rgb666", "", "QUALIA_S3_RGB666",
           16, 8, 'opi', False,
           "Adafruit", 'Qualia ESP32-S3 RGB666', "0x239A", ["0x8147", "0x0147", "0x8148"])
