# Install Troubleshooting

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

This usually happens when you are using a web proxy and the certificate being presented for proxied connections is an intermediate certificate from the proxy. You need to add the root certificate and intermediaries to the `additionalTrustBundle` in `install-config.yaml`.

### Host Not Registering

- Verify MAC addresses match between `agent-config.yaml` and actual hardware
- Verify IP configuration is correct and on the expected subnet
- Check BMC virtual media is properly mounted

### DNS Validation Fails

- Verify `api.{{ cluster_name }}.{{ base_domain }}` and `*.apps.{{ cluster_name }}.{{ base_domain }}` A records exist
- Test resolution from the same network: `dig +short api.{{ cluster_name }}.{{ base_domain }}`

### NTP Validation Fails

- Verify port 123/UDP is open to NTP servers
- Check `additionalNtpSources` in `agent-config.yaml`
