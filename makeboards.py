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
    print("# {}".format(prettyname))
    print()
    print("{}.name={}".format(name, prettyname))

    for i in range(len(pid_list)):
        print("{}.vid.{}={}".format(name, i, vid))
        print("{}.pid.{}={}".format(name, i, pid_list[i]))
    print()


def build_upload(mcu, name, flash_size):
    info = mcu_dict[mcu]
    
    # Bootloader
    print("{}.bootloader.tool=esptool_py".format(name))
    print("{}.bootloader.tool.default=esptool_py".format(name))
    print()

    print("{}.upload.tool=esptool_py".format(name))
    print("{}.upload.tool.default=esptool_py".format(name))
    print("{}.upload.tool.network=esp_ota".format(name))
    print()

    print("{}.upload.maximum_size=1310720".format(name))
    print("{}.upload.maximum_data_size={}".format(name, info['maximum_data_size']))
    print("{}.upload.flags=".format(name))
    print("{}.upload.extra_flags=".format(name))

    if info['touch1200']:
        print("{}.upload.use_1200bps_touch={}".format(name, info['touch1200']))
        print("{}.upload.wait_for_upload_port={}".format(name, info['touch1200']))
        print()
        print("{}.serial.disableDTR=false".format(name))
        print("{}.serial.disableRTS=false".format(name))
    else:
        print()
        print("{}.serial.disableDTR=true".format(name))
        print("{}.serial.disableRTS=true".format(name))
    print()


def build_build(mcu, name, variant, flash_size, boarddefine):
    info = mcu_dict[mcu]

    print("{}.build.tarch={}".format(name, info['tarch']))
    print("{}.build.bootloader_addr={}".format(name, info['bootloader_addr']))
    print("{}.build.target={}".format(name, info['target']))
    print("{}.build.mcu={}".format(name, mcu))
    print("{}.build.core={}".format(name, "esp32"))
    print("{}.build.variant={}".format(name, variant))
    print("{}.build.board={}".format(name, boarddefine))
    print()

    if info['usb_mode']:
        print('{}.build.usb_mode=0'.format(name))
    if info['cdc_on_boot'] >= 0:
        print("{}.build.cdc_on_boot={}".format(name, info['cdc_on_boot']))
    if info['native_usb']:
        print("{}.build.msc_on_boot=0".format(name))
        print("{}.build.dfu_on_boot=0".format(name))
    print("{}.build.f_cpu={}L".format(name, info["f_cpu"]))
    print("{}.build.flash_size={}MB".format(name, flash_size))
    print("{}.build.flash_freq=80m".format(name))
    print("{}.build.flash_mode=dio".format(name))
    print("{}.build.boot={}".format(name, info['spi_mode']))
    print("{}.build.partitions=default".format(name))
    print("{}.build.defines=".format(name))
    
    if info['dual_core']:
        print('{}.build.loop_core='.format(name))
        print('{}.build.event_core='.format(name))
    
    if info['psram_opi']:
        print('{}.build.flash_type=qio'.format(name))
        print('{}.build.psram_type=qspi'.format(name))
        print('{}.build.memory_type={{build.flash_type}}_{{build.psram_type}}'.format(name))
    
    print()

def build_loop(mcu, name):
    info = mcu_dict[mcu]
    if info['dual_core']:
        print('{}.menu.LoopCore.1=Core 1'.format(name))
        print('{}.menu.LoopCore.1.build.loop_core=-DARDUINO_RUNNING_CORE=1'.format(name))
        print('{}.menu.LoopCore.0=Core 0'.format(name))
        print('{}.menu.LoopCore.0.build.loop_core=-DARDUINO_RUNNING_CORE=0'.format(name))
        print()
        
        print('{}.menu.EventsCore.1=Core 1'.format(name))
        print('{}.menu.EventsCore.1.build.event_core=-DARDUINO_EVENT_RUNNING_CORE=1'.format(name))
        print('{}.menu.EventsCore.0=Core 0'.format(name))
        print('{}.menu.EventsCore.0.build.event_core=-DARDUINO_EVENT_RUNNING_CORE=0'.format(name))        
        print()
        

