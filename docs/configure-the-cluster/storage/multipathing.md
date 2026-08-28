# Multipathing

Multipathing is the practice of establishing multiple physical network paths between a server and a storage array so that if one path fails — a cable is pulled, an HBA dies, or a switch reboots — I/O continues over the surviving paths without interruption. Beyond redundancy, multipathing can also aggregate bandwidth across paths, improving throughput for block storage workloads. In a Fibre Channel or iSCSI environment, each host typically has two or more HBAs (or NICs) connected through independent fabric switches to redundant storage controller ports, giving every LUN at least two distinct paths. The multipath software on the host groups these paths, monitors their health, and decides how to distribute I/O across them.

On OpenShift, multipathing is handled at the RHCOS host layer, not by the CSI drivers themselves. The core `device-mapper-multipath` (`multipathd`) framework is the same regardless of vendor — what differs is the tuning parameters inside the configuration file.

## Transport Models

Not all storage uses `dm-multipath`. The multipath mechanism depends entirely on the transport protocol:

| Transport                     | Multipath Mechanism           | Configuration                                         |
| ----------------------------- | ----------------------------- | ----------------------------------------------------- |
| FC (SCSI)                     | `dm-multipath` (`multipathd`) | `multipath.conf` via MachineConfig                    |
| iSCSI                         | `dm-multipath` (`multipathd`) | `multipath.conf` via MachineConfig + `iscsid` enabled |
| NVMe-oF (NVMe/TCP, NVMe/FC)  | Native NVMe ANA               | Kernel handles natively — no `multipathd` needed      |
| Proprietary (e.g. SDC)        | Vendor kernel module          | Vendor-specific — no `multipathd`                     |

If your array uses NVMe-oF or a proprietary transport, you do not need anything on this page. The rest of this guide applies only to FC and iSCSI.

## How Multipathing Works on RHCOS

Because RHCOS is immutable, you cannot install or configure `multipathd` manually. Instead, you deliver configuration via a `MachineConfig` that drops a `/etc/multipath.conf` file (base64-encoded in an Ignition payload) onto the nodes and enables the `multipathd.service` systemd unit. RHCOS ships with `multipathd` available — the MachineConfig enables it and supplies the config.

The general flow:

1. Obtain the recommended `multipath.conf` from your storage vendor's OpenShift or RHEL documentation
2. Base64-encode it
3. Wrap it in a `MachineConfig` targeting `master`, `worker`, or both
4. Apply with `oc apply` — nodes reboot serially via the Machine Config Operator

!!! note "Root Device Multipathing"
    There is also a kernel argument path (`rd.multipath=default` plus `root=/dev/disk/by-label/dm-mpath-root`) if you need the root device itself multipathed. For attached persistent volumes — which is the common POC case — you only need the `multipath.conf` approach described here.

## The multipath.conf Structure

A `multipath.conf` file has four main sections:

### defaults

Global settings that apply unless overridden by a `device {}` block.

```ini
defaults {
    find_multipaths no
}
```

Setting `find_multipaths no` disables automatic device detection and forces `multipathd` to rely on explicit `blacklist_exceptions` matching. This is the recommended approach for OpenShift because it gives you precise control over which devices are multipathed.

### blacklist

Devices that `multipathd` should **never** claim.

```ini
blacklist {
    device {
        vendor  ".*"
        product ".*"
    }
}
```

!!! danger "Always Blacklist Local Disks"
    This wildcard blacklist blocks **all** devices from multipathing by default — including the RHCOS boot disk, local NVMe drives, and virtual disks (if running on a hypervisor). Without this, `multipathd` will attempt to claim every block device on the node, which can cause boot failures, root filesystem corruption, or nodes getting stuck during MachineConfig rollout.

### blacklist_exceptions

Devices that are exempt from the blacklist. This is where you whitelist your storage array by its SCSI `vendor` and `product` strings.

```ini
blacklist_exceptions {
    device {
        vendor  "<vendor-string>"
        product "<product-string>"
    }
}
```

Your storage vendor's documentation will specify the correct `vendor` and `product` values. You can also discover them from an attached device:

```bash
oc debug node/<worker-node> -- chroot /host multipathd show paths format "%d %s %v %p"
```

### devices

The tuning parameters for each device type. This is where vendors diverge — the values depend on whether the array is ALUA-based, active/active symmetric, or active/passive, and on the vendor's tested recommendations for path failover behavior.

```ini
devices {
    device {
        vendor                 "<vendor-string>"
        product                "<product-string>"
        path_grouping_policy   <vendor-recommended>
        path_selector          "<vendor-recommended>"
        prio                   <vendor-recommended>
        failback               <vendor-recommended>
        no_path_retry          <vendor-recommended>
        detect_prio            <vendor-recommended>
    }
}
```

