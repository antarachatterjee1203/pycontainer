#!/usr/bin/env python3
"""
PyContainer - Starter Script 1: Combined PID & UTS Namespace Isolation
Authors: Antara Chatterjee (20251503007), Asmit Pratap Singh (20251503011)
Course: CS303 Operating Systems
"""

import os
import sys
import ctypes

# 1. Load libc foreign function interface
libc = ctypes.CDLL("libc.so.6", use_errno=True)

libc.unshare.argtypes = [ctypes.c_int]
libc.unshare.restype = ctypes.c_int

libc.sethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
libc.sethostname.restype = ctypes.c_int

# 2. Kernel namespace flags (from <linux/sched.h>)
CLONE_NEWPID = 0x20000000  # Virtualizes process ID hierarchy
CLONE_NEWUTS = 0x04000000  # Virtualizes host and domain name

def main():
    if os.geteuid() != 0:
        sys.exit("[-] Permission Error: Must run as root (use 'sudo').")

    original_hostname = os.uname().nodename
    print(f"[*] [Host] Initial Hostname: '{original_hostname}'")
    print(f"[*] [Host] Root Process PID: {os.getpid()}")

    # Step 1: Detach PID & UTS namespaces
    flags = CLONE_NEWPID | CLONE_NEWUTS
    if libc.unshare(flags) != 0:
        errno = ctypes.get_errno()
        sys.exit(f"[-] unshare() failed with error code: {errno}")

    print("[+] [Host] unshare(CLONE_NEWPID | CLONE_NEWUTS) successful.")
    print("[*] [Host] Forking to instantiate the isolated child process...")

    # The child forked immediately after CLONE_NEWPID becomes PID 1
    child_pid = os.fork()

    if child_pid == 0:
        # --- INSIDE ISOLATED CHILD ---
        virtual_pid = os.getpid()
        print(f"\n[+] [Child] Entering isolated namespace context.")
        print(f"[+] [Child] Perceived os.getpid() value: {virtual_pid}")

        if virtual_pid == 1:
            print(" -> SUCCESS: Process has assumed PID 1 (Container Init role).")
        else:
            print(f" -> UNEXPECTED: Perceived PID is {virtual_pid}")

        # Alter isolated guest hostname
        guest_hostname = "guest-isolated-node"
        encoded = guest_hostname.encode("utf-8")
        libc.sethostname(encoded, len(encoded))
        print(f"[+] [Child] Updated guest hostname: '{os.uname().nodename}'")
        print("[+] [Child] Test complete. Terminating child context.")
        sys.exit(0)
    else:
        # --- INSIDE HOST PARENT ---
        print(f"[*] [Host] Forked child tracked on host with PID: {child_pid}")
        _, status = os.waitpid(child_pid, 0)
        
        current_hostname = os.uname().nodename
        print(f"\n[*] [Host] Child finished with exit status: {status}")
        print(f"[*] [Host] Hostname after child termination: '{current_hostname}'")
        assert current_hostname == original_hostname, "Hostname leaked to host!"
        print("[+] [Host] UTS and PID namespace isolation verified successfully.")

if __name__ == "__main__":
    main()
