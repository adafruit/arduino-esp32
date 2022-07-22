#ifndef Pins_Arduino_h
#define Pins_Arduino_h

#include <stdint.h>


#define USB_VID            0x239A
#define USB_PID            0x8117
#define USB_MANUFACTURER   "Adafruit"
#define USB_PRODUCT        "Camera ESP32-S2"
#define USB_SERIAL         "" // Empty string for MAC adddress


#define EXTERNAL_NUM_INTERRUPTS 46
#define NUM_DIGITAL_PINS        48
#define NUM_ANALOG_INPUTS       20

#define analogInputToDigitalPin(p)  (((p)<20)?(esp32_adc2gpio[(p)]):-1)
#define digitalPinToInterrupt(p)    (((p)<48)?(p):-1)
#define digitalPinHasPWM(p)         (p < 46)

#define LED_BUILTIN   1

static const uint8_t PIN_NEOPIXEL = 21;

static const uint8_t TFT_BACKLIGHT = 41;
static const uint8_t TFT_DC        = 40;
static const uint8_t TFT_CS        = 39;
static const uint8_t TFT_RESET     = 38;
static const uint8_t TFT_RST       = 38;

static const uint8_t SD_CS          = 2;
static const uint8_t SD_CHIP_SELECT = 2;
static const uint8_t SPEAKER        = 41;

static const uint8_t SDA = 33;
static const uint8_t SCL = 34;

static const uint8_t SS    = 39;
static const uint8_t MOSI  = 35;
static const uint8_t SCK   = 36;
static const uint8_t MISO  = 37;

static const uint8_t A0 = 17;
static const uint8_t A1 = 18;

static const uint8_t TX = 43;
static const uint8_t RX = 44;

static const uint8_t DAC1 = 17;
static const uint8_t DAC2 = 18;

#endif /* Pins_Arduino_h */
