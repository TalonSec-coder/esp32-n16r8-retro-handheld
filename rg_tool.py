#!/usr/bin/env python3
import argparse
import subprocess
import shutil
import glob
import math
import sys
import re
import os
import struct

DEFAULT_TARGET = os.getenv("RG_TOOL_TARGET", "odroid-go")
DEFAULT_BAUD = os.getenv("RG_TOOL_BAUD", "1152000")
DEFAULT_PORT = os.getenv("RG_TOOL_PORT", "COM3")
DEFAULT_APPS = os.getenv("RG_TOOL_APPS", "launcher retro-core prboom-go gbsp gwenesis fmsx")
PROJECT_NAME = os.getenv("PROJECT_NAME", "Retro-Go")
PROJECT_ICON = os.getenv("PROJECT_ICON", "assets/icon.raw")
PROJECT_APPS = {
  # Project name  Type, SubType, Size
  'launcher':     [0, 0, 983040],
  'retro-core':   [0, 0, 983040],
  'prboom-go':    [0, 0, 851968],
  'gwenesis':     [0, 0, 1572864],
  'fmsx':         [0, 0, 589824],
  'gbsp':         [0, 0, 851968],
}

try:
    PROJECT_VER = os.getenv("PROJECT_VER") or subprocess.check_output(
        "git describe --tags --abbrev=5 --dirty --always", shell=True
    ).decode().rstrip()
except:
    PROJECT_VER = "unknown"
FW_FORMAT = "none"

TARGETS = []
for t in glob.glob("components/retro-go/targets/*/config.h"):
    TARGETS.append(os.path.basename(os.path.dirname(t)))

IDF_TARGET = os.getenv("IDF_TARGET", "esp32")
IDF_PATH = os.getenv("IDF_PATH")
if not IDF_PATH:
    exit("IDF_PATH is not defined. Are you running inside esp-idf environment?")

if os.name == 'nt':
    IDF_PY = os.path.join(IDF_PATH, "tools", "idf.py")
    IDF_MONITOR_PY = os.path.join(IDF_PATH, "tools", "idf_monitor.py")
    ESPTOOL_PY = os.path.join(IDF_PATH, "components", "esptool_py", "esptool", "esptool.py")
    PARTTOOL_PY = os.path.join(IDF_PATH, "components", "partition_table", "parttool.py")
    GEN_ESP32PART_PY = os.path.join(IDF_PATH, "components", "partition_table", "gen_esp32part.py")
else:
    IDF_PY = "idf.py"
    IDF_MONITOR_PY = "idf_monitor.py"
    ESPTOOL_PY = "esptool.py"
    PARTTOOL_PY = "parttool.py"
    GEN_ESP32PART_PY = "gen_esp32part.py"
MKFW_PY = os.path.join("tools", "mkfw.py")


def run(cmd, cwd=None, check=True):
    print(f"Running command: {' '.join(cmd)}")
    if os.name == 'nt' and cmd[0].endswith(".py"):
        return subprocess.run(["python", *cmd], shell=True, cwd=cwd, check=check)
    return subprocess.run(cmd, shell=False, cwd=cwd, check=check)


def build_firmware(output_file, apps, fw_format="odroid-go", fatsize=0):
    print("Building firmware with: %s\n" % " ".join(apps))
    args = [MKFW_PY, output_file, f"{PROJECT_NAME} {PROJECT_VER}", PROJECT_ICON]

    if fw_format == "esplay":
        args.append("--esplay")

    for app in apps:
        part = PROJECT_APPS[app]
        args += [str(part[0]), str(part[1]), str(part[2]), app, os.path.join(app, "build", app + ".bin")]

    run(args)


def parse_size(value):
    """Parse sizes such as 8M, 10M, 512K or plain bytes."""
    if value is None or value == 0:
        return 0
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMG]?)B?\s*", str(value), re.IGNORECASE)
    if not match:
        raise ValueError("Invalid size: %s" % value)
    number = float(match.group(1))
    unit = match.group(2).upper()
    multiplier = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}[unit]
    return int(number * multiplier)