def build_menu_usb(mcu, name):
    info = mcu_dict[mcu]
    
    require_otg = ''
    upload_cdc = 'Internal USB'
    upload_uart = 'UART0'
    
    if info['usb_mode']:
        require_otg = ' (Requires USB-OTG Mode)'
        upload_cdc = 'USB-OTG CDC (TinyUSB)'
        upload_uart = 'UART0 / Hardware CDC'
        print('{}.menu.USBMode.default=USB-OTG (TinyUSB)'.format(name))
        print('{}.menu.USBMode.default.build.usb_mode=0'.format(name))
        print('{}.menu.USBMode.hwcdc=Hardware CDC and JTAG'.format(name))
        print('{}.menu.USBMode.hwcdc.build.usb_mode=1'.format(name))                
        print()
    
    if info['cdc_on_boot'] >= 0:
        print("{}.menu.CDCOnBoot.cdc=Enabled".format(name))
        print("{}.menu.CDCOnBoot.cdc.build.cdc_on_boot=1".format(name))
        print("{}.menu.CDCOnBoot.default=Disabled".format(name))
        print("{}.menu.CDCOnBoot.default.build.cdc_on_boot=0".format(name))
        print()

    if info['native_usb']:
        print("{}.menu.MSCOnBoot.default=Disabled".format(name))
        print("{}.menu.MSCOnBoot.default.build.msc_on_boot=0".format(name))
        print("{}.menu.MSCOnBoot.msc=Enabled".format(name) + require_otg)
        print("{}.menu.MSCOnBoot.msc.build.msc_on_boot=1".format(name))
        print()

        print("{}.menu.DFUOnBoot.default=Disabled".format(name))
        print("{}.menu.DFUOnBoot.default.build.dfu_on_boot=0".format(name))
        print("{}.menu.DFUOnBoot.dfu=Enabled".format(name) + require_otg)
        print("{}.menu.DFUOnBoot.dfu.build.dfu_on_boot=1".format(name))
        print()

        print("{}.menu.UploadMode.cdc={}".format(name, upload_cdc))
        print("{}.menu.UploadMode.cdc.upload.use_1200bps_touch=true".format(name))
        print("{}.menu.UploadMode.cdc.upload.wait_for_upload_port=true".format(name))
        print("{}.menu.UploadMode.default={}".format(name, upload_uart))
        print("{}.menu.UploadMode.default.upload.use_1200bps_touch=false".format(name))
        print("{}.menu.UploadMode.default.upload.wait_for_upload_port=false".format(name))
        print()


def build_menu_psram(mcu, name, psram_size):
    info = mcu_dict[mcu]
    
    enabled_defines = "{}.menu.PSRAM.enabled.build.defines=-DBOARD_HAS_PSRAM".format(name)    
    if mcu == 'esp32':
        enabled_defines += ' -mfix-esp32-psram-cache-issue -mfix-esp32-psram-cache-strategy=memw'
            
    if psram_size > 0:
        if info['psram_opi']:
            print('{}.menu.PSRAM.enabled=QSPI PSRAM'.format(name))
            print(enabled_defines)
            print('{}.menu.PSRAM.enabled.build.psram_type=qspi'.format(name))
            print('{}.menu.PSRAM.disabled=Disabled'.format(name))
            print('{}.menu.PSRAM.disabled.build.defines='.format(name))
            print('{}.menu.PSRAM.disabled.build.psram_type=qspi'.format(name))
            print('{}.menu.PSRAM.opi=OPI PSRAM'.format(name))
            print('{}.menu.PSRAM.opi.build.defines=-DBOARD_HAS_PSRAM'.format(name))
            print('{}.menu.PSRAM.opi.build.psram_type=opi'.format(name))
        else:
            print("{}.menu.PSRAM.enabled=Enabled".format(name))
            print(enabled_defines)
            print("{}.menu.PSRAM.disabled=Disabled".format(name))
            print("{}.menu.PSRAM.disabled.build.defines=".format(name))
        print()


