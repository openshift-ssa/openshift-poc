# Example Virtual Machines

This guide walks through deploying an example Red Hat Enterprise Linux 9 virtual machine on OpenShift Virtualization. Use it as a smoke test after [OpenShift Virtualization](../post-installation/virtualization.md) is installed, or as a starting point before [failover](../operations/vm-failover.md) and [backup/restore](../operations/vm-backup-restore.md) exercises.

## Prerequisites

- OpenShift Virtualization installed and the HyperConverged instance is healthy
- A default virtualization StorageClass (`storageclass.kubevirt.io/is-default-virt-class: "true"`)
- Boot sources available in the cluster
- `oc` and optionally `virtctl` installed locally

Verify boot sources before creating a VM:

```bash
oc get datasources -n openshift-virtualization-os-images
```

Templates that show **Source available** in the console are ready to use. If RHEL sources are missing, wait for the DataImportCron jobs to finish or confirm the cluster can pull from the Red Hat registry.

## Create a Project

```bash
oc new-project example-vms
```

## Deploy from the Web Console

1. Go to **Virtualization** → **VirtualMachines** → ensure you are in the `example-vms` project → click **Create** → **From template**
2. Select **Red Hat Enterprise Linux 9** (choose a tile with **Source available**)
3. Name the VM `example-rhel9`
4. Click **Customize VirtualMachine**

### Optional: Set Login Credentials

5. Open the **Scripts** tab
6. Under **Cloud-init**, set a password for the guest user (or paste an SSH public key). Example cloud-init:

  ```yaml
  #cloud-config
  user: cloud-user
  password: Pass123!
  chpasswd:
    expire: false
  ```

  !!! note
      RHEL cloud images do not ship with a usable default password. Set a password or SSH key before first boot, or you will not be able to log in from the console.

### Optional: Confirm Disk and Run Strategy

7. Open the **Disks** tab and confirm the root disk uses your virtualization StorageClass
8. Prefer **ReadWriteMany (RWX)** if you plan to live-migrate or test failover later
9. On the **Overview** tab, leave **Start this VirtualMachine after creation** selected so the VM boots immediately (`runStrategy: Always`)

### Create and Wait

10. Click **Create VirtualMachine**
11. Wait until the VM status shows **Running**

  Provisioning clones the boot source PVC first. On a cold cluster this can take several minutes.

## Verify the Virtual Machine

From the CLI:

```bash
oc get vm,vmi example-rhel9 -n example-vms -o wide
```

The `VirtualMachine` should be `Ready`, and the `VirtualMachineInstance` should show `Running` with a node assigned.

Check guest interfaces and IP (requires the QEMU guest agent, included on RHEL templates):

```bash
oc get vmi example-rhel9 -n example-vms -o jsonpath='{.status.interfaces}' | jq
```

Watch creation events if the VM stays in provisioning:

```bash
oc get events -n example-vms --field-selector involvedObject.name=example-rhel9 --sort-by='.lastTimestamp'
```

## Access the Console

1. Go to **Virtualization** → **VirtualMachines** → click `example-rhel9`
2. Open the **Console** tab
3. Log in as `cloud-user` with the password (or SSH key) you set in cloud-init
4. Confirm the guest is healthy:

  ```bash
  cat /etc/redhat-release
  ip addr
  ```

## Deploy from the CLI (Optional)

You can create the same style of VM with `virtctl` using a cluster DataSource:

```bash
virtctl create vm \
  --name example-rhel9 \
  --instancetype u1.medium \
  --preference rhel.9 \
  --volume-import type:ds,src:openshift-virtualization-os-images/rhel9 \
  --cloud-init-user cloud-user \
  --cloud-init-password Pass123! \
  | oc apply -n example-vms -f -
```

Start the VM if it was created stopped:

```bash
virtctl start example-rhel9 -n example-vms
```

Watch until it is running:

```bash
oc get vmi example-rhel9 -n example-vms -w
```

!!! tip
    Run `virtctl create vm --help` for additional options such as CPU/memory overrides, extra disks, and cloud-init SSH keys.

## Cleanup

```bash
oc delete vm example-rhel9 -n example-vms
oc delete project example-vms
```

When deleting from the web console, confirm that associated disks (PVCs) are removed if you do not need to reuse them.

## Next Steps

- [VM Failover Test](../operations/vm-failover.md) — validate node-loss recovery within the 120-second target
- [VM Backup and Restore](../operations/vm-backup-restore.md) — exercise OADP with the kubevirt plugin
- [Networking](../post-installation/networking.md) — attach VMs to a CUDN for persistent IPAM
