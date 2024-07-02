#ifndef Pins_Arduino_h
#define Pins_Arduino_h

#include <stdint.h>
#include "soc/soc_caps.h"

#define USB_VID          0x239A
#define USB_PID          0x815F
#define USB_MANUFACTURER "Adafruit"
#define USB_PRODUCT      "Vindie S2"
#define USB_SERIAL       ""  // Empty string for MAC address

#define LED_BUILTIN 18
#define BUILTIN_LED LED_BUILTIN  // backward compatibility

// Neopixel
#define PIN_NEOPIXEL 26
// RGB_BUILTIN and RGB_BRIGHTNESS can be used in new Arduino API neopixelWrite() and digitalWrite() for blinking
#define RGB_BUILTIN    (PIN_NEOPIXEL + SOC_GPIO_PIN_COUNT)
#define RGB_BRIGHTNESS 64

#define NEOPIXEL_NUM 1

#define PIN_BUTTON1 0  // BOOT0 switch

static const uint8_t TX = 45;
static const uint8_t RX = 21;
#define TX1 TX
#define RX1 RX

static const uint8_t SDA = 41;
static const uint8_t SCL = 42;

static const uint8_t FAN = 33;

#endif /* Pins_Arduino_h */