def build_menu_partition(mcu, name, flash_size):
    info = mcu_dict[mcu]

    if flash_size == 4:
        if info['native_usb']:
            print("{}.menu.PartitionScheme.tinyuf2=TinyUF2 4MB (1.3MB APP/960KB FFAT)".format(name))
            print("{}.menu.PartitionScheme.tinyuf2.build.custom_bootloader=bootloader-tinyuf2".format(name))
            print("{}.menu.PartitionScheme.tinyuf2.build.custom_partitions=partitions-4MB-tinyuf2".format(name))
            print("{}.menu.PartitionScheme.tinyuf2.upload.maximum_size=1441792".format(name))
            print('{}.menu.PartitionScheme.tinyuf2.upload.extra_flags=0x2d0000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'.format(name))        

        print("{}.menu.PartitionScheme.default=Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.default.build.partitions=default".format(name))
        print("{}.menu.PartitionScheme.defaultffat=Default 4MB with ffat (1.2MB APP/1.5MB FATFS)".format(name))
        print("{}.menu.PartitionScheme.defaultffat.build.partitions=default_ffat".format(name))
        print("{}.menu.PartitionScheme.minimal=Minimal (1.3MB APP/700KB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.minimal.build.partitions=minimal".format(name))
        print("{}.menu.PartitionScheme.no_ota=No OTA (2MB APP/2MB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.no_ota.build.partitions=no_ota".format(name))
        print("{}.menu.PartitionScheme.no_ota.upload.maximum_size=2097152".format(name))
        print("{}.menu.PartitionScheme.noota_3g=No OTA (1MB APP/3MB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.noota_3g.build.partitions=noota_3g".format(name))
        print("{}.menu.PartitionScheme.noota_3g.upload.maximum_size=1048576".format(name))
        print("{}.menu.PartitionScheme.noota_ffat=No OTA (2MB APP/2MB FATFS)".format(name))
        print("{}.menu.PartitionScheme.noota_ffat.build.partitions=noota_ffat".format(name))
        print("{}.menu.PartitionScheme.noota_ffat.upload.maximum_size=2097152".format(name))
        print("{}.menu.PartitionScheme.noota_3gffat=No OTA (1MB APP/3MB FATFS)".format(name))
        print("{}.menu.PartitionScheme.noota_3gffat.build.partitions=noota_3gffat".format(name))
        print("{}.menu.PartitionScheme.noota_3gffat.upload.maximum_size=1048576".format(name))
        print("{}.menu.PartitionScheme.huge_app=Huge APP (3MB No OTA/1MB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.huge_app.build.partitions=huge_app".format(name))
        print("{}.menu.PartitionScheme.huge_app.upload.maximum_size=3145728".format(name))
        print("{}.menu.PartitionScheme.min_spiffs=Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.min_spiffs.build.partitions=min_spiffs".format(name))
        print("{}.menu.PartitionScheme.min_spiffs.upload.maximum_size=1966080".format(name))
    elif flash_size == 8:
        if info['native_usb']:
            print("{}.menu.PartitionScheme.tinyuf2=TinyUF2 8MB (2MB APP/3.7MB FFAT)".format(name))
            print("{}.menu.PartitionScheme.tinyuf2.build.custom_bootloader=bootloader-tinyuf2".format(name))
            print("{}.menu.PartitionScheme.tinyuf2.build.custom_partitions=partitions-8MB-tinyuf2".format(name))
            print("{}.menu.PartitionScheme.tinyuf2.upload.maximum_size=2097152".format(name))
            print('{}.menu.PartitionScheme.tinyuf2.upload.extra_flags=0x410000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'.format(name))

        print("{}.menu.PartitionScheme.default_8MB=Default (3MB APP/1.5MB SPIFFS)".format(name))
        print("{}.menu.PartitionScheme.default_8MB.build.partitions=default_8MB".format(name))
        print("{}.menu.PartitionScheme.default_8MB.upload.maximum_size=3342336".format(name))
    elif flash_size == 16:
        if info['native_usb']:
            print('{}.menu.PartitionScheme.tinyuf2=TinyUF2 16MB (2MB APP/11.6MB FFAT)'.format(name))
            print('{}.menu.PartitionScheme.tinyuf2.build.custom_bootloader=bootloader-tinyuf2'.format(name))
            print('{}.menu.PartitionScheme.tinyuf2.build.custom_partitions=partitions-16MB-tinyuf2'.format(name))
            print('{}.menu.PartitionScheme.tinyuf2.upload.maximum_size=2097152'.format(name))
            print('{}.menu.PartitionScheme.tinyuf2.upload.extra_flags=0x410000 "{{runtime.platform.path}}/variants/{{build.variant}}/tinyuf2.bin"'.format(name))

        print('{}.menu.PartitionScheme.default_16MB=Default (6.25MB APP/3.43MB SPIFFS)'.format(name))
        print('{}.menu.PartitionScheme.default_16MB.build.partitions=default_16MB'.format(name))
        print('{}.menu.PartitionScheme.default_16MB.upload.maximum_size=6553600'.format(name))
        print('{}.menu.PartitionScheme.large_spiffs=Large SPIFFS (4.5MB APP/6.93MB SPIFFS)'.format(name))
        print('{}.menu.PartitionScheme.large_spiffs.build.partitions=large_spiffs_16MB'.format(name))
        print('{}.menu.PartitionScheme.large_spiffs.upload.maximum_size=4718592'.format(name))
        print('{}.menu.PartitionScheme.app3M_fat9M_16MB=16M Flash (3MB APP/9MB FATFS)'.format(name))
        print('{}.menu.PartitionScheme.app3M_fat9M_16MB.build.partitions=app3M_fat9M_16MB'.format(name))
        print('{}.menu.PartitionScheme.app3M_fat9M_16MB.upload.maximum_size=3145728'.format(name))
        print('{}.menu.PartitionScheme.fatflash=16M Flash (2MB APP/12.5MB FAT)'.format(name))
        print('{}.menu.PartitionScheme.fatflash.build.partitions=ffat'.format(name))
        print('{}.menu.PartitionScheme.fatflash.upload.maximum_size=2097152'.format(name))
    print()


