#!/usr/bin/env python3
"""
PyContainer - Validation & Demo Test Harness
"""
import os
import sys

def test_pid():
    pid = os.getpid()
    print(f"\n[TEST 1] Process ID Namespace Verification:")
    print(f" -> Current Process PID: {pid}")
    if pid == 1:
        print(" -> SUCCESS: Process is virtualized as PID 1 (Container Init).")
    else:
        print(f" -> SUB-PROCESS: PID is {pid} (Child of PID 1).")

def test_fs():
    print(f"\n[TEST 2] Filesystem Jail (chroot) Verification:")
    root_items = os.listdir("/")
    print(f" -> Root '/' directory entries: {root_items}")
    if "home" in root_items and not os.path.exists("/home/ubuntu"):
        print(" -> SUCCESS: Confined to guest rootfs. Host partitions are invisible.")

def test_memory_oom():
    print(f"\n[TEST 3] Cgroups v2 Memory Boundary Stress Test:")
    print(" -> Allocating 100 MB of memory...")
    try:
        chunk = bytearray(100 * 1024 * 1024)
        print(f" -> Allocated {len(chunk) / (1024*1024)} MB successfully (Limit > 100MB).")
    except MemoryError:
        print(" -> Intercepted: MemoryError thrown before kernel kill.")

if __name__ == "__main__":
    test_pid()
    test_fs()
    if "--oom" in sys.argv:
        test_memory_oom()
