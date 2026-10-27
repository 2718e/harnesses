# Plan: self-hosted KVM microVM for the dsh harness

- **Date:** 2026-10-16
- **Status:** Proposed — research complete, implementation not started
- **Project:** `harnesses/dsh` (the container this session runs in)
- **Goal:** run dsh directly inside a lightweight KVM microVM on the Debian host, with the project
  directory shared in from the host (virtio-fs), so the agent gets an isolated kernel and can use
  Docker **inside the VM** — no container wrapper, no host Docker socket.
- **Related:** the Docker Sandboxes plan (`2026-10-16-docker-sandboxes-for-dsh.md`) is the
  turnkey alternative to this one.

## TL;DR

- The idea is sound and is a recognised pattern. A full VM gives the strongest isolation and
  **naturally provides Docker**: install Docker in the guest and it uses the guest kernel, with no
  socket-passthrough problem.
- **Firecracker is the wrong pick here.** Its device model is deliberately tiny: VirtIO **net,
  block, vsock**, serial, i8042 — it has **no virtio-fs and no 9p**. Live host-directory sharing is
  not possible; you would fall back to a pre-formatted block image (not live) or a network FS.
- The "microVM + shared directory" combination points to **Cloud Hypervisor** (first-class virtio-fs,
  `--fs` plus `--memory shared=on`; production-ready) or **crosvm** (native in-process
  virtio-fs/9p). **QEMU `microvm`** works via the MMIO `vhost-user-fs-device` but targets
  short-lived guests; **libkrun** is another small option (with a confinement caveat).
- **Recommended path:** prototype with **Lima** first (it packages QEMU + cloud-init + mounts +
  port-forwarding + snapshots), because it is days not weeks. Then, if minimal footprint matters,
  build the purpose-built **Cloud Hypervisor + virtiofsd** microVM. Both share the same guest
  provisioning and the same workspace mount.
- Where Debian matters: it is fine. Debian 13 (trixie) ships the **Rust `virtiofsd` 1.13.2**
  (`rust-virtiofsd`) and QEMU; Cloud Hypervisor is **not** packaged and needs a release binary or
  source build. KVM is the only hard host prerequisite.
- Biggest gotchas: **(1) virtio-fs has no inotify/fsnotify** (file watchers miss host edits);
  **(2)** uid/gid and cache-mode semantics; **(3)** the virtiofsd host process is itself part of the
  attack surface; **(4)** networking defaults can silently expose the host.

## 1. Component capabilities (2026)

| Runtime | Type | virtio-fs | 9p | Other fs options | Notes |
| --- | --- | --- | --- | --- | --- |
| **Firecracker** | microVM | no | no | virtio-block (pre-formatted image), network FS | Tiny device model; needs jailer/TAP; snapshots |
| **Cloud Hypervisor** | microVM | **yes** (`--fs` + `--memory shared=on`) | no | virtio-block | DAX not available; not in Debian repos; host kernel >= 6.8; v54 (Oct 2026); production via Kata |
| **QEMU `microvm`** | microVM machine | yes, via `vhost-user-fs-device` (MMIO) | yes (virtio-9p mmio) | virtio-block | No PCI/ACPI; max ~8 virtio-mmio devices; built for short-lived guests (no migration/hotplug) |
| **crosvm** | microVM VMM | **yes (native, in-process)** | **yes (native)** | virtio-block | Mature (ChromeOS); `--shared-dir PATH:TAG:type=fs`; optional DAX, uid/gid maps |
| **QEMU (standard)** | full VM | yes (`vhost-user-fs-pci`) | yes | virtio-block | Heavier, ubiquitous, best documented |
| **libkrun / krunvm** | microVM lib/CLI | **yes** | no | virtio-block | Small footprint; krunvm is OCI-image based |
| **Lima** | VM manager (QEMU/VZ) | yes on Linux (Rust virtiofsd, experimental) | **yes (default on Linux)** | reverse-sshfs, block, sync | Batteries included; explicitly supports AI agents |

## 2. Why not Firecracker for this

Firecracker's device/API matrix is exhaustively VirtIO block (and vhost-user-block), net, vsock,
rng, pmem and mem, plus a serial console, a minimal keyboard controller, and ballooning. There is no
virtio-fs, no 9p and no FUSE. The optional PCI transport (v1.13+) only re-homes those same devices
and adds no passthrough. The practical consequences:

