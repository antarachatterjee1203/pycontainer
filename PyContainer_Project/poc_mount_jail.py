#!/usr/bin/env python3
"""
PyContainer - Starter Script 2: Mount Namespace Isolation & VFS Jailing
Authors: Antara Chatterjee (20251503007), Asmit Pratap Singh (20251503011)
Course: CS303 Operating Systems
"""

import os
import sys
import ctypes

libc = ctypes.CDLL("libc.so.6", use_errno=True)

libc.unshare.argtypes = [ctypes.c_int]
libc.unshare.restype = ctypes.c_int

libc.mount.argtypes = [
    ctypes.c_char_p, ctypes.c_char_p,
    ctypes.c_char_p, ctypes.c_ulong,
    ctypes.c_char_p
]
libc.mount.restype = ctypes.c_int

libc.umount2.argtypes = [ctypes.c_char_p, ctypes.c_int]
libc.umount2.restype = ctypes.c_int

# Constants (sys/mount.h and linux/sched.h)
CLONE_NEWNS  = 0x00020000  # Mount namespace
MS_REC       = 1 << 14     # Recursive flag
MS_PRIVATE   = 1 << 18     # Convert mount tree to private propagation
MNT_DETACH   = 0x00000002  # Lazy unmount

def setup_minimal_test_sandbox(jail_dir: str):
    """Generates a sandboxed directory structure."""
    os.makedirs(os.path.join(jail_dir, "proc"), exist_ok=True)
    os.makedirs(os.path.join(jail_dir, "bin"), exist_ok=True)
    os.makedirs(os.path.join(jail_dir, "test_dir"), exist_ok=True)
    
    marker = os.path.join(jail_dir, "test_dir", "guest_marker.txt")
    with open(marker, "w") as f:
        f.write("You are locked inside the sandboxed root filesystem!\n")

def main():
    if os.geteuid() != 0:
        sys.exit("[-] Permission Error: Must run as root (use 'sudo').")

    jail_path = os.path.abspath("./minimal_jail")
    setup_minimal_test_sandbox(jail_path)

    print(f"[*] [Host] Prepared sandbox target at: {jail_path}")
    print("[*] [Host] Unsharing mount namespace (CLONE_NEWNS)...")

    # Step 1: Detach from host mount namespace
    if libc.unshare(CLONE_NEWNS) != 0:
        errno = ctypes.get_errno()
        sys.exit(f"[-] unshare(CLONE_NEWNS) failed with error code: {errno}")

    # Step 2: Prevent mount propagation back to the host system
    # We must mark '/' as MS_REC | MS_PRIVATE so child mounts remain invisible to host
    if libc.mount(b"none", b"/", b"", MS_REC | MS_PRIVATE, b"") != 0:
        errno = ctypes.get_errno()
        sys.exit(f"[-] Failed to mark mounts as private: {errno}")

    print("[+] [Host] Mount propagation set to MS_PRIVATE (Host filesystem protected).")

    # Step 3: Fork child to test the filesystem jail
    pid = os.fork()

    if pid == 0:
        print(f"\n[+] [Child] Pivoting root filesystem into: {jail_path}")

        # Shift perceived root directory to our jail folder
        os.chroot(jail_path)
        os.chdir("/")

        print(f"[+] [Child] Successfully chrooted.")
        print(f"[+] [Child] Entries visible at root directory ('/'): {os.listdir('/')}")

        # Mount virtual /proc
        if libc.mount(b"proc", b"/proc", b"proc", 0, b"") == 0:
            print("[+] [Child] Mounted isolated /proc filesystem.")
            proc_entries = os.listdir("/proc")[:5]
            print(f"[+] [Child] /proc samples: {proc_entries}")
            
            libc.umount2(b"/proc", MNT_DETACH)
            print("[+] [Child] Cleaned up /proc mount.")
        else:
            print("[-] [Child] Could not mount /proc.")

        print("[+] [Child] Filesystem jail verified. Exiting.")
        sys.exit(0)
    else:
        os.waitpid(pid, 0)
        print(f"\n[*] [Host] Child exited cleanly.")
        print(f"[*] [Host] Verifying host root ('/'): {os.listdir('/')[:5]}... (Host untouched)")

if __name__ == "__main__":
    main()
