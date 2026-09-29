#pragma once

// ESP32-S3 N16R8 + 1.8" ST7735S 128x160
#define RG_TARGET_NAME              "ESP32-S3 N16R8 ST7735S 128x160"

// Internal flash storage. The image builder creates the "vfs" FAT partition.
#define RG_STORAGE_ROOT             "/storage"
#define RG_STORAGE_FLASH_PARTITION  "vfs"

// Audio: passive/active buzzer on GPIO10.
// Retro-Go's buzzer driver uses LEDC channel/timer 0.
#define RG_AUDIO_USE_BUZZER_PIN     GPIO_NUM_10
#define RG_AUDIO_USE_INT_DAC        0
#define RG_AUDIO_USE_EXT_DAC        0

// ST7735S 128x160 SPI display.
#define RG_SCREEN_DRIVER            2   // 2 = ST7735S
#define RG_SCREEN_HOST              SPI2_HOST
#define RG_SCREEN_SPEED             SPI_MASTER_FREQ_26M
#define RG_SCREEN_BACKLIGHT         1
#define RG_SCREEN_WIDTH             160
#define RG_SCREEN_HEIGHT            128
#define RG_SCREEN_ROTATE            0
#define RG_SCREEN_VISIBLE_AREA      {0, 0, 0, 0}
#define RG_SCREEN_SAFE_AREA         {0, 0, 0, 0}

// ST7735S controller-side addressing.
// Most red-board 128x160 modules use 0,0 offsets. These are overrideable for
// modules whose visible glass starts at a non-zero GRAM offset.
#define RG_ST7735_XSTART            0
#define RG_ST7735_YSTART            0
#define RG_ST7735_MADCTL            0x68

#define RG_GPIO_LCD_MISO            GPIO_NUM_NC
#define RG_GPIO_LCD_MOSI            GPIO_NUM_6
#define RG_GPIO_LCD_CLK             GPIO_NUM_5
#define RG_GPIO_LCD_CS              GPIO_NUM_16
#define RG_GPIO_LCD_DC              GPIO_NUM_7
#define RG_GPIO_LCD_RST             GPIO_NUM_15
#define RG_GPIO_LCD_BCKL            GPIO_NUM_4

// Buttons.
#undef RG_GAMEPAD_ADC_MAP
#define RG_GAMEPAD_GPIO_MAP {\
    {RG_KEY_UP,     .num = GPIO_NUM_9,  .pullup = 1, .level = 0},\
    {RG_KEY_DOWN,   .num = GPIO_NUM_11, .pullup = 1, .level = 0},\
    {RG_KEY_LEFT,   .num = GPIO_NUM_12, .pullup = 1, .level = 0},\
    {RG_KEY_RIGHT,  .num = GPIO_NUM_13, .pullup = 1, .level = 0},\
    {RG_KEY_A,      .num = GPIO_NUM_14, .pullup = 1, .level = 0},\
}

// Display defaults: fill the entire panel. This intentionally stretches
// emulator frames when their aspect ratio differs from 128x160.
// The panel image is rotated 180 degrees by ST7735 MADCTL above.
#ifndef RG_DISPLAY_DEFAULT_SCALING
#define RG_DISPLAY_DEFAULT_SCALING RG_DISPLAY_SCALING_FULL
#endif
#define RG_DISPLAY_DEFAULT_FILTER  RG_DISPLAY_FILTER_BOTH

#define RG_BATTERY_DRIVER           0
#undef RG_GPIO_LED