- You cannot expose a live host directory. Options are:
  - **virtio-block** against a host file pre-formatted with a filesystem — a fixed image, not a
    live view of the host tree. You must rebuild/remount it to share changes.
  - **Network filesystem** (NFS/SSHFS) over the TAP interface — live, but network semantics,
    caching, locking and uid mapping problems, and it widens the network surface.
- If Firecracker is a hard requirement, the least-bad design is a **virtio-block data disk plus
  NFS export of the project**, but that combination is strictly worse than Cloud Hypervisor +
  virtio-fs for this use case.

So: keep the *spirit* of the idea (small KVM microVM) and pick a VMM that supports virtio-fs.

## 3. Filesystem sharing: options and gotchas

### virtio-fs (preferred)

- Implemented by a host `virtiofsd` daemon over vhost-user, carried on a VirtIO device; uses FUSE
  and is designed for local filesystem semantics (unlike 9p, which repurposes a network protocol).
- **Debian 13 has the actively developed Rust daemon**: `virtiofsd` 1.13.2 (source package
  `rust-virtiofsd`), which depends on `uidmap`/`libcap-ng`/`libseccomp` and is built to run
  with dropped privileges, not root.
- **Guest kernel must have `CONFIG_VIRTIO_FS`** (Ubuntu/Debian cloud images do).
- **Cloud Hypervisor requires `--memory shared=on`**; **DAX is not available** there.
- **No inotify/fsnotify.** This is the single biggest practical gotcha: build tools, Vite,
  nodemon, and test watchers will not see files changed on the host side. Lima has an experimental
  `mountInotify` shim (Lima >= 0.21) that relays host events into the guest; a minimal microVM
  would need the same shim or a polling watcher.
- **cache modes:** `cache=never` avoids host page-cache growth and is coherent; `cache=always`
  is faster but can serve stale data when the host also edits files. For a shared dev tree, start
  with `cache=never`.
- **uid/gid:** files written in the guest appear on the host with the guest process's uid/gid. Run
  the agent as the host uid (1000) so the shared tree stays owned by the host user; if the guest
  agent runs as root, host files become root-owned.
- **Security:** virtiofsd is a host process with access to the exported tree. Export only the
  project directory, run it sandboxed (user namespace / `--sandbox`, seccomp, dropped caps), and
  do not follow symlinks out of the export root.

### The alternatives

| Method | Live | Performance | Semantics | Inotify | Notes |
| --- | --- | --- | --- | --- | --- |
| virtio-fs | yes | best | near-local | **no** | needs VMM support + virtiofsd |
| virtio-9p | yes | poorer | weak (xattr/symlink modes) | no | Lima default on Linux; simple |
| reverse-sshfs | yes | fair | SSH/SFTP quirks | no | Lima default historically; breaks if SSH drops |
| virtio-block | no | native | full | n/a | fixed image, not a live share |
| NFS over virtio-net | yes | fair | network | no | stays live even on Firecracker |

## 4. Architecture options

**Option A — Lima (QEMU) guest, project mounted (recommended prototype).**
Lima provisions an Ubuntu/Debian cloud image, mounts only the project directory, forwards guest
ports to host `localhost`, and supports snapshots and SSH. On Linux it defaults to 9p, but
`mountType: virtiofs` works with Debian's Rust virtiofsd. Lima's own docs recommend running AI
agents inside the VM and mounting **only** the project directory. Fastest route to a working
system; keep it if footprint is acceptable.

**Option B — purpose-built Cloud Hypervisor microVM (recommended target if you want minimal).**
Boot a distro cloud image (or kernel + rootfs) with `--memory shared=on`, one virtio-fs share
backed by virtiofsd, TAP networking with nftables NAT (or passt for user-mode, rootless
networking), and vsock for control/SSH. You own the launcher, image build and networking. Smallest
attack surface and fastest boot, most work.

**Option C — QEMU `microvm` + `vhost-user-fs-device` (MMIO).** QEMU is already in Debian, but
`microvm` is built for short-lived guests: no migration, no hotplug, and only ~8 virtio-mmio
devices total (shared with disk and net). Prefer standard QEMU with `vhost-user-fs-pci` for a
long-lived dev VM; keep `microvm` only if boot time dominates.

