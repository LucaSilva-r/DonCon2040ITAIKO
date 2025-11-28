#ifndef GLOBALCONFIGURATION_H_
#define GLOBALCONFIGURATION_H_

#include "peripherals/Controller.h"
#include "peripherals/Display.h"
#include "peripherals/Drum.h"
#include "peripherals/StatusLed.h"

#include "hardware/i2c.h"
#include "hardware/spi.h"

namespace Doncon::Config {

struct I2c {
    uint8_t sda_pin;
    uint8_t scl_pin;
    i2c_inst_t *block;
    uint speed_hz;
};

namespace Default {

const usb_mode_t usb_mode = USB_MODE_KEYBOARD_P1;

const I2c i2c_config = {
    .sda_pin = 6,
    .scl_pin = 7,
    .block = i2c1,
    .speed_hz = 1000000,
};

const Peripherals::Drum::Config drum_config = {
    .trigger_thresholds =
        {
            .don_left = 800,
            .ka_left = 800,
            .don_right = 800,
            .ka_right = 800,
        },

    .double_trigger_mode = Peripherals::Drum::Config::DoubleTriggerMode::Off,
    .double_trigger_thresholds =
        {
            .don_left = 3000,                                                                                                                                                                                             
            .ka_left = 2500,
            .don_right = 3000,
            .ka_right = 2500,
        },

    .debounce_delay_ms = 25,
    .don_debounce = 30,
    .kat_debounce = 30,
    .crosstalk_debounce = 30,
    .key_timeout_ms = 19,
    .roll_counter_timeout_ms = 500,

    .adc_channels =
        {
            .don_left = 1,
            .ka_left = 0,
            .don_right = 2,
            .ka_right = 3,
        },

    // ADC Config, either InternalAdc or ExternalAdc
    .adc_config =
        Peripherals::Drum::Config::InternalAdc{
            .sample_count = 1,
        },

    // .adc_config =
    //     Peripherals::Drum::Config::ExternalAdc{
    //         .spi_block = spi1,
    //         .spi_speed_hz = 2000000,
    //         .spi_mosi_pin = 11,
    //         .spi_miso_pin = 12,
    //         .spi_sclk_pin = 10,
    //         .spi_scsn_pin = 13,
    //         .spi_level_shifter_enable_pin = 9,
    //     },
};
  
const Peripherals::Controller::Config controller_config = {
    .pins =
        {
            .dpad =
                {
                    .up = 13,
                    .down = 9,
                    .left = 12,
                    .right = 10,
                },
            .buttons =
                {
                    .north = 1,
                    .east = 8,
                    .south = 2,
                    .west = 4,

                    .l = 15,
                    .r = 0,

                    .start = 3,
                    .select = 14,
                    .home = 5,
                    .share = 11,
                },
        },

    .debounce_delay_ms = 25,

    // GPIO Config, either InternalGpio or ExternalGpio
    .gpio_config = Peripherals::Controller::Config::InternalGpio{},
    // .gpio_config =
    //     Peripherals::Controller::Config::ExternalGpio{
    //         .i2c =
    //             {
    //                 .block = i2c_config.block,
    //                 .address = 0x20,
    //             },
    //     },
};

const Peripherals::StatusLed::Config led_config = {
    .idle_color = {.r = 128, .g = 128, .b = 128},
    .don_left_color = {.r = 255, .g = 0, .b = 0},
    .ka_left_color = {.r = 0, .g = 0, .b = 255},
    .don_right_color = {.r = 255, .g = 255, .b = 0},
    .ka_right_color = {.r = 0, .g = 255, .b = 255},

    .led_enable_pin = 25,
    .led_pin = 16,
    .is_rgbw = false,

    .brightness = 255,
    .enable_player_color = true,
};

const Peripherals::Display::Config display_config = {
    .i2c_block = i2c_config.block,
    .i2c_address = 0x3C,
};

} // namespace Default
} // namespace Doncon::Config

#endif // GLOBALCONFIGURATION_H_ffffjjjjjjkkkkkkddddd