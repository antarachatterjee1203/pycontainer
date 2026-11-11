#!/bin/bash
set -e

ROOTFS_DIR="./alpine_rootfs"
ALPINE_URL="https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/alpine-minirootfs-3.19.1-x86_64.tar.gz"
ARCHIVE="alpine_minirootfs.tar.gz"

echo "[*] Setting up Alpine Linux RootFS for PyContainer..."

if [ -d "$ROOTFS_DIR" ]; then
    echo "[!] Directory '$ROOTFS_DIR' already exists. Skipping download."
    exit 0
fi

mkdir -p "$ROOTFS_DIR"

echo "[*] Downloading Alpine MinirootFS..."
wget -q --show-progress "$ALPINE_URL" -O "$ARCHIVE"

echo "[*] Extracting RootFS hierarchy..."
tar -xzf "$ARCHIVE" -C "$ROOTFS_DIR"
rm "$ARCHIVE"

mkdir -p "$ROOTFS_DIR/proc"
mkdir -p "$ROOTFS_DIR/dev"
mkdir -p "$ROOTFS_DIR/sys"

echo "[+] RootFS setup complete at '$ROOTFS_DIR'."