**Option D — crosvm.** A mature microVM VMM (ChromeOS) with **native in-process virtio-fs and 9p**
— no external virtiofsd to wire up — configured with
`--shared-dir PATH:TAG:type=fs[,cache=never|auto|always][,dax=BOOL]`. Good middle ground between
Lima and Cloud Hypervisor.

**Option E — libkrun / krunvm.** virtio-fs and TSI networking built in, very small. krunvm builds
from OCI images, which is closer to "container-ish" than the goal; libkrun-as-a-library is more
work to wire up than Lima. Note libkrun's own warning: it does **not** confine virtio-fs to the
shared directory, so pair it with a mount/user namespace.

**Option F — Firecracker.** Only with a block image or network FS. Not recommended (section 2).

## 5. Recommended implementation

### Phase 0 — host gate

```sh
grep -Eo 'vmx|svm' /proc/cpuinfo | head -1   # CPU virt (vmx present on this host)
lsmod | grep -E 'kvm_(intel|amd)|kvm_arm64'
ls -l /dev/kvm
groups | tr ' ' '\n' | grep -x kvm
# if the host is itself a VM, nested virtualization must be enabled
```

If `/dev/kvm` is absent, stop: none of the local options work (Docker Sandboxes has the same
requirement; only a container-only approach does).

### Phase 1 — Lima prototype (validate the whole workflow fast)

Suggested file: `dsh/vm/lima-dsh.yaml`

```yaml
vmType: qemu
arch: x86_64
cpus: 4
memory: 8GiB
disk: 60GiB
mountType: virtiofs          # needs Debian's rust virtiofsd; fall back to 9p if it misbehaves
mountInotify: true           # experimental host->guest event shim (Lima >= 0.21)
mounts:
  - location: "~/dev/<project>"   # mount ONLY what the agent needs
    writable: true
portForwards:
  - guestPort: 3080
    hostPort: 3080
provision:
  - mode: system
    script: |
      #!/bin/bash
      set -eux
      apt-get update
      apt-get install -y curl ca-certificates git build-essential python3 python3-venv docker.io
      curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
      apt-get install -y nodejs
      npm install -g pnpm@12.4.2
      curl -LsSf https://astral.sh/uv/install.sh | sh
  - mode: user
    script: |
      #!/bin/bash
      set -eux
      pnpm add -g @deepseek-ai/dsh@0.2.0-rc.2
```

Then:

```sh
limactl start --name dsh ./vm/lima-dsh.yaml
limactl shell dsh
# inside the guest
dsh web --no-open --trusted-host localhost --trusted-host 127.0.0.1   # binds guest 127.0.0.1:3080
# host: http://localhost:3080  (Lima forwards the guest localhost port)
```

Why this works where the sandbox product needed a forwarder: Lima forwards the **guest's loopback**
port to the host, so `dsh web` can keep its safe `127.0.0.1` default. For headless access,
`ssh -L 3080:127.0.0.1:3080 lima-dsh` is equivalent.

Pass criteria: project files visible in the guest and host edits appear without a remount; file
watchers behave (or the `mountInotify`/polling gap is understood); dsh UI reachable; guest
`docker run hello-world` works; `limactl stop/start` preserves installed packages; `limactl
snapshot` works.

### Phase 2 — minimal Cloud Hypervisor microVM (optional target)

Components in `dsh/vm/cloud-hypervisor/`:

- `build-image.sh`: download an Ubuntu/Debian cloud image + kernel, inject cloud-init that runs
  the same provisioning script as Phase 1, resize the disk.
- `run-vm.sh`: start `virtiofsd` and then `cloud-hypervisor`, e.g.

```sh
virtiofsd --socket-path=/run/virtiofsd-dsh.sock \
  --shared-dir=/home/<user>/dev/<project> --cache=never --sandbox=namespace &
cloud-hypervisor \
  --cpus boot=4 --memory size=8G,shared=on \
  --kernel vmlinux --cmdline "console=hvc0 root=/dev/vda1 rw" \
  --disk path=ubuntu-24.04.img,image_type=raw \
  --fs tag=workspace,socket=/run/virtiofsd-dsh.sock,num_queues=1,queue_size=512 \
  --net tap=dsh-tap0,mac=02:00:00:00:01:02,ip=192.168.100.2,mask=255.255.255.0 \
  --vsock cid=3,socket=/run/ch-vsock.sock
```

