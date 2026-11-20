# Nested VM integration test

From `4microvm` on the host, run `just test-nested` while `agentvm` is
running. The test needs internet access, available nested KVM, and enough
outer-VM resources for an inner VM with 2 CPUs, 2 GiB RAM and a 12 GiB disk.
It downloads an Ubuntu image and installs Docker in the inner guest on its first
run; it then runs an Alpine container and stops the guest. Later runs reuse the
guest and image. This is a slow integration test, separate from `just test`.

The test's dedicated Lima home is `~/.lima-nested-smoke` inside the outer VM.
It refuses to use an unmarked existing home or a running test instance. The
test VM and Docker data are stored on the outer VM's root filesystem and are
lost when it is recreated. To inspect the stopped guest from the outer VM:

```sh
export LIMA_HOME="$HOME/.lima-nested-smoke"
limactl list
limactl start nested-smoke-docker
limactl shell nested-smoke-docker
limactl stop nested-smoke-docker
```

The outer guest's user needs access to `/dev/kvm`; a new login may be needed
after provisioning changes group membership. `just test-nested` uses
`/usr/bin/sg` to refresh the group for its own command (the plain `sg` name in
this environment is ast-grep). Shut down inner VMs before stopping or
recreating the outer VM: the outer `just stop` does not yet check for them.

New outer VMs install QEMU, OVMF and pinned Lima during provisioning. Existing
VMs do not automatically receive provisioning changes; recreate one to apply
them, or install those prerequisites and add the guest user to the `kvm`
group manually. Recreating the outer VM replaces its primary disk and logins.

The earlier `~/.lima-nested-experiment` and its `nested-smoke` instance are a
separate manual experiment; this test does not modify them.
