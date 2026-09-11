# Install Troubleshooting

## Collecting Bootstrap / Install Logs

The right log-gathering command depends on which installer method you used.

### IPI and UPI (with a distinct bootstrap machine)

`openshift-install gather bootstrap` applies only to installs that create a **separate bootstrap VM** (IPI or UPI with an explicit bootstrap node). If the installation times out during the bootstrap phase, gather diagnostic logs before the bootstrap node is destroyed:

```bash
openshift-install gather bootstrap --dir=install \
  --bootstrap={{ bootstrap_ip }} \
  --master={{ master0_ip }} \
  --master={{ master1_ip }} \
  --master={{ master2_ip }}
```

This creates a compressed archive containing journal logs, container logs, and bootstrap progress information.

### Agent-based installer

There is no separate bootstrap host to gather from. Instead, stream debug-level logs from the rendezvous host and collect the agent-gather archive:

```bash
# Stream bootstrap progress with debug output
openshift-install agent wait-for bootstrap-complete --dir=install --log-level=debug

# Collect the agent-gather diagnostic archive from the rendezvous host
ssh core@<rendezvousIP> agent-gather -O > agent-gather.tar.xz
```

### Assisted Installer

On the discovery host, inspect the agent journal for registration and installation errors:

```bash
sudo journalctl TAG=agent
```

For post-install issues, use [must-gather](../workloads-and-operations/day-2-operations/must-gather.md) instead.

## Booting in Debug Mode

If you need to troubleshoot boot issues, modify the boot parameters at the GRUB menu:

1. Reboot the machine with the ISO
2. At the GRUB menu, press an arrow key to stop the automatic countdown
3. Select the default boot entry and press `e` to edit
4. Locate the `linux` or `linuxefi` line and add one of the parameters below
5. Press `Ctrl+X` or `F10` to boot with the modified parameters

### Debug Parameters

| Parameter                       | When to Use                                                                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rd.break`                      | Fix problems on root filesystem before systemd runs                                                                                               |
| `rd.break=initqueue`           | Interrupts at the dracut main loop — use for Assisted/Agent discovery ISO boot failures to inspect NMState/network from the initramfs shell       |
| `systemd.unit=emergency.target` | General system troubleshooting (corrupt fstab, services) — applies to an already-installed RHCOS rootfs only                                      |
| `init=/bin/bash`                | Last resort when other methods fail — applies to an already-installed RHCOS rootfs only                                                           |

## Known Issues

### x509: certificate signed by unknown authority

Installing an OpenShift cluster with the agent-based installer fails with "tls: failed to verify certificate: x509: certificate signed by unknown authority".

This usually happens when you are using a web proxy and the certificate being presented for proxied connections is an intermediate certificate from the proxy. You need to add the root certificate and intermediate certificates to the `additionalTrustBundle` in `install-config.yaml`.

### Host Not Registering

**Agent-based installer:**

- Verify MAC addresses match between `agent-config.yaml` and actual hardware
- Verify IP configuration is correct and on the expected subnet
- Check BMC virtual media is properly mounted
- Verify TCP 8090 is reachable from all hosts to the rendezvous host (the assisted-service API runs on this port)

**Assisted Installer:**

- Verify the host is booted from the correct discovery ISO
- Check that the host can reach the Assisted Service API (`console.redhat.com` or on-prem endpoint)
- Verify network connectivity on the provisioning interface
- Check `sudo journalctl TAG=agent` on the discovery host for registration errors

### DNS Validation Fails

{% raw %}
- Verify `api.{{ cluster_name }}.{{ base_domain }}`, `api-int.{{ cluster_name }}.{{ base_domain }}`, and `*.apps.{{ cluster_name }}.{{ base_domain }}` A records exist
- `api-int` resolution is a **blocking pre-install validation** for user-managed networking — the install will not proceed if it cannot be resolved
- Test resolution from the same network: `dig +short api.{{ cluster_name }}.{{ base_domain }}` and `dig +short api-int.{{ cluster_name }}.{{ base_domain }}`
{% endraw %}
- Verify reverse DNS (PTR) records for node IPs if hosts are registering with incorrect hostnames

!!! warning "Wildcard DNS scope"
    Do **not** create a wildcard at `*.{{ cluster_name }}.{{ base_domain }}` — this will match `api` and `api-int` but also catch traffic not intended for the cluster ingress. The wildcard must be scoped to `*.apps.{{ cluster_name }}.{{ base_domain }}` only.

### NTP Validation Fails

- Verify port 123/UDP is open to NTP servers
- Check `additionalNTPSources` in `agent-config.yaml`

### Image Pull Failures (Disconnected)

- Verify the mirror registry is accessible from all nodes
- Check the `ImageDigestMirrorSet` is applied correctly
- Confirm the registry CA is in `additionalTrustBundle`
- Verify credentials in the pull secret can authenticate to the mirror

### MachineConfigPool Degraded

After installation or node reboot, nodes get stuck in `NotReady` with MCP reporting degraded:

```bash
oc get mcp
oc describe mcp worker
```

Common causes:

- Failed to pull an image referenced in a MachineConfig (check mirror/pull secret)
- Invalid Ignition or Butane config syntax
- Certificate trust issue preventing image pulls

### Collecting Must-Gather

For general post-install troubleshooting, collect a must-gather archive to share with Red Hat support:

```bash
oc adm must-gather
```

For operator-specific diagnostics, target the operator's image:

```bash
oc adm must-gather --image=registry.redhat.io/odf4/odf-must-gather-rhel9:latest
```