- Guest `/etc/fstab`: `workspace /home/<user>/project virtiofs defaults 0 0`.
- Host `nftables`: masquerade the TAP subnet, then **drop guest->host and guest->LAN** by default;
  allow only the model/provider endpoints you use.
- UI access: either bind dsh to the guest's `192.168.100.2` with
  `--host 192.168.100.2 --trusted-host <name>`, or keep `127.0.0.1` and tunnel
  `ssh -L 3080:127.0.0.1:3080` over the guest's sshd.
- Cloud Hypervisor is not in Debian: pin a release tarball (and checksum) or build from source.

### Phase 3 — dsh provisioning, service, tooling

- Turn the existing `Dockerfile` package list into `vm/provision/dsh.sh` (shared by Lima and the
  microVM): Node 24, python 3.13/venv, `uv`, `pnpm`, `git`, `build-essential`, `dsh` pinned.
- Run dsh under a guest `systemd` unit so the web server and (optionally) guest Docker survive
  reboots; write startup output to a log so the URL/token can be read.
- Keep `DSH_HOME` on the guest disk (persistent across stop/start; lost only if the VM image is
  rebuilt). Keep the workspace on the host via virtio-fs.
- Add `just` recipes: `vm-start`, `vm-shell`, `vm-url`, `vm-stop`, `vm-snapshot`,
  `vm-delete`. Document in `.agent-writing/docs/MAIN.md` (do not edit `README.md`).
- Docker in the guest: install `docker.io`/`docker-ce` and run it as the guest daemon. Because
  the guest has its own kernel, this is normal Docker — not Docker-in-Docker — and containers never
  touch the host.

## 6. Security model and hardening

- **Boundary:** the KVM/hypervisor boundary plus a separate kernel. Stronger than the current
  container, comparable in kind to Docker Sandboxes.
- **The agent owns the guest.** It can become root inside, so guest-side controls are for safety,
  not a security boundary. Enforce on the host: the exported directory, the TAP/NAT rules, and the
  host-side firewall.
- **Mount only the project.** Lima explicitly recommends `--mount-only .:w` for AI agents. Use
  read-only mounts for datasets. Consider Lima's `--sync` mode (>= 2.1, rsync + review prompt) for
  high-risk tasks: the agent works on a guest copy and you approve changes before they reach the host.
- **Export root must be tight.** Do not export a parent directory (e.g. `$HOME`). virtiofsd
  sandboxing plus not following symlinks matters because a compromised guest can ask the daemon to
  open paths within the export.
- **Networking defaults are the classic footgun.** User-mode/slirp setups can make host services
  reachable from the guest; TAP+bridge puts the guest on your LAN. Decide egress explicitly and
  verify from inside the guest (see Phase 2 nftables).
- **Credentials:** the guest holds the provider keys, so treat the VM image/snapshots as sensitive.
  Prefer a host-side egress proxy that injects credentials (and logs requests) over pasting keys
  into the guest filesystem.
- **Supply chain:** the guest image and every `apt`/`npm`/`pip` package are now part of your
  trusted base. Pin where practical and snapshot before upgrades.
- **Snapshots contain secrets.** Store and encrypt accordingly.

## 7. Gotchas checklist (things that will bite)

1. Firecracker cannot share a live directory (no virtio-fs/9p).
2. virtio-fs has no inotify; watchers/rebuilds may not trigger on host edits.
3. DAX is experimental and unavailable in Cloud Hypervisor; `--memory shared=on` is required.
4. Guest kernel needs `CONFIG_VIRTIO_FS`; `mount -t virtiofs <tag>`.
5. QEMU `microvm` has no PCI: use `vhost-user-fs-device` (MMIO), not `vhost-user-fs-pci`; it also
   caps at ~8 virtio-mmio devices and targets short-lived guests (no migration/hotplug).
6. Lima's Linux virtiofs mode is experimental and needs the **Rust** virtiofsd; the QEMU-packaged
   `qemu-virtiofsd` will not work (it wants root).
7. `cache=always` can serve stale files; `cache=never` is coherent but slower.
8. uid/gid: guest-root writes become root-owned on the host.
9. virtiofsd is a host process with access to the export; sandbox it and limit the export.
10. Cloud Hypervisor is not packaged in Debian (release binary/build); Firecracker likewise.
11. Port forwarding targets guest **localhost**; binding `0.0.0.0` is unnecessary (and dsh refuses it).
12. Nested virtualization is required if the host is itself a VM.
13. Backups/snapshots of the VM include credentials and `DSH_HOME`.
14. The dsh native addon needs an executable mmap target; keep `NARB_NATIVE_CACHE_DIR` on a normal
    writable path in the guest.

