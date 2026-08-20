# Install Troubleshooting

## Collecting Bootstrap Logs

If the installation times out during the bootstrap phase, gather diagnostic logs before the bootstrap node is destroyed:

```bash
openshift-install gather bootstrap --dir=install/ --bootstrap={{ bootstrap_ip }} --master="{{ master0_ip } { master1_ip } { master2_ip }"
```

This creates a compressed archive containing journal logs, container logs, and bootstrap progress information.

## Booting in Debug Mode

If you need to troubleshoot boot issues, modify the boot parameters at the GRUB menu:

1. Reboot the machine with the ISO
2. At the GRUB menu, press an arrow key to stop the automatic countdown
3. Select the default boot entry and press `e` to edit
4. Locate the `linux` or `linuxefi` line and add one of the parameters below
5. Press `Ctrl+X` or `F10` to boot with the modified parameters

### Debug Parameters

| Parameter                         | When to Use                                              |
| --------------------------------- | -------------------------------------------------------- |
| `rd.break`                        | Fix problems on root filesystem before systemd runs      |
| `systemd.unit=emergency.target`   | General system troubleshooting (corrupt fstab, services) |
| `init=/bin/bash`                  | Last resort when other methods fail                      |

## Known Issues

### x509: certificate signed by unknown authority

Installing an OpenShift cluster with the agent-based installer fails with "tls: failed to verify certificate: x509: certificate signed by unknown authority".

This usually happens when you are using a web proxy and the certificate being presented for proxied connections is an intermediate certificate from the proxy. You need to add the root certificate and intermediate certificates to the `additionalTrustBundle` in `install-config.yaml`.

### Host Not Registering

**Agent-based installer:**

- Verify MAC addresses match between `agent-config.yaml` and actual hardware
- Verify IP configuration is correct and on the expected subnet
- Check BMC virtual media is properly mounted

**Assisted Installer:**

- Verify the host is booted from the correct discovery ISO
- Check that the host can reach the Assisted Service API (`console.redhat.com` or on-prem endpoint)
- Verify network connectivity on the provisioning interface

### DNS Validation Fails

- Verify `api.{{ cluster_name }}.{{ base_domain }}` and `*.apps.{{ cluster_name }}.{{ base_domain }}` A records exist
- Test resolution from the same network: `dig +short api.{{ cluster_name }}.{{ base_domain }}`
- Verify reverse DNS (PTR) records for node IPs if hosts are registering with incorrect hostnames

### NTP Validation Fails

- Verify port 123/UDP is open to NTP servers
- Check `additionalNtpSources` in `agent-config.yaml`

### Image Pull Failures (Disconnected)

- Verify the mirror registry is accessible from all nodes
- Check the `ImageDigestMirrorSet` or `ImageContentSourcePolicy` is applied correctly
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
