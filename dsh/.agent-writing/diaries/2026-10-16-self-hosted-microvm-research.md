# 2026-10-16 - self-hosted microVM research and plan

## Why

Alternative to Docker Sandboxes: run a KVM microVM directly on the host, share the host project
directory in (virtio-fs), and run the dsh harness inside the microVM with no container. User asked
for feasibility, issues and gotchas, and assumed Debian is close enough to Ubuntu.

## What I found

- **Firecracker is not suitable for live directory sharing.** Its design lists only VirtIO net,
  block and vsock plus serial/i8042; there is no virtio-fs and no 9p, and no PCI. Sharing means a
  pre-formatted **virtio-block** image (not live) or a network filesystem (NFS/SSHFS).
- **Cloud Hypervisor** is the clean microVM match: virtio-fs via `--fs` and `--memory shared=on`.
  DAX is not available. It is **not in Debian repos** (release binary/source build).
- **QEMU microvm** can do virtio-fs but has no PCI, so you must use `vhost-user-fs-device` (MMIO),
  not `vhost-user-fs-pci`. Niche but real.
- **Lima** packages QEMU, cloud-init, mounts, port forwarding and snapshots. On Linux it defaults to
  **9p**; `mountType: virtiofs` is experimental but works with the **Rust virtiofsd**. Lima's own
  docs recommend running AI agents inside the VM and mounting only the project directory.
- **Debian fit is good:** trixie ships `virtiofsd` 1.13.2 (source `rust-virtiofsd`) and QEMU.
  Only KVM is a hard prerequisite; `vmx` is present on this host.
- **libkrun/krunvm** is a third option with virtio-fs built in; krunvm is OCI-image-centric.
- **Gotchas:** virtio-fs has **no inotify/fsnotify** (Lima has an experimental `mountInotify` shim);
  cache-mode coherency (`cache=never` vs `cache=always`); guest-root writes become root-owned on
  the host; virtiofsd is a host process with access to the exported tree and must be sandboxed and
  limited to the export root; networking defaults (slirp/TAP+bridge) can expose host/LAN silently.

## Decisions

- Recommend **Phase 1 Lima prototype** (fast) then **Phase 2 Cloud Hypervisor microVM** (minimal)
  if footprint matters. Firecracker excluded.
- Share only the project directory; use virtio-fs with `cache=never`; run the agent as uid 1000.
- The web UI is easy here: Lima forwards the guest's **loopback** port, so `dsh web` keeps its safe
  `127.0.0.1` default (no socat forwarder needed, unlike Docker Sandboxes).
- Docs go in `.agent-writing/docs/MAIN.md`; never edit `README.md`.
- Cross-linked with the Docker Sandboxes plan.

## Corroboration (Firecracker subagent)

- Re-verified: Firecracker's device matrix has no virtio-fs/9p/FUSE; live sharing only via NFS/SSHFS
  over TAP or an offline block image. The optional PCI transport (v1.13+) is transport-only.
- Added option: **crosvm** has native in-process virtio-fs and 9p. QEMU `microvm` works with
  `vhost-user-fs-device` but caps at ~8 virtio-mmio devices and targets short-lived guests.
- Cloud Hypervisor: v54 (Oct 2026), host kernel >= 6.8, production via Kata (kata-clh).
- libkrun README warns virtio-fs is not confined to the shared directory.

## Open questions

- Is Lima virtiofs stable enough on Linux, or is 9p the pragmatic default?
- How badly does the missing inotify break the agent's dev loop?
- Cloud Hypervisor vs QEMU microvm for least friction.
- Egress model: host-side credential-injecting proxy vs NAT + allowlist.
- Default to Lima `--sync` (review before changes reach host) or a live mount?

## Artifacts

- Plan: `.agent-writing/plans/2026-10-16-self-hosted-microvm-for-dsh.md`
- Related plan: `.agent-writing/plans/2026-10-16-docker-sandboxes-for-dsh.md`

## Sources

- https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md
- https://github.com/cloud-hypervisor/cloud-hypervisor/blob/main/docs/fs.md
- https://virtio-fs.gitlab.io/
- https://lists.gnu.org/archive/html/qemu-discuss/2021-05/msg00085.html
- https://packages.debian.org/trixie/virtiofsd
- https://lima-vm.io/docs/config/mount/
- https://lima-vm.io/docs/config/port/
- https://lima-vm.io/docs/examples/ai/
- https://lima-vm.io/docs/security/
- https://github.com/containers/libkrun
- https://github.com/containers/krunvm
