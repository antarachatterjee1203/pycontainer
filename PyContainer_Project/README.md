# PyContainer: Pure Python Linux Container Runtime

**Course:** CS303 Operating Systems  
**Authors:** Antara Chatterjee (20251503007), Asmit Pratap Singh (20251503011)

---

## Folder Structure
- `pycontainer.py`: Complete production container runtime engine.
- `poc_pid_uts_isolation.py`: Starter Script 1 demonstrating PID and UTS isolation.
- `poc_mount_jail.py`: Starter Script 2 demonstrating Mount namespace and chroot jail.
- `check_system.py`: Host diagnostic tool to verify Cgroups v2 and libc.so.6.
- `setup_rootfs.sh`: Automatic downloader and unpacker for Alpine Linux minirootfs.
- `test_limits.py`: Test harness to verify PID 1 virtualization and OOM limits inside container.

---

## Quick Start Instructions

### 1. Check System Compatibility
```bash
python3 check_system.py
```

### 2. Run Phase 1 Early POC Scripts
```bash
sudo python3 poc_pid_uts_isolation.py
sudo python3 poc_mount_jail.py
```

### 3. Provision RootFS & Run Full PyContainer
```bash
chmod +x setup_rootfs.sh
./setup_rootfs.sh

# Run interactive shell inside container
sudo python3 pycontainer.py --rootfs ./alpine_rootfs --hostname isolated-guest /bin/sh

# Run with 40MB memory limit (Tests Cgroups v2 OOM Killer)
sudo python3 pycontainer.py --rootfs ./alpine_rootfs --memory 40 /bin/sh -c "python3 -c 'x = bytearray(80*1024*1024)'"
```