Key parameters and what they control:

| Parameter                | What It Controls                                                              |
| ------------------------ | ----------------------------------------------------------------------------- |
| `path_grouping_policy`   | How paths are grouped — `group_by_prio` (ALUA) or `multibus` (active/active) |
| `path_selector`          | How I/O is distributed — `round-robin 0`, `service-time 0`, `queue-length 0` |
| `prio`                   | Path priority method — `alua` (asymmetric) or `const` (symmetric)            |
| `failback`               | When to return to preferred paths — `immediate`, `manual`, or seconds        |
| `no_path_retry`          | What happens when all paths fail — `queue`, `fail`, or a retry count         |
| `detect_prio`            | Auto-detect priority method from the device — `yes` or `no`                  |
| `fast_io_fail_tmo`       | Seconds before declaring a path failed (FC/iSCSI transport timeout)          |
| `dev_loss_tmo`           | Seconds before removing a failed path entirely from the kernel               |

!!! warning "Do Not Guess These Values"
    Always pull the recommended `device {}` block from your storage vendor's OpenShift or RHEL host connectivity documentation. Vendors test specific combinations of these parameters against their firmware and update them per OCP release. Incorrect values can cause I/O hangs, premature path failover, or silent data path degradation.

## Multi-Vendor Clusters

If you run multiple storage arrays on the same cluster, merge all vendor `device {}` entries into a single `multipath.conf` delivered by one MachineConfig. Do not apply separate MachineConfigs for `/etc/multipath.conf` — the last one wins and will overwrite the previous configuration.

The structure is the same: one `defaults` block, one `blacklist` block, and then multiple entries in both `blacklist_exceptions` and `devices` — one per array type. Pull each vendor's recommended `device {}` block from their documentation and combine them.

## MachineConfig Template

Encode your `multipath.conf` and deliver it via MachineConfig. You need one MachineConfig per node role (`master` and `worker`):

```bash
MULTIPATH_B64=$(cat multipath.conf | base64 -w0)
```

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: master
  name: 99-master-multipath-conf
spec:
  config:
    ignition:
      version: 3.5.0
    storage:
      files:
      - path: /etc/multipath.conf
        mode: 0644
        overwrite: true
        contents:
          source: "data:text/plain;charset=utf-8;base64,<MULTIPATH_B64>"
    systemd:
      units:
      - enabled: true
        name: multipathd.service
---
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: worker
  name: 99-worker-multipath-conf
spec:
  config:
    ignition:
      version: 3.5.0
    storage:
      files:
      - path: /etc/multipath.conf
        mode: 0644
        overwrite: true
        contents:
          source: "data:text/plain;charset=utf-8;base64,<MULTIPATH_B64>"
    systemd:
      units:
      - enabled: true
        name: multipathd.service
```

Replace `<MULTIPATH_B64>` with the output of the base64 encoding step.

## Verify

After the MachineConfigPool finishes rolling out:

```bash
oc debug node/<worker-node> -- chroot /host systemctl status multipathd

oc debug node/<worker-node> -- chroot /host multipath -ll

oc debug node/<worker-node> -- chroot /host multipathd show config
```

Healthy output from `multipath -ll` shows multiple paths per device with `active ready` status:

```
mpath0 (3600508b4000abcdef1234567890abcde) dm-2 VENDOR,PRODUCT
size=100G features='1 queue_if_no_path' hwhandler='0' wp=rw
|-+- policy='round-robin 0' prio=1 status=active
| `- 3:0:0:0 sda 8:0   active ready running
`-+- policy='round-robin 0' prio=1 status=enabled
  `- 4:0:0:0 sdb 8:16  active ready running
```

## Troubleshooting

### No Multipath Devices Visible

```bash
oc get mc | grep multipath

oc get mcp worker -o jsonpath='{.status.conditions[?(@.type=="Updated")].status}'

oc debug node/<worker-node> -- chroot /host cat /etc/multipath.conf
```

### Paths Showing as "faulty" or "ghost"

This typically indicates a zoning or network issue, not a multipath configuration problem. Verify:

- FC: zone configuration includes all target and initiator WWPNs
- iSCSI: all target portal IPs are reachable from all nodes (`iscsiadm -m discovery -t sendtargets -p <target-ip>`)
- Array-side: LUN masking / host groups include all node initiators

### MachineConfigPool Degraded After Applying Multipath Config

An invalid `multipath.conf` (e.g., syntax error in the base64-encoded content) can cause nodes to fail during boot:

```bash
oc get mcp worker

oc get mc 99-worker-multipath-conf -o yaml
```

Decode and validate the base64 content before reapplying:

```bash
echo "<base64-string>" | base64 -d
```
