# Installer Provisioned Infrastructure (IPI)

IPI is the recommended installation method when the installer can directly provision and manage infrastructure, such as with VMware vSphere.

## Steps

1. Prepare the `install-config.yaml` with platform-specific settings
2. Run the installer
3. Wait for bootstrap to complete
4. Wait for installation to finish

```bash
openshift-install create cluster --dir ~/ocp-install --log-level=info
```

Monitor bootstrap progress:

```bash
openshift-install wait-for bootstrap-complete --dir ~/ocp-install --log-level=info
```

Monitor installation completion:

```bash
openshift-install wait-for install-complete --dir ~/ocp-install --log-level=info
```

---

## Details

### vSphere Platform Configuration

For vSphere IPI, update the platform section in `install-config.yaml`:

```yaml
platform:
  vsphere:
    vcenter: vcenter.example.com
    username: administrator@vsphere.local
    password: <vcenter_password>
    datacenter: DC1
    defaultDatastore: datastore1
    cluster: Cluster1
    network: VM Network
    apiVIPs:
      - 10.0.0.5
    ingressVIPs:
      - 10.0.0.6
```

### vSphere Prerequisites

- vCenter 7.0 or later
- A user with the required privileges (see [vSphere permissions documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/installing_on_vsphere/ipi-vsphere))
- A folder and resource pool for the cluster
- DHCP available on the target network

### What IPI Automates

- VM creation and configuration
- Boot disk and ignition delivery
- Control plane and worker provisioning
- Bootstrap node creation and teardown

### Troubleshooting

Access the bootstrap node logs:

```bash
ssh -i ~/.ssh/ocp-key core@<bootstrap-ip>
journalctl -b -f -u release-image.service -u bootkube.service
```

Check cluster operator status after bootstrap:

```bash
export KUBECONFIG=~/ocp-install/auth/kubeconfig
oc get clusteroperators
```
