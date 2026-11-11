#!/usr/bin/env python3
"""
PyContainer: A Pure Python Linux Container Virtualization Engine
Course: CS303 Operating Systems
Authors: Antara Chatterjee (20251503007), Asmit Pratap Singh (20251503011)
"""

import os
import sys
import argparse
import ctypes
import traceback

# -----------------------------------------------------------------------------
# 1. CTYPES & LIBC LOW-LEVEL KERNEL BINDINGS
# -----------------------------------------------------------------------------
try:
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
except Exception as e:
    sys.exit(f"[-] Critical Error: Failed to load libc.so.6: {e}")

# int unshare(int flags);
libc.unshare.argtypes = [ctypes.c_int]
libc.unshare.restype = ctypes.c_int

# int mount(const char *source, const char *target,
#           const char *filesystemtype, unsigned long mountflags,
#           const void *data);
libc.mount.argtypes = [
    ctypes.c_char_p, ctypes.c_char_p,
    ctypes.c_char_p, ctypes.c_ulong,
    ctypes.c_char_p
]
libc.mount.restype = ctypes.c_int

# int umount2(const char *target, int flags);
libc.umount2.argtypes = [ctypes.c_char_p, ctypes.c_int]
libc.umount2.restype = ctypes.c_int

# int sethostname(const char *name, size_t len);
libc.sethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
libc.sethostname.restype = ctypes.c_int

# -----------------------------------------------------------------------------
# 2. LINUX KERNEL CONSTANTS (from linux/sched.h and sys/mount.h)
# -----------------------------------------------------------------------------
CLONE_NEWNS   = 0x00020000  # Mount namespace
CLONE_NEWUTS  = 0x04000000  # Hostname / Domain namespace
CLONE_NEWPID  = 0x20000000  # Process ID namespace
CLONE_NEWNET  = 0x40000000  # Network namespace

MS_NOSUID     = 1 << 1      # Disallow set-user-ID and set-group-ID
MS_NODEV      = 1 << 2      # Disallow access to devices
MS_NOEXEC     = 1 << 3      # Disallow execution of binaries
MS_REC        = 1 << 14     # Recursive submount flag
MS_PRIVATE    = 1 << 18     # Convert mount tree to private propagation

MNT_DETACH    = 0x00000002  # Lazy unmount flag

CGROUP_ROOT   = "/sys/fs/cgroup"
CGROUP_NAME   = "pycontainer_runtime"

# -----------------------------------------------------------------------------
# 3. CGROUPS V2 RESOURCE GOVERNANCE
# -----------------------------------------------------------------------------
def configure_cgroups(child_pid: int, memory_mb: int = None, cpu_percent: int = None) -> str:
    """
    Sets up Cgroups v2 controllers for strict memory capping and CPU quota throttling.
    """
    if not os.path.exists(CGROUP_ROOT):
        print("[-] Cgroups v2 filesystem not detected. Skipping hardware limiting.")
        return ""

    cgroup_dir = os.path.join(CGROUP_ROOT, CGROUP_NAME)
    os.makedirs(cgroup_dir, exist_ok=True)

    # Enable controllers in parent subtree if allowed
    subtree_ctl = os.path.join(CGROUP_ROOT, "cgroup.subtree_control")
    if os.path.exists(subtree_ctl):
        try:
            with open(subtree_ctl, "w") as f:
                f.write("+memory +cpu")
        except PermissionError:
            pass

    # 1. Enforce Memory Limit (in Bytes)
    if memory_mb is not None:
        mem_file = os.path.join(cgroup_dir, "memory.max")
        mem_bytes = memory_mb * 1024 * 1024
        with open(mem_file, "w") as f:
            f.write(str(mem_bytes))
        print(f"[+] [Host] Cgroups v2: Hard memory cap enforced at {memory_mb} MB")

    # 2. Enforce CPU Bandwidth Quota (CFS Scheduler)
    if cpu_percent is not None:
        cpu_file = os.path.join(cgroup_dir, "cpu.max")
        period_us = 100000  # 100ms standard period
        quota_us = int((cpu_percent / 100.0) * period_us)
        with open(cpu_file, "w") as f:
            f.write(f"{quota_us} {period_us}")
        print(f"[+] [Host] Cgroups v2: CPU quota capped at {cpu_percent}%")

    # 3. Register child PID in cgroup.procs
    procs_file = os.path.join(cgroup_dir, "cgroup.procs")
    with open(procs_file, "w") as f:
        f.write(str(child_pid))
    print(f"[+] [Host] Attached Child PID {child_pid} to Cgroup '{CGROUP_NAME}'")

    return cgroup_dir


