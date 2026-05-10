#include <rg_system.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../components/gbsp-libretro/common.h"
#include "../components/gbsp-libretro/memmap.h"
#include "../components/gbsp-libretro/gba_memory.h"
#include "../components/gbsp-libretro/gba_cc_lut.h"
#include "../components/gbsp-libretro/savestate.h"

// PERFORMANCE BOOST: 22050Hz saves CPU (Safe now that we have a real I2S DAC!)
#define AUDIO_SAMPLE_RATE 22050
#define AUDIO_BUFFER_LENGTH (AUDIO_SAMPLE_RATE / 60 + 1)

#include "bios.h"

u32 idle_loop_target_pc = 0xFFFFFFFF;
u32 translation_gate_target_pc[MAX_TRANSLATION_GATES];
u32 translation_gate_targets = 0;
boot_mode selected_boot_mode = boot_bios;

u32 skip_next_frame = 0;
int sprite_limit = 1;

gbsp_memory_t *gbsp_memory;

static rg_surface_t *updates[2];
static rg_surface_t *currentUpdate;
static rg_app_t *app;

static char sram_path[256] = {0};

void netpacket_poll_receive() {}
void netpacket_send(uint16_t client_id, const void *buf, size_t len) {}

static bool screenshot_handler(const char *filename, int width, int height)
{
    return rg_surface_save_image_file(currentUpdate, filename, width, height);
}

static bool save_state_handler(const char *filename)
{
    void *data = calloc(1, GBA_STATE_MEM_SIZE);
    if (!data) return false;
    
    gba_save_state(data);
    
    uint32_t real_size = *(uint32_t*)data;
    if (real_size == 0 || real_size > GBA_STATE_MEM_SIZE) {
        real_size = GBA_STATE_MEM_SIZE;
    }

    bool ok = false;
    FILE *f = fopen(filename, "wb");
    if (f) {
        if (fwrite(data, 1, real_size, f) == real_size) {
            ok = true;
        }
        fclose(f);
    }
    
    free(data);
    return ok;
}

static bool load_state_handler(const char *filename)
{
    void *data = calloc(1, GBA_STATE_MEM_SIZE);
    if (!data) return false;

    bool ok = false;
    FILE *f = fopen(filename, "rb");
    if (f) {
        size_t bytes_read = fread(data, 1, GBA_STATE_MEM_SIZE, f);
        fclose(f);
        
        if (bytes_read > 8) {
            ok = gba_load_state(data);
        }
    }
    
    free(data);
    return ok;
}

static void init_sram_path(void)
{
    if (!app || !app->romPath) return;
    
    const char *name = strrchr(app->romPath, '/');
    name = name ? name + 1 : app->romPath;
    
    snprintf(sram_path, sizeof(sram_path), "/sd/retro-go/saves/gba/%s", name);
    
    char *ext = strrchr(sram_path, '.');
    if (ext) {
        strcpy(ext, ".srm");
    } else {
        strcat(sram_path, ".srm");
    }
}

static void save_sram(void)
{
    if (sram_path[0] == '\0') return;
    
    FILE *f = fopen(sram_path, "wb");
    if (f) {
        fwrite(gamepak_backup, 1, sizeof(gamepak_backup), f);
        fclose(f);
    }
}

static void load_sram(void)
{
    if (sram_path[0] == '\0') return;
    
    FILE *f = fopen(sram_path, "rb");
    if (f) {
        fread(gamepak_backup, 1, sizeof(gamepak_backup), f);
        fclose(f);
    }
}

static bool reset_handler(bool hard)
{
    return true;
}

static void event_handler(int event, void *arg)
{
    if (event == RG_EVENT_REDRAW)
    {
        rg_display_submit(currentUpdate, 0);
    }
}

int16_t input_cb(unsigned port, unsigned device, unsigned index, unsigned id)
{
    uint32_t joystick = rg_input_read_gamepad();
    int16_t val = 0;
    if (joystick & RG_KEY_DOWN) val |= (1 << RETRO_DEVICE_ID_JOYPAD_DOWN);
    if (joystick & RG_KEY_UP) val |= (1 << RETRO_DEVICE_ID_JOYPAD_UP);
    if (joystick & RG_KEY_LEFT) val |= (1 << RETRO_DEVICE_ID_JOYPAD_LEFT);
    if (joystick & RG_KEY_RIGHT) val |= (1 << RETRO_DEVICE_ID_JOYPAD_RIGHT);
    if (joystick & RG_KEY_START) val |= (1 << RETRO_DEVICE_ID_JOYPAD_START);
    if (joystick & RG_KEY_SELECT) val |= (1 << RETRO_DEVICE_ID_JOYPAD_SELECT);
    if (joystick & RG_KEY_B) val |= (1 << RETRO_DEVICE_ID_JOYPAD_B);
    if (joystick & RG_KEY_A) val |= (1 << RETRO_DEVICE_ID_JOYPAD_A);
    return val;
}

void set_fastforward_override(bool fastforward) {}

void app_main(void)
{
    const rg_handlers_t handlers = {
        .loadState = &load_state_handler,
        .saveState = &save_state_handler,
        .reset = &reset_handler,
        .screenshot = &screenshot_handler,
        .event = &event_handler,
    };

    app = rg_system_init(AUDIO_SAMPLE_RATE, &handlers, NULL);
    
    // PERFORMANCE BOOST: Skip drawing every other frame
    app->frameskip = 1;  
    
    init_sram_path();

    updates[0] = rg_surface_create(GBA_SCREEN_WIDTH, GBA_SCREEN_HEIGHT + 1, RG_PIXEL_565_LE, MEM_FAST);
    updates[0]->height = GBA_SCREEN_HEIGHT;
    currentUpdate = updates[0];

    gba_screen_pixels = currentUpdate->data;

    gbsp_memory = rg_alloc(sizeof(*gbsp_memory), MEM_ANY);

    libretro_supports_bitmasks = true;
    retro_set_input_state(input_cb);
    init_gamepak_buffer();
    init_sound();

    if (load_bios("/sd/retro-go/system/gba_bios.bin") != 0)
        memcpy(bios_rom, open_gba_bios_rom, sizeof(bios_rom));

    memset(gamepak_backup, 0xff, sizeof(gamepak_backup));
    if (load_gamepak(NULL, app->romPath, FEAT_DISABLE, FEAT_DISABLE, SERIAL_MODE_DISABLED) != 0)
    {
        RG_PANIC("Could not load the game file.");
    }

    load_sram();

    reset_gba();

    while (true)
    {
        rg_audio_sample_t mixbuffer[AUDIO_BUFFER_LENGTH];
        uint32_t joystick = rg_input_read_gamepad();

        if (joystick & (RG_KEY_MENU | RG_KEY_OPTION))
        {
            save_sram();
            
            if (joystick & RG_KEY_MENU)
                rg_gui_game_menu();
            else
                rg_gui_options_menu();
        }

        int64_t start_time = rg_system_timer();

        update_input();
        rumble_frame_reset();

        clear_gamepak_stickybits();
        execute_arm(execute_cycles);

        if (!skip_next_frame)
            rg_display_submit(currentUpdate, 0);

        size_t frames_count = sound_read_samples((s16 *)mixbuffer, AUDIO_BUFFER_LENGTH);

        rg_system_tick(rg_system_timer() - start_time);

        rg_audio_submit(mixbuffer, frames_count);

        if (skip_next_frame == 0)
            skip_next_frame = app->frameskip;
        else if (skip_next_frame > 0)
            skip_next_frame--;
    }

    RG_PANIC("GBsP Ended");
}