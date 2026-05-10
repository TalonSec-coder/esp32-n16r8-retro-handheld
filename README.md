# 🎮 Custom ESP32-S3 Retro-Go Handheld (GBA Edition)

A custom DIY retro gaming handheld built around the **ESP32-S3 (8MB Octal PSRAM)** and the experimental **Retro-Go 1.4x-GBA** branch. 

This repository contains heavily modified firmware designed to stabilize Game Boy Advance emulation on the ESP32-S3. It features custom C-code rewrites to fix broken BSON save states, fixes for Octal PSRAM bootloops, UI asset corrections, and specifically targets true **I2S Digital Audio (MAX98357A)** to prevent hardware brownouts commonly caused by raw PDM setups.

---

## ✨ Features & Fixes in this Build
*   **GBA Emulation on ESP32-S3:** Runs Game Boy, GBC, NES, SMS, Game Gear, Genesis (60 FPS), and Game Boy Advance (~30 FPS via forced frameskip).
*   **True I2S Audio:** Switched from raw PDM to an external MAX98357A I2S DAC. This prevents the "Brownout Loop" crash caused by feeding 1.65V DC Bias into standard analog amplifiers.
*   **Fixed GBA Saves (SRAM & States):** The base 1.4x branch stripped standard Libretro saves. Rewrote `main.c` to manually flush `gamepak_backup` (SRAM) to the SD card and hooked native BSON `gba_save_state` functions into Retro-Go's UI handler.
*   **Optimized Performance:** CPU locked to 240MHz, GBA audio processing reduced to 22,050Hz to save CPU overhead, and hardware `frameskip` locked to 1 for a stable, playable GBA experience.
*   **Octal PSRAM Stability:** Fixed an ESP-IDF compiler bug where `sdkconfig` rebuilds would default to Quad PSRAM and cause infinite hourglass bootloops.
*   **Fixed UI Assets:** Restored the `gen_images.py` C-array injection to fix the "Red Square" missing logo bug for GBA games.

---

## 🛠️ Hardware Requirements & Pinout

This build is pre-configured for the following hardware setup. If your wiring differs, you can change the pins in `components/retro-go/targets/esp32-s3-devkit/config.h`.

| Component | Pin Name | ESP32-S3 GPIO | Notes |
| :--- | :--- | :--- | :--- |
| **Display (ILI9341)** | MISO / MOSI / CLK | 16 / 17 / 18 | SPI2_HOST (40MHz) |
| | CS / DC / RST | 5 / 4 / 2 | Backlight wired directly to 3.3V/Buck |
| **MicroSD Card** | MISO / MOSI / CLK | 9 / 11 / 13 | SPI3_HOST (20MHz for stable menus) |
| | CS | 10 | |
| **Audio (MAX98357A)** | DIN (Data) | 15 | *Do not use an analog PAM8403!* |
| | BCLK (Clock) | 42 | |
| | LRC (WS) | 41 | |
| **Gamepad** | D-PAD (U/D/L/R) | 1 / 3 / 47 / 21 | Pulled HIGH internally (Trigger on LOW) |
| | A / B / SEL / START | 6 / 7 / 8 / 0 | |
| | MENU | 38 | Opens the Retro-Go OS Menu |

---

## 🚀 How to Build and Flash

### 1. Prerequisites
You must have **ESP-IDF v5.5.4** installed and active in your terminal. 

### 2. Compiling the Firmware
Clone this repository, open your terminal in the root folder, and run the following commands to build the UI launcher and emulators:

```cmd
python rg_tool.py --target esp32-s3-devkit build launcher retro-core gwenesis gbsp
3. Stitch and Flash
Stitch the compiled binaries into a single image file:
code
Cmd
python rg_tool.py --target esp32-s3-devkit build-img launcher retro-core gwenesis gbsp
Flash the image to your ESP32-S3 (replace COM17 with your actual COM port):
code
Cmd
python -m esptool --chip esp32s3 --port COM17 --baud 921600 write_flash 0x0 retro-go_v5.5.4_esp32-s3-devkit.img
💾 SD Card Setup
Retro-Go relies heavily on the SD card. Make sure it is formatted to FAT32.
Create a folder named retro-go on the root of your SD card.
Inside retro-go, create two folders: roms and system.
Crucial GBA Step: You must place a valid Game Boy Advance BIOS file named exactly gba_bios.bin inside the SD:/retro-go/system/ folder. The emulator will crash or lag heavily without it.
Place your game ROMs inside their respective folders (e.g., SD:/retro-go/roms/gba/).
⚠️ Known Limitations
GBA Framerate: Emulating a 32-bit console on a microcontroller is pushing the absolute physical limits of the ESP32-S3. frameskip is permanently set to 1 in code to maintain a playable 30 FPS. Action games will look slightly choppy, but input and logic speed will be accurate.
Filter Settings: For maximum performance, press the MENU button in-game and ensure "Video Filter" is set to OFF. Bilinear filtering costs too much CPU overhead on GBA titles.