## 8. Verification

- Host: `/dev/kvm` usable; Lima starts and mounts the project.
- Guest: `docker run hello-world`; ``dsh web` reachable from the host; provider calls work.
- Round-trip: create a file on the host, confirm it is visible in the guest without remount; edit
  in the guest, confirm ownership is the host user.
- Watcher test: run a watcher in the guest, edit on the host, note whether it fires (expected: not,
  unless `mountInotify` or polling).
- Isolation test: from the guest, try to reach a host-only service and the LAN; confirm the
  firewall blocks them.
- Persistence: `limactl stop/start` and a snapshot/restore keep installed packages and sessions.

## 9. Comparison with the alternatives

| | Current compose container | Docker Sandboxes (`sbx`) | Self-hosted microVM (this plan) |
| --- | --- | --- | --- |
| Isolation | namespaces | microVM | microVM |
| Docker for agent | no (unless added) | yes (private engine) | yes (guest Docker) |
| Host OS support | any Docker host | Ubuntu 24.04+/KVM, or cloud | any KVM Linux (Debian fine) |
| Account/subscription | none | Docker account (+ cloud paid) | none |
| Filesystem sharing | bind mounts | direct/clone/mountless | virtio-fs (or 9p/sshfs) |
| Setup/maintenance | low | low (turnkey) | high (you own image/net/security) |
| Workspace path fidelity | remapped | host absolute | host absolute (virtio-fs) |
| Best for | today's workflow | fastest safe Docker for agents | full control, Docker, no account |

If the goal is simply "agent gets Docker safely, soon", the Docker Sandboxes plan is less work.
This plan wins on distro freedom, no account, and complete control of the image, network and
lifecycle.

## 10. Effort

| Phase | Work | Rough size |
| --- | --- | --- |
| 0 | host KVM gate | minutes |
| 1 | Lima config + provisioning + UI/port check | half a day to 1 day |
| 2 | Cloud Hypervisor images, virtiofsd, TAP+nftables, launcher | 2-4 days |
| 3 | systemd unit, just recipes, docs, hardening | 1 day |
| — | ongoing | image/package updates, virtio-fs quirks |

## 11. Open questions

- Is virtio-fs (via Lima) stable enough here, or is 9p the pragmatic default despite the semantics?
- Does the missing inotify break the agent's dev loop in practice (esbuild/Vite/test watchers)?
- Cloud Hypervisor vs QEMU `microvm`: which gives the least friction for virtio-fs + networking?
- Egress model: host-side credential-injecting proxy vs plain NAT + allowlist.
- Do we want Lima's `--sync` (review-before-apply) as the default, at the cost of it not being live?

## Sources

- Firecracker design (device model): https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md
- Cloud Hypervisor virtio-fs: https://github.com/cloud-hypervisor/cloud-hypervisor/blob/main/docs/fs.md
- virtio-fs project (status, FAQ, DAX/coherence): https://virtio-fs.gitlab.io/
- QEMU microvm + virtio-fs (no PCI; use `vhost-user-fs-device`): https://lists.gnu.org/archive/html/qemu-discuss/2021-05/msg00085.html
- Debian `virtiofsd` (Rust, 1.13.2 in trixie): https://packages.debian.org/trixie/virtiofsd
- Lima filesystem mounts: https://lima-vm.io/docs/config/mount/
- Lima port forwarding: https://lima-vm.io/docs/config/port/
- Lima AI agents (mount only the project; `--sync`): https://lima-vm.io/docs/examples/ai/
- Lima security: https://lima-vm.io/docs/security/
- libkrun (virtio-fs, security caveats): https://github.com/containers/libkrun
- krunvm: https://github.com/containers/krunvm
- Firecracker device matrix: https://github.com/firecracker-microvm/firecracker/blob/main/docs/device-api.md
- QEMU microvm machine (limits): https://www.qemu.org/docs/master/system/i386/microvm.html
- crosvm shared directories (virtio-fs and 9p): https://crosvm.dev/book/devices/fs.html
- Cloud Hypervisor production/release notes: https://github.com/cloud-hypervisor/cloud-hypervisor/blob/main/README.md