def build_menu_freq(mcu, name):
    info = mcu_dict[mcu]
    wf_bt = '(WiFi/BT)' if mcu == 'esp32' else '(WiFi)'
    
    if info['f_cpu'] == 240000000:
        print("{}.menu.CPUFreq.240=240MHz {}".format(name, wf_bt))
        print("{}.menu.CPUFreq.240.build.f_cpu=240000000L".format(name))
    print("{}.menu.CPUFreq.160=160MHz {}".format(name, wf_bt))
    print("{}.menu.CPUFreq.160.build.f_cpu=160000000L".format(name))
    print("{}.menu.CPUFreq.80=80MHz {}".format(name, wf_bt))
    print("{}.menu.CPUFreq.80.build.f_cpu=80000000L".format(name))
    print("{}.menu.CPUFreq.40=40MHz".format(name))
    print("{}.menu.CPUFreq.40.build.f_cpu=40000000L".format(name))
    print("{}.menu.CPUFreq.20=20MHz".format(name))
    print("{}.menu.CPUFreq.20.build.f_cpu=20000000L".format(name))
    print("{}.menu.CPUFreq.10=10MHz".format(name))
    print("{}.menu.CPUFreq.10.build.f_cpu=10000000L".format(name))
    print()


def build_menu_flash(mcu, name, flash_size):
    info = mcu_dict[mcu]
    
    if mcu == 'esp32s3':
        print('{}.menu.FlashMode.qio=QIO 80MHz'.format(name))
        print('{}.menu.FlashMode.qio.build.flash_mode=dio'.format(name))
        print('{}.menu.FlashMode.qio.build.boot=qio'.format(name))
        print('{}.menu.FlashMode.qio.build.boot_freq=80m'.format(name))
        print('{}.menu.FlashMode.qio.build.flash_freq=80m'.format(name))
        print('{}.menu.FlashMode.qio120=QIO 120MHz'.format(name))
        print('{}.menu.FlashMode.qio120.build.flash_mode=dio'.format(name))
        print('{}.menu.FlashMode.qio120.build.boot=qio'.format(name))
        print('{}.menu.FlashMode.qio120.build.boot_freq=120m'.format(name))
        print('{}.menu.FlashMode.qio120.build.flash_freq=80m'.format(name))
        print('{}.menu.FlashMode.dio=DIO 80MHz'.format(name))
        print('{}.menu.FlashMode.dio.build.flash_mode=dio'.format(name))
        print('{}.menu.FlashMode.dio.build.boot=dio'.format(name))
        print('{}.menu.FlashMode.dio.build.boot_freq=80m'.format(name))
        print('{}.menu.FlashMode.dio.build.flash_freq=80m'.format(name))
        print('{}.menu.FlashMode.opi=OPI 80MHz'.format(name))
        print('{}.menu.FlashMode.opi.build.flash_mode=dout'.format(name))
        print('{}.menu.FlashMode.opi.build.boot=opi'.format(name))
        print('{}.menu.FlashMode.opi.build.boot_freq=80m'.format(name))
        print('{}.menu.FlashMode.opi.build.flash_freq=80m'.format(name))
    else:
        if (info['spi_mode'] == 'qio'):
            print("{}.menu.FlashMode.qio=QIO".format(name))
            print("{}.menu.FlashMode.qio.build.flash_mode=dio".format(name))
            print("{}.menu.FlashMode.qio.build.boot=qio".format(name))
            print("{}.menu.FlashMode.dio=DIO".format(name))
            print("{}.menu.FlashMode.dio.build.flash_mode=dio".format(name))
            print("{}.menu.FlashMode.dio.build.boot=dio".format(name))
            print("{}.menu.FlashMode.qout=QOUT".format(name))
            print("{}.menu.FlashMode.qout.build.flash_mode=dout".format(name))
            print("{}.menu.FlashMode.qout.build.boot=qout".format(name))
            print("{}.menu.FlashMode.dout=DOUT".format(name))
            print("{}.menu.FlashMode.dout.build.flash_mode=dout".format(name))
            print("{}.menu.FlashMode.dout.build.boot=dout".format(name))
            print()
    
        print("{}.menu.FlashFreq.80=80MHz".format(name))
        print("{}.menu.FlashFreq.80.build.flash_freq=80m".format(name))
        print("{}.menu.FlashFreq.40=40MHz".format(name))
        print("{}.menu.FlashFreq.40.build.flash_freq=40m".format(name))
    
    print()
    print("{}.menu.FlashSize.{}M={}MB ({}Mb)".format(name, flash_size, flash_size, flash_size*8))
    print("{}.menu.FlashSize.{}M.build.flash_size={}MB".format(name, flash_size, flash_size))
    print()