def _fat16_short_name(long_name, used_names):
    """Return deterministic 8.3 names for the built-in ROM catalog."""
    aliases = {
        "Sonic The Hedgehog (USA, Europe).md": b"SONIC   MD ",
        "Super Mario Advance (USA, Europe).gba": b"MARIO   GBA",
        "doom1.wad": b"DOOM    WAD",
    }
    if long_name in aliases:
        candidate = aliases[long_name]
        if candidate not in used_names:
            return candidate

    stem, ext = os.path.splitext(os.path.basename(long_name))
    stem = re.sub(r"[^A-Za-z0-9]", "", stem).upper() or "ROM"
    ext = re.sub(r"[^A-Za-z0-9]", "", ext[1:]).upper()[:3]
    stem = stem[:8]
    candidate = (stem.ljust(8) + ext.ljust(3)).encode("ascii")
    if candidate not in used_names:
        return candidate

    for index in range(1, 100):
        suffix = str(index)
        base = stem[:8-len(suffix)] + suffix
        candidate = (base.ljust(8) + ext.ljust(3)).encode("ascii")
        if candidate not in used_names:
            return candidate

    raise RuntimeError("Unable to create unique FAT 8.3 alias for %s" % long_name)

def _fat16_lfn_entries(long_name, short_name):
    """Return LFN directory entries for a FAT16 root directory."""
    encoded = long_name.encode("utf-16le")
    code_units = list(struct.unpack("<%dH" % (len(encoded) // 2), encoded))
    checksum = 0
    for value in short_name:
        checksum = ((checksum & 1) << 7) + (checksum >> 1) + value
        checksum &= 0xFF

    chunks = [code_units[i:i + 13] for i in range(0, len(code_units), 13)]
    entries = []
    for index in range(len(chunks) - 1, -1, -1):
        units = list(chunks[index])
        if len(units) < 13:
            units.append(0x0000)
        units += [0xFFFF] * (13 - len(units))
        ordinal = index + 1
        if index == len(chunks) - 1:
            ordinal |= 0x40

        entry = bytearray(32)
        entry[0] = ordinal
        struct.pack_into("<5H", entry, 1, *units[0:5])
        entry[11] = 0x0F
        entry[12] = 0
        entry[13] = checksum
        struct.pack_into("<6H", entry, 14, *units[5:11])
        struct.pack_into("<2H", entry, 28, *units[11:13])
        entries.append(bytes(entry))
    return entries


def _fat12_set_entry(fat, cluster, value):
    """Write one 12-bit FAT entry."""
    offset = cluster + (cluster // 2)
    value &= 0x0FFF
    if cluster & 1:
        fat[offset] = (fat[offset] & 0x0F) | ((value << 4) & 0xF0)
        fat[offset + 1] = (value >> 4) & 0xFF
    else:
        fat[offset] = value & 0xFF
        fat[offset + 1] = (fat[offset + 1] & 0xF0) | ((value >> 8) & 0x0F)


def _build_fat16_image(output_file, file_specs, image_size):
    """Build a FAT12 image using 4096-byte raw-flash sectors.

    The directory tree mirrors a normal Retro-Go SD card:
      /retro-go/roms/<app>/<rom>
    """
    sector_size = 4096
    if image_size % sector_size:
        raise RuntimeError("FAT image size must be aligned to the flash sector size")
    total_sectors = image_size // sector_size
    reserved_sectors = 1
    fat_count = 2
    root_entries = 128
    root_dir_sectors = (root_entries * 32 + sector_size - 1) // sector_size
    sectors_per_cluster = 1

    fat_sectors = 1
    for _ in range(16):
        data_sectors = total_sectors - reserved_sectors - fat_count * fat_sectors - root_dir_sectors
        cluster_count = data_sectors // sectors_per_cluster
        needed = (((cluster_count + 2) * 3) + 1) // 2
        needed = (needed + sector_size - 1) // sector_size
        if needed == fat_sectors:
            break
        fat_sectors = needed
    if cluster_count > 4084:
        raise RuntimeError("Configured image does not fit FAT12 limits")

    image = bytearray(b"\xFF" * image_size)
    image[0:3] = b"\xEB\x3C\x90"
    image[3:11] = b"MSDOS5.0"
    struct.pack_into("<H", image, 11, sector_size)
    image[13] = sectors_per_cluster
    struct.pack_into("<H", image, 14, reserved_sectors)
    image[16] = fat_count
    struct.pack_into("<H", image, 17, root_entries)
    struct.pack_into("<H", image, 19, total_sectors)
    image[21] = 0xF8
    struct.pack_into("<H", image, 22, fat_sectors)
    struct.pack_into("<H", image, 24, 32)
    struct.pack_into("<H", image, 26, 64)
    image[36] = 0x80
    image[38] = 0x29
    struct.pack_into("<I", image, 39, 0x5254474F)
    image[43:54] = b"RETROGO    "
    image[54:62] = b"FAT12   "
    # The boot-sector signature belongs at the end of the logical sector.\n    # This image uses 4096-byte flash/FAT sectors, so writing it at 510\n    # leaves the FAT filesystem without a valid 0x55AA signature.\n    image[sector_size - 2:sector_size] = b"\x55\xAA"

    fat_offset = reserved_sectors * sector_size
    fat_bytes = fat_sectors * sector_size
    fat = bytearray(fat_bytes)
    _fat12_set_entry(fat, 0, 0xFF8)
    _fat12_set_entry(fat, 1, 0xFFF)

    root_offset = (reserved_sectors + fat_count * fat_sectors) * sector_size
    data_offset = root_offset + root_dir_sectors * sector_size
    root = bytearray(root_dir_sectors * sector_size)

    def short_name(name):
        aliases = {
            "retro-go": b"RETRO-GO   ",
            "roms": b"ROMS       ",
            "gba": b"GBA        ",
            "md": b"MD         ",
            "doom": b"DOOM       ",
        }
        if name.lower() in aliases:
            return aliases[name.lower()]
        stem, ext = os.path.splitext(os.path.basename(name))
        stem = re.sub(r"[^A-Za-z0-9]", "", stem).upper() or "ROM"
        ext = re.sub(r"[^A-Za-z0-9]", "", ext[1:]).upper()[:3]
        return (stem[:8].ljust(8) + ext.ljust(3)).encode("ascii")

    normalized = []
    for rel, src in file_specs:
        parts = [p for p in rel.replace("\\", "/").strip("/").split("/") if p]
        if len(parts) < 2:
            raise RuntimeError("ROM path must include a directory: %s" % rel)
        normalized.append((parts, src))

    dirs = {tuple()}
    for parts, _src in normalized:
        for n in range(1, len(parts)):
            dirs.add(tuple(parts[:n]))

    next_cluster = 2
    dir_cluster = {}
    for d in sorted(dirs, key=lambda x: (len(x), x)):
        dir_cluster[d] = next_cluster
        _fat12_set_entry(fat, next_cluster, 0xFFF)
        next_cluster += 1

    children = {d: [] for d in dirs}
    for parts, src in normalized:
        children[tuple(parts[:-1])].append(("file", parts[-1], src, tuple(parts)))
    for d in dirs:
        if d:
            children[tuple(d[:-1])].append(("dir", d[-1], None, d))

    file_meta = {}
    for kind, name, src, full in sum(children.values(), []):
        if kind != "file":
            continue
        size = os.path.getsize(src)
        clusters = max(1, (size + sector_size - 1) // sector_size)
        if next_cluster + clusters - 2 > cluster_count:
            raise RuntimeError("FAT image is too small for bundled files")
        first = next_cluster
        for cluster in range(first, first + clusters):
            _fat12_set_entry(fat, cluster, 0xFFF if cluster == first + clusters - 1 else cluster + 1)
        with open(src, "rb") as fp:
            remaining = size
            cluster = first
            while remaining:
                chunk = fp.read(sector_size)
                if not chunk:
                    raise RuntimeError("Unexpected EOF while packaging %s" % src)
                off = data_offset + (cluster - 2) * sector_size
                image[off:off + len(chunk)] = chunk
                remaining -= len(chunk)
                cluster += 1
        file_meta[full] = (first, size)
        next_cluster += clusters

    def add_entry(buf, pos, name, attr, cluster, size=0, lfn=True):
        short = short_name(name)
        if lfn and attr == 0x20:
            for e in _fat16_lfn_entries(name, short):
                if pos + 32 > len(buf) - 32:
                    raise RuntimeError("Directory is full")
                buf[pos:pos+32] = e
                pos += 32
        ent = bytearray(32)
        ent[0:11] = short
        ent[11] = attr
        struct.pack_into("<H", ent, 26, cluster)
        if attr == 0x20:
            struct.pack_into("<I", ent, 28, size)
        buf[pos:pos+32] = ent
        return pos + 32

    def write_dir(d):
        buf = root if not d else bytearray(sector_size)
        pos = 0
        if d:
            for dot, cl in [(".", dir_cluster[d]), ("..", dir_cluster[tuple(d[:-1])] if len(d) > 1 else 0)]:
                ent = bytearray(32)
                ent[0:11] = (dot + " " * 11)[:11].encode("ascii")
                ent[11] = 0x10
                struct.pack_into("<H", ent, 26, cl)
                buf[pos:pos+32] = ent
                pos += 32
        for kind, name, src, full in children.get(d, []):
            if kind == "dir":
                pos = add_entry(buf, pos, name, 0x10, dir_cluster[full], lfn=False)
            else:
                first, size = file_meta[full]
                pos = add_entry(buf, pos, name, 0x20, first, lfn=True)
                struct.pack_into("<I", buf, pos-4, size)
        if d:
            off = data_offset + (dir_cluster[d] - 2) * sector_size
            image[off:off+sector_size] = buf

    for d in sorted(dirs, key=lambda x: (len(x), x), reverse=True):
        write_dir(d)
    write_dir(tuple())

    image[fat_offset:fat_offset + fat_bytes] = fat
    image[fat_offset + fat_bytes:fat_offset + 2 * fat_bytes] = fat
    with open(output_file, "wb") as dst:
        dst.write(image)


def build_image(output_file, apps, img_format="esp32", fatsize=0):
    print("Building image with: %s\n" % " ".join(apps))
    image_data = bytearray(b"\xFF" * 0x10000)
    table_ota = 0
    table_csv = [
        "nvs, data, nvs, 36864, 16384",
        "otadata, data, ota, 53248, 8192",
        "phy_init, data, phy, 61440, 4096",
    ]

    for app in apps:
        with open(os.path.join(app, "build", app + ".bin"), "rb") as f:
            data = f.read()
        part_size = max(PROJECT_APPS[app][2], math.ceil(len(data) / 0x10000) * 0x10000)
        table_csv.append("%s, app, ota_%d, %d, %d" % (app, table_ota, len(image_data), part_size))
        table_ota += 1
        image_data += data + b"\xFF" * (part_size - len(data))

    if fatsize:
        # Bundle ROMs exactly where the original Retro-Go launcher expects them.
        fat_size = parse_size(fatsize)
        root = os.path.abspath(".")
        rom_specs = [
            ("retro-go/roms/md/Sonic The Hedgehog (USA, Europe).md",
             os.path.join(root, "Sonic The Hedgehog (USA, Europe).md")),
            ("retro-go/roms/gba/Super Mario Advance (USA, Europe).gba",
             os.path.join(root, "Super Mario Advance (USA, Europe).gba")),
            ("retro-go/roms/doom/doom1.wad",
             os.path.join(root, "prboom-go", "components", "prboom", "data", "doom1.wad")),
        ]
        missing = [src for _rel, src in rom_specs if not os.path.isfile(src)]
        if missing:
            raise RuntimeError("Required bundled ROM file(s) missing: %s" % ", ".join(missing))
        fat_image = os.path.abspath("storage_fat.bin")
        _build_fat16_image(fat_image, rom_specs, fat_size)
        with open(fat_image, "rb") as f:
            image_data += f.read()
        table_csv.append("vfs, data, fat, %d, %d" % (len(image_data) - fat_size, fat_size))

    print("Generating partition table...")
    with open("partitions.csv", "w") as f:
        f.write("\n".join(table_csv))
    run([GEN_ESP32PART_PY, "partitions.csv", "partitions.bin"])
    with open("partitions.bin", "rb") as f:
        table_bin = f.read()

    print("Building bootloader...")
    bootloader_file = os.path.join(os.getcwd(), list(apps)[0], "build", "bootloader", "bootloader.bin")
    if not os.path.exists(bootloader_file):
        run([IDF_PY, "bootloader"], cwd=os.path.join(os.getcwd(), list(apps)[0]))
    with open(bootloader_file, "rb") as f:
        bootloader_bin = f.read()

    if img_format == "esp32s3":
        image_data[0x0000:0x0000+len(bootloader_bin)] = bootloader_bin
        image_data[0x8000:0x8000+len(table_bin)] = table_bin
    elif img_format == "esp32p4":
        image_data[0x2000:0x2000+len(bootloader_bin)] = bootloader_bin
        image_data[0x8000:0x8000+len(table_bin)] = table_bin
    else:
        image_data[0x1000:0x1000+len(bootloader_bin)] = bootloader_bin
        image_data[0x8000:0x8000+len(table_bin)] = table_bin

    with open(output_file, "wb") as f:
        f.write(image_data)

    print("\nPartition table:")
    print("\n".join(table_csv))
    print("\nSaved image '%s' (%d bytes)\n" % (output_file, len(image_data)))


def clean_app(app):
    print("Cleaning up app '%s'..." % app)
    try:
        os.unlink(os.path.join(app, "sdkconfig"))
        os.unlink(os.path.join(app, "sdkconfig.old"))
    except:
        pass
    try:
        shutil.rmtree(os.path.join(app, "build"))
    except:
        pass
    print("Done.\n")


def build_app(app, device_type, with_profiling=False, no_networking=False, is_release=False):
    print("Building app '%s'" % app)
    args = [IDF_PY, "app"]
    args.append(f"-DRG_PROJECT_APP={app}")
    args.append(f"-DRG_PROJECT_VER={PROJECT_VER}")
    args.append(f"-DRG_BUILD_TARGET=RG_TARGET_{re.sub(r'[^A-Z0-9]', '_', device_type.upper())}")
    args.append(f"-DRG_BUILD_RELEASE={1 if is_release else 1}")
    args.append(f"-DRG_ENABLE_PROFILING={1 if with_profiling else 0}")
    args.append(f"-DRG_ENABLE_NETWORKING={0 if no_networking else 1}")
    with open("partitions.csv", "w") as f:
        f.write("# This table isn't used, it's just needed to avoid esp-idf build failures.\n")
        f.write("dummy, app, ota_0, 65536, 3145728\n")
    run(args, cwd=os.path.join(os.getcwd(), app))
    print("Done.\n")


def flash_app(app, port, baudrate=1152000):
    os.putenv("ESPTOOL_CHIP", IDF_TARGET)
    os.putenv("ESPTOOL_BAUD", str(baudrate))
    os.putenv("ESPTOOL_PORT", port)
    if not os.path.exists("partitions.bin"):
        print("Reading device's partition table...")
        run([ESPTOOL_PY, "read_flash", "0x8000", "0x1000", "partitions.bin"], check=False)
        run([GEN_ESP32PART_PY, "partitions.bin"], check=False)
    app_bin = os.path.join(app, "build", app + ".bin")
    print(f"Flashing '{app_bin}' to port {port}")
    run([PARTTOOL_PY, "--partition-table-file", "partitions.bin", "write_partition", "--partition-name", app, "--input", app_bin])
    print("Done.\n")


def flash_image(image_file, port, baudrate=1152000):
    os.putenv("ESPTOOL_CHIP", IDF_TARGET)
    os.putenv("ESPTOOL_BAUD", str(baudrate))
    os.putenv("ESPTOOL_PORT", port)
    print(f"Flashing image file '{image_file}' to {port}")
    run([ESPTOOL_PY, "write_flash", "--flash_size", "detect", "0x0", image_file])
    print("Done.\n")


def monitor_app(app, port, baudrate=115200):
    print(f"Starting monitor for app {app} on port {port}")
    elf_file = os.path.join(os.getcwd(), app, "build", app + ".elf")
    if os.path.exists(elf_file):
        run([IDF_MONITOR_PY, "--port", port, elf_file])
    else:
        run([IDF_MONITOR_PY, "--port", port, "-d", sys.argv[0]])


parser = argparse.ArgumentParser(description="Retro-Go build tool")
parser.add_argument("command", choices=["build-fw", "build-img", "release", "build", "clean", "flash", "monitor", "run", "profile", "install"])
parser.add_argument("apps", nargs="*", default="all", choices=["all"] + list(PROJECT_APPS.keys()))
parser.add_argument("--target", default=DEFAULT_TARGET, choices=set(TARGETS), help="Device to target")
parser.add_argument("--no-networking", action="store_const", const=True, help="Build without networking support")
parser.add_argument("--port", default=DEFAULT_PORT, help="Serial port to use for flash and monitor")
parser.add_argument("--baud", default=DEFAULT_BAUD, help="Serial baudrate to use for flashing")
parser.add_argument("--fatsize", help="Add FAT storage partition of provided size (500K, 5M,...) to the built image.")
args = parser.parse_args()

if os.path.exists(f"components/retro-go/targets/{args.target}/env.py"):
    with open(f"components/retro-go/targets/{args.target}/env.py", "rb") as f:
        prev_idf_target = os.getenv("IDF_TARGET")
        exec(f.read())
        if os.getenv("IDF_TARGET") != prev_idf_target:
            IDF_TARGET = os.getenv("IDF_TARGET")

if os.path.exists(f"components/retro-go/targets/{args.target}/sdkconfig"):
    os.putenv("SDKCONFIG_DEFAULTS", os.path.abspath(f"components/retro-go/targets/{args.target}/sdkconfig"))
os.putenv("IDF_TARGET", IDF_TARGET)

command = args.command
apps = DEFAULT_APPS.split() if "all" in args.apps else args.apps
apps = [app for app in PROJECT_APPS.keys() if app in apps]

try:
    if command in ["build-fw", "build-img", "release", "install"] and "launcher" not in apps:
        print("\nWARNING: The launcher is mandatory for those apps and will be included!\n")
        apps.insert(0, "launcher")

    if command in ["clean", "release"]:
        print("=== Step: Cleaning ===\n")
        for app in apps:
            clean_app(app)

    if command in ["build", "build-fw", "build-img", "release", "run", "profile", "install"]:
        print("=== Step: Building ===\n")
        for app in apps:
            build_app(app, args.target, command == "profile", args.no_networking, command == "release")

    if command in ["build-fw", "release"]:
        print("=== Step: Packing ===\n")
        if FW_FORMAT in ["odroid", "esplay"]:
            fw_file = ("%s_%s_%s.fw" % (PROJECT_NAME, PROJECT_VER, args.target)).lower()
            build_firmware(fw_file, apps, FW_FORMAT, args.fatsize)
        else:
            print("Device doesn't support fw format, try build-img!")

    if command in ["build-img", "release", "install"]:
        print("=== Step: Packing ===\n")
        img_file = ("%s_%s_%s.img" % (PROJECT_NAME, PROJECT_VER, args.target)).lower()
        build_image(img_file, apps, IDF_TARGET, args.fatsize)

    if command in ["install"]:
        print("=== Step: Flashing entire image to device ===\n")
        img_file = ("%s_%s_%s.img" % (PROJECT_NAME, PROJECT_VER, args.target)).lower()
        flash_image(img_file, args.port, args.baud)

    if command in ["flash", "run", "profile"]:
        print("=== Step: Flashing ===\n")
        try: os.unlink("partitions.bin")
        except: pass
        for app in apps:
            flash_app(app, args.port, args.baud)

    if command in ["monitor", "run", "profile"]:
        print("=== Step: Monitoring ===\n")
        monitor_app(apps[0] if len(apps) else "none", args.port)

    print("All done!")

except KeyboardInterrupt as e:
    exit("\n")

except Exception as e:
    exit(f"\nTask failed: {e}")
