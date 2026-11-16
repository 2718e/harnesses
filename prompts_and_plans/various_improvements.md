# VM and repository improvements

## Goal and scope

Make `4microvm` the active project in this repository, retain the VM's Tailscale identity across recreation, and add `just` and T3 Code to the guest. Keep the existing SSH and tmux remote access options available.

Nested virtualization and installing Lima inside the guest are deferred. Preserving T3 Code, Codex or tmux sessions, history or login state across VM recreation is also out of scope; Tailscale identity is the persistence goal here.

## 1. Retire dsh and clarify the repository

- Remove the top-level `dsh` subproject and remove installation, configuration, commands and documentation for the dsh harness inside the VM. Keep Codex and unrelated guest capabilities working.
- Update the root README to describe `4microvm` as the active project and link to its setup instructions. Review repository and guest-facing `AGENTS.md` files for clarity and stale references, taking care that guest configuration is not mistaken for instructions to the developer working on this repository.
- Search for remaining dsh references and decide whether historical planning notes should remain as history rather than being rewritten.

## 2. Install just in the guest

- Install `just` during guest provisioning, using a reproducible version and an installation method appropriate to the existing setup. Add it to the guest tool checks and document it where useful.
- Verify an agent can run `just --version` and validate or run a simple justfile inside the VM.

## 3. Preserve Tailscale identity

Use the persistent Lima disk, renamed `agentvm-persist` (short enough for older ext4 label handling) for Tailscale's state, in a dedicated root-owned directory inaccessible to the guest user. The disk survives `just recreate`; no host directory mount or additional disk is needed. The state contains sensitive machine credentials and must not be committed or exposed through guest-user permissions.

- Configure `tailscaled` to use its supported persistent state location on that disk. Inspect the installed Debian service and select the appropriate systemd or package configuration; ensure the configuration is in place before the daemon can start, including on first provisioning and subsequent boots.
- Require and verify the actual disk mount before starting the daemon. If the disk is absent or unavailable, fail clearly rather than silently creating a new identity on the VM root disk. Preserve the existing operator and Tailscale SSH behavior.
- Provide a safe, documented migration for an existing enrolled VM: stop the daemon, copy the existing state with root-only permissions, configure and verify the new state location before recreation. Do not overwrite existing persistent state silently; make the handling of conflicts explicit. If there is no existing identity to migrate, enroll once after setup.
- Keep recreation and setup idempotent. Ensure disk deletion commands, confirmations and documentation explain that deleting `agentvm-persist` now also deletes the Tailscale identity. Normal deletion/recreation of the VM must retain the disk.
- Document that identity persistence does not prevent key expiry, revocation or other tailnet policy from requiring reauthentication. Never run multiple VMs simultaneously using copies of the same Tailscale state.

## 4. Add T3 Code as another remote access option

- Install a known, reproducible T3 Code release in the guest, and configure it to use the guest user's existing Codex installation and login. Check current upstream installation and remote-access instructions during implementation.
- Make T3 accessible over Tailscale, using the supported headless or SSH-managed approach that meets the intended client workflow. Document the connection and authentication steps, service lifecycle, and how to start or stop it. Avoid exposing the service more broadly than needed.
- Retain the existing Tailscale SSH and tmux workflows. T3 must run with the guest user's access to the intended project mounts, without requiring general sudo.
- T3 state, Codex login and sessions, and tmux sessions may be lost when the VM is recreated; document this rather than adding persistence for them in this work.

## Verification

- Run the existing host-side tests and add focused coverage for changed lifecycle or provisioning behavior where practical. Check the documentation and repository for obsolete active dsh instructions.
- On a real Lima VM, verify provisioning, guest `just`, Codex availability, Tailscale SSH and tmux, and T3 access over Tailscale. Confirm T3 can start Codex as the guest user.
- Verify a normal stop/start and a recreation preserve the Tailscale device identity and access. Test migration of an existing identity separately if one is available. Verify missing persistent storage prevents Tailscale from starting with a fresh identity, and confirm disk deletion warnings describe the impact.
- If a full VM or remote-client test cannot be performed, report exactly what remains unverified; do not imply that host-side tests establish persistence or remote access.

## Implementation status

The storage rename uses `agentvm-persist`; the legacy disk is detected and never deleted automatically. A fresh enrollment is supported after the documented legacy reset. Migration of an existing root-only Tailscale identity to the renamed disk is not automated or verified and remains open. Full Lima, recreation and remote T3 verification also remain open in an environment with Lima.