def cleanup_cgroups(cgroup_dir: str):
    """Cleans up the cgroup directory node upon container teardown."""
    if cgroup_dir and os.path.exists(cgroup_dir):
        try:
            os.rmdir(cgroup_dir)
        except OSError:
            pass

# -----------------------------------------------------------------------------
# 4. CONTAINER CHILD EXECUTION (Sandboxed Runtime)
# -----------------------------------------------------------------------------
def run_child_container(rootfs: str, hostname: str, command: list):
    """
    Executes within the child process to unshare namespaces and establish VFS jail.
    """
    try:
        # Step 1: Unshare Namespaces
        flags = CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWPID | CLONE_NEWNET
        if libc.unshare(flags) != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"unshare failed (code {errno}). Run with 'sudo'.")

        # Step 2: Prevent Mount Leaks to Host (Firewall)
        if libc.mount(b"none", b"/", b"", MS_REC | MS_PRIVATE, b"") != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"Failed to mark mount tree private (code {errno})")

        # Step 3: Enter Filesystem Jail (chroot)
        os.chroot(rootfs)
        os.chdir("/")

        # Step 4: Mount Virtual /proc (Local process table introspection)
        os.makedirs("/proc", exist_ok=True)
        if libc.mount(b"proc", b"/proc", b"proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, b"") != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"Mount /proc failed (code {errno})")

        # Step 5: Mount Synthetic /dev nodes (Minimal tmpfs)
        os.makedirs("/dev", exist_ok=True)
        libc.mount(b"tmpfs", b"/dev", b"tmpfs", MS_NOSUID, b"mode=0755")

        # Step 6: Set Virtual UTS Hostname
        encoded_host = hostname.encode("utf-8")
        if libc.sethostname(encoded_host, len(encoded_host)) != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"sethostname failed (code {errno})")

        # Step 7: Clear host environment variables
        env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "TERM": os.environ.get("TERM", "xterm-256color"),
            "HOME": "/root",
            "USER": "root"
        }

        # Step 8: Replace process image via execvpe
        print(f"[+] [Child PID 1] Spawning payload: {' '.join(command)}")
        sys.stdout.flush()
        os.execvpe(command[0], command, env)

    except Exception as e:
        print(f"[!] [Child Exception]: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

# -----------------------------------------------------------------------------
# 5. CLI INTERFACE & ORCHESTRATION
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="PyContainer: Pure Python Linux Container Runtime (CS303 OS)"
    )
    parser.add_argument("--rootfs", required=True, help="Path to guest root filesystem")
    parser.add_argument("--memory", type=int, default=None, help="Memory ceiling in MB (Cgroups v2)")
    parser.add_argument("--cpu", type=int, default=None, help="CPU quota percentage (e.g., 50 for 50%)")
    parser.add_argument("--hostname", default="pycontainer-guest", help="Isolated hostname")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command payload to execute inside container")

    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("[-] Critical Error: PyContainer requires root privileges. Run with 'sudo'.")

    rootfs_path = os.path.abspath(args.rootfs)
    if not os.path.isdir(rootfs_path):
        sys.exit(f"[-] Error: RootFS directory '{rootfs_path}' does not exist.")

    payload = args.command if args.command else ["/bin/sh"]

    print("=" * 65)
    print("  PyContainer - Operating System-Level Virtualization Engine")
    print(f"  Target RootFS : {rootfs_path}")
    print(f"  Memory Limit  : {args.memory} MB" if args.memory else "  Memory Limit  : Unbounded")
    print(f"  CPU Quota     : {args.cpu} %" if args.cpu else "  CPU Quota     : Unbounded")
    print(f"  Hostname      : {args.hostname}")
    print(f"  Init Payload  : {' '.join(payload)}")
    print("=" * 65)

    # Fork execution boundary
    child_pid = os.fork()

    if child_pid == 0:
        run_child_container(rootfs_path, args.hostname, payload)
    else:
        cgroup_path = configure_cgroups(child_pid, args.memory, args.cpu)
        print(f"[+] [Host] Supervising container child PID {child_pid}...")

        try:
            _, status = os.waitpid(child_pid, 0)
            exit_code = os.waitstatus_to_exitcode(status)
            print(f"[+] [Host] Container terminated with return code: {exit_code}")
        except KeyboardInterrupt:
            print("[!] Host caught interrupt. Terminating container...")
            os.kill(child_pid, 9)
        finally:
            cleanup_cgroups(cgroup_path)
            print("[+] [Host] Cgroup teardown and cleanup complete.")

if __name__ == "__main__":
    main()
