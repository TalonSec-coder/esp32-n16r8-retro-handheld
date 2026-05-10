#pragma once

// Target definition
#define RG_TARGET_NAME              "MY_CUSTOM_S3_GBA"

// Storage
#define RG_STORAGE_ROOT             "/sd"
#define RG_STORAGE_SDSPI_HOST       SPI3_HOST
#define RG_STORAGE_SDSPI_SPEED      SPI_MASTER_FREQ_20M

// Audio (New MAX98357A DAC/Amp Module)
#define RG_AUDIO_USE_INT_DAC        0   
#define RG_AUDIO_USE_EXT_DAC        1   
#define RG_GPIO_SND_I2S_DATA        GPIO_NUM_15 
#define RG_GPIO_SND_I2S_BCK         GPIO_NUM_42
#define RG_GPIO_SND_I2S_WS          GPIO_NUM_41     

// Video (TFT Display - Working Pins + 180 Flip)
#define RG_SCREEN_DRIVER            0
#define RG_SCREEN_HOST              SPI2_HOST
#define RG_SCREEN_SPEED             SPI_MASTER_FREQ_40M
#define RG_SCREEN_BACKLIGHT         0   // Disabled: powered directly via buck converter
#define RG_SCREEN_WIDTH             320
#define RG_SCREEN_HEIGHT            240
#define RG_SCREEN_ROTATE            0
#define RG_SCREEN_INIT()                                                                                         \
    ILI9341_CMD(0xCF, 0x00, 0xc3, 0x30);                                                                         \
    ILI9341_CMD(0xED, 0x64, 0x03, 0x12, 0x81);                                                                   \
    ILI9341_CMD(0xE8, 0x85, 0x00, 0x78);                                                                         \
    ILI9341_CMD(0xCB, 0x39, 0x2c, 0x00, 0x34, 0x02);                                                             \
    ILI9341_CMD(0xF7, 0x20);                                                                                     \
    ILI9341_CMD(0xEA, 0x00, 0x00);                                                                               \
    ILI9341_CMD(0xC0, 0x1B);                                                                                     \
    ILI9341_CMD(0xC1, 0x12);                                                                                     \
    ILI9341_CMD(0xC5, 0x32, 0x3C);                                                                               \
    ILI9341_CMD(0xC7, 0x91);                                                                                     \
    ILI9341_CMD(0x36, 0xA8);                 /* 180 Degree Flip Fix */                                           \
    ILI9341_CMD(0xB1, 0x00, 0x10);                                                                               \
    ILI9341_CMD(0xB6, 0x0A, 0xA2);                                                                               \
    ILI9341_CMD(0xF6, 0x01, 0x30);                                                                               \
    ILI9341_CMD(0xF2, 0x00);                                                                                     \
    ILI9341_CMD(0x26, 0x01);                                                                                     \
    ILI9341_CMD(0xE0, 0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1, 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00); \
    ILI9341_CMD(0xE1, 0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1, 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F);

// Display Pins
#define RG_GPIO_LCD_MISO            GPIO_NUM_16 
#define RG_GPIO_LCD_MOSI            GPIO_NUM_17 
#define RG_GPIO_LCD_CLK             GPIO_NUM_18 
#define RG_GPIO_LCD_CS              GPIO_NUM_5  
#define RG_GPIO_LCD_DC              GPIO_NUM_4  
#define RG_GPIO_LCD_RST             GPIO_NUM_2  
#undef RG_GPIO_LCD_BCKL             // Removed dummy pin to prevent PWM conflicts

// SD Card Pins
#define RG_GPIO_SDSPI_MISO          GPIO_NUM_9
#define RG_GPIO_SDSPI_MOSI          GPIO_NUM_11
#define RG_GPIO_SDSPI_CLK           GPIO_NUM_13
#define RG_GPIO_SDSPI_CS            GPIO_NUM_10

// Input (Buttons)
#undef RG_GAMEPAD_ADC_MAP
#define RG_GAMEPAD_GPIO_MAP {\
    {RG_KEY_UP,     .num = GPIO_NUM_1,  .pullup = 1, .level = 0},\
    {RG_KEY_DOWN,   .num = GPIO_NUM_3,  .pullup = 1, .level = 0},\
    {RG_KEY_LEFT,   .num = GPIO_NUM_47, .pullup = 1, .level = 0},\
    {RG_KEY_RIGHT,  .num = GPIO_NUM_21, .pullup = 1, .level = 0},\
    {RG_KEY_A,      .num = GPIO_NUM_6,  .pullup = 1, .level = 0},\
    {RG_KEY_B,      .num = GPIO_NUM_7,  .pullup = 1, .level = 0},\
    {RG_KEY_SELECT, .num = GPIO_NUM_8,  .pullup = 1, .level = 0},\
    {RG_KEY_START,  .num = GPIO_NUM_0,  .pullup = 1, .level = 0},\
    {RG_KEY_MENU,   .num = GPIO_NUM_38, .pullup = 1, .level = 0},\
}

#define RG_BATTERY_DRIVER           0
#undef RG_GPIO_LED                  // Removed dummy pin