def build_menu_uploadspeed(mcu, name):
    info = mcu_dict[mcu]
    print("{}.menu.UploadSpeed.921600=921600".format(name))
    print("{}.menu.UploadSpeed.921600.upload.speed=921600".format(name))
    print("{}.menu.UploadSpeed.115200=115200".format(name))
    print("{}.menu.UploadSpeed.115200.upload.speed=115200".format(name))
    print("{}.menu.UploadSpeed.256000.windows=256000".format(name))
    print("{}.menu.UploadSpeed.256000.upload.speed=256000".format(name))
    print("{}.menu.UploadSpeed.230400.windows.upload.speed=256000".format(name))
    print("{}.menu.UploadSpeed.230400=230400".format(name))
    print("{}.menu.UploadSpeed.230400.upload.speed=230400".format(name))
    print("{}.menu.UploadSpeed.460800.linux=460800".format(name))
    print("{}.menu.UploadSpeed.460800.macosx=460800".format(name))
    print("{}.menu.UploadSpeed.460800.upload.speed=460800".format(name))
    print("{}.menu.UploadSpeed.512000.windows=512000".format(name))
    print("{}.menu.UploadSpeed.512000.upload.speed=512000".format(name))
    print()


def build_menu_debug(mcu, name):
    info = mcu_dict[mcu]
    print("{}.menu.DebugLevel.none=None".format(name))
    print("{}.menu.DebugLevel.none.build.code_debug=0".format(name))
    print("{}.menu.DebugLevel.error=Error".format(name))
    print("{}.menu.DebugLevel.error.build.code_debug=1".format(name))
    print("{}.menu.DebugLevel.warn=Warn".format(name))
    print("{}.menu.DebugLevel.warn.build.code_debug=2".format(name))
    print("{}.menu.DebugLevel.info=Info".format(name))
    print("{}.menu.DebugLevel.info.build.code_debug=3".format(name))
    print("{}.menu.DebugLevel.debug=Debug".format(name))
    print("{}.menu.DebugLevel.debug.build.code_debug=4".format(name))
    print("{}.menu.DebugLevel.verbose=Verbose".format(name))
    print("{}.menu.DebugLevel.verbose.build.code_debug=5".format(name))
    print()


