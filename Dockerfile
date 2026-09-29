FROM espressif/idf:release-v4.4

WORKDIR /app

ADD . /app

# ESP-IDF 4.4 does not ship a host FAT image generator.\n# Install the standard Linux FAT tools used by the image packer.\nRUN apt-get update && apt-get install -y --no-install-recommends dosfstools mtools && rm -rf /var/lib/apt/lists/*

# Apply patches
RUN cd /opt/esp/idf && \
	patch --ignore-whitespace -p1 -i "/app/tools/patches/panic-hook (esp-idf 4).diff" && \
	patch --ignore-whitespace -p1 -i "/app/tools/patches/sdcard-fix (esp-idf 4).diff"

# Build
SHELL ["/bin/bash", "-c"]
RUN . /opt/esp/idf/export.sh && \
	python rg_tool.py --target=esp32-s3-st7735 --fatsize=10M release
