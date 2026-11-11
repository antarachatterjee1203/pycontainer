#!/usr/bin/env python3
"""
PyContainer - Diagnostic & System Compatibility Check
"""
import os
import sys
import ctypes

def check_system():
    print("=" * 60)
    print("  PyContainer: Host System Diagnostic Check")
    print("=" * 60)

    euid = os.geteuid()
    print(f"[*] Effective User ID : {euid}", end=" ")
    if euid == 0:
        print("[OK] (Running as root)")
    else:
        print("[WARNING] (Run with 'sudo' for kernel system calls)")

    uname = os.uname()
    print(f"[*] Linux OS Kernel   : {uname.sysname} {uname.release} ({uname.machine})")

    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        print("[*] C Standard Library : libc.so.6 loaded successfully [OK]")
    except Exception as err:
        print(f"[-] C Standard Library : Failed to load libc ({err}) [FAIL]")

    cgroup_path = "/sys/fs/cgroup"
    controllers_file = os.path.join(cgroup_path, "cgroup.controllers")
    if os.path.exists(controllers_file):
        with open(controllers_file, "r") as f:
            controllers = f.read().strip()
        print(f"[*] Cgroups v2 Support : Detected at {cgroup_path} [OK]")
        print(f"[*] Active Controllers : {controllers}")
    else:
        print("[-] Cgroups v2 Support : Unified hierarchy not found [FAIL]")

    if hasattr(libc, "unshare"):
        print("[*] Syscall Check      : unshare() symbol resolved in libc [OK]")
    else:
        print("[-] Syscall Check      : unshare() symbol missing [FAIL]")
    print("=" * 60)

if __name__ == "__main__":
    check_system()