def make_board(mcu, name, variant, boarddefine, flash_size, psram_size, vendor, product, vid, pid_list):
    if variant == "":
        variant = name
    build_header(name, vendor, product, vid, pid_list)
    build_upload(mcu, name, flash_size)
    build_build(mcu, name, variant, flash_size, boarddefine)
    build_loop(mcu, name)
    build_menu_usb(mcu, name)
    build_menu_psram(mcu, name, psram_size)
    build_menu_partition(mcu, name, flash_size)
    build_menu_freq(mcu, name)
    build_menu_flash(mcu, name, flash_size)
    build_menu_uploadspeed(mcu, name)
    build_menu_debug(mcu, name)


make_board("esp32", "featheresp32", "feather_esp32", "FEATHER_ESP32", 4, 0,
           "Adafruit", "ESP32 Feather", "", [])

# ---------- ESP32 S2 -----------

make_board("esp32s2", "adafruit_metro_esp32s2", "", "METRO_ESP32S2", 4, 2,
           "Adafruit", "Metro ESP32-S2", "0x239A", ["0x80DF", "0x00DF", "0x80E0"])

make_board("esp32s2", "adafruit_magtag29_esp32s2", "", "MAGTAG29_ESP32S2", 4, 2,
           "Adafruit", 'MagTag 2.9"', "0x239A", ["0x80E5", "0x00E5", "0x80E6"])

make_board("esp32s2", "adafruit_funhouse_esp32s2", "", "FUNHOUSE_ESP32S2", 4, 2,
           "Adafruit", 'FunHouse', "0x239A", ["0x80F9", "0x00F9", "0x80FA"])

make_board("esp32s2", "adafruit_feather_esp32s2", "", "ADAFRUIT_FEATHER_ESP32S2", 4, 2,
           "Adafruit", 'Feather ESP32-S2', "0x239A", ["0x80EB", "0x00EB", "0x80EC"])

make_board("esp32s2", "adafruit_feather_esp32s2_tft", "", "ADAFRUIT_FEATHER_ESP32S2_TFT", 4, 2,
           "Adafruit", 'Feather ESP32-S2 TFT', "0x239A", ["0x810F", "0x010F", "0x8110"])

make_board("esp32s2", "adafruit_qtpy_esp32s2", "", "ADAFRUIT_QTPY_ESP32S2", 4, 2,
           "Adafruit", 'QT Py ESP32-S2', "0x239A", ["0x8111", "0x0111", "0x8112"])

# C3
make_board("esp32c3", "adafruit_qtpy_esp32c3", "", "ADAFRUIT_QTPY_ESP32C3", 4, 0,
           "Adafruit", "QT Py ESP32-C3", "0x303a", ["0x1001"])

# ESP32
make_board("esp32", "adafruit_qtpy_esp32_pico", "adafruit_qtpy_esp32", "ADAFRUIT_QTPY_ESP32_PICO", 8, 2,
           "Adafruit", "QT Py ESP32", "", [])

make_board("esp32", "adafruit_feather_esp32_v2", "adafruit_feather_esp32_v2", "ADAFRUIT_FEATHER_ESP32_V2", 8, 2,
           "Adafruit", "Feather ESP32 V2", "", [])

# S3

make_board("esp32s3", "adafruit_feather_esp32s3", "", "ADAFRUIT_FEATHER_ESP32S3", 4, 2,
           "Adafruit", 'Feather ESP32-S3 2MB PSRAM', "0x239A", ["0x811B", "0x011B", "0x811C"])

make_board("esp32s3", "adafruit_feather_esp32s3_nopsram", "", "ADAFRUIT_FEATHER_ESP32S3_NOPSRAM", 8, 0,
           "Adafruit", 'Feather ESP32-S3 No PSRAM', "0x239A", ["0x8113", "0x0113", "0x8114"])

make_board("esp32s3", "adafruit_feather_esp32s3_tft", "", "ADAFRUIT_FEATHER_ESP32S3_TFT", 4, 2,
           "Adafruit", 'Feather ESP32-S3 TFT', "0x239A", ["0x811D", "0x011D", "0x811E"])

make_board("esp32s3", "adafruit_qtpy_esp32s3_nopsram", "", "ADAFRUIT_QTPY_ESP32S3_NOPSRAM", 8, 0,
           "Adafruit", 'QT Py ESP32-S3 No PSRAM', "0x239A", ["0x8119", "0x0119", "0x811A"])
