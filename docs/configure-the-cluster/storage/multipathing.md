# Multipathing

Multipathing is the practice of establishing multiple physical network paths between a server and a storage array so that if one path fails — a cable is pulled, an HBA dies, or a switch reboots — I/O continues over the surviving paths without interruption. Beyond redundancy, multipathing can also aggregate bandwidth across paths, improving throughput for block storage workloads. In a Fibre Channel or iSCSI environment, each host typically has two or more HBAs (or NICs) connected through independent fabric switches to redundant storage controller ports, giving every LUN at least two distinct paths. The multipath software on the host groups these paths, monitors their health, and decides how to distribute I/O across them.

On OpenShift, multipathing is handled at the RHCOS host layer, not by the CSI drivers themselves. The core mechanism is common across vendors — `device-mapper-multipath` (`multipathd`) running on RHCOS nodes — but the tuning parameters differ per array.

!!! tip "Vendor-Specific Installation Guides"
    The vendor-specific pages already include the MachineConfigs needed for their arrays. This page explains the *why* behind multipath configuration and how to handle multi-vendor clusters. For single-vendor setups, follow the instructions on the appropriate vendor page:

    - [NetApp Trident — iSCSI and Multipath MachineConfigs](netapp-trident.md#iscsi-and-multipath-machineconfigs)
    - [Dell Unity XT — Multipath Configuration](dell/dell-unity.md#2c-multipath-configuration)

## How Multipathing Works on RHCOS

Because RHCOS is immutable, you cannot install or configure `multipathd` manually. Instead, you deliver configuration via a `MachineConfig` that drops a `/etc/multipath.conf` file (base64-encoded in an Ignition payload) onto the nodes and enables the `multipathd.service` systemd unit. RHCOS ships with `multipathd` available — the MachineConfig enables it and supplies the config.

The general flow:

1. Create a `multipath.conf` with your vendor-specific `devices {}` stanza
2. Base64-encode it
3. Wrap it in a `MachineConfig` targeting `master`, `worker`, or both
4. Apply with `oc apply` — nodes reboot serially via the Machine Config Operator

!!! note "Root Device Multipathing"
    There is also a kernel argument path (`rd.multipath=default` plus `root=/dev/disk/by-label/dm-mpath-root`) if you need the root device itself multipathed. For attached persistent volumes — which is the common POC case — you only need the `multipath.conf` `devices {}` stanza described here.

## Transport Models

Not all storage uses `dm-multipath`. The mechanism depends on the transport protocol:

| Transport        | Multipath Mechanism          | Configuration                                         |
| ---------------- | ---------------------------- | ----------------------------------------------------- |
| FC (SCSI)        | `dm-multipath` (`multipathd`)| `multipath.conf` via MachineConfig                    |
| iSCSI            | `dm-multipath` (`multipathd`)| `multipath.conf` via MachineConfig + `iscsid` enabled |
| NVMe-oF (NVMe/TCP, NVMe/FC) | Native NVMe ANA   | Kernel handles natively — no `multipathd` needed      |
| Dell PowerFlex   | Proprietary SDC              | SDC kernel module — no `multipathd`                   |

## Vendor Device Configurations

The differences between vendors live in the `device {}` entries within `multipath.conf`, keyed by SCSI `vendor` and `product` strings. Each vendor publishes recommended values for `path_selector`, `path_grouping_policy`, `prio`, `failback`, `no_path_retry`, and related parameters. These reflect whether the array is ALUA-based, active/active, or active/passive.

!!! warning "Always Use Vendor-Published Values"
    Pull the current recommended `multipath.conf` device block from each vendor's OpenShift-specific documentation rather than hand-writing values. Vendors update recommended parameters per platform, firmware version, and OCP release.

### NetApp ONTAP (Trident CSI)

ONTAP is ALUA-based. NetApp's recommended device block uses ALUA priority and round-robin path selection:

```ini
devices {
    device {
        vendor                 "NETAPP"
        product                "LUN.*"
        path_grouping_policy   group_by_prio
        path_selector          "round-robin 0"
        prio                   alua
        failback               immediate
        no_path_retry          queue
        detect_prio            yes
        features               "3 queue_if_no_path pg_init_retries 50"
        dev_loss_tmo           infinity
        fast_io_fail_tmo       5
    }
}
```

Key points:

- `find_multipaths no` in the `defaults {}` block — NetApp recommends explicit device matching rather than automatic detection
- Blacklist all devices, then whitelist only NetApp LUNs via `blacklist_exceptions`
- Trident handles iSCSI/FC/NVMe-oF attachment but relies on the host multipath config being present for iSCSI and FC

Reference: [NetApp Trident — Worker Node Preparation](https://docs.netapp.com/us-en/trident/trident-use/worker-node-prep.html)

### Dell PowerStore

PowerStore is ALUA-based and supports FC, iSCSI, and NVMe-oF. For FC and iSCSI:

```ini
devices {
    device {
        vendor                 "DellEMC"
        product                "PowerStore"
        path_grouping_policy   group_by_prio
        path_selector          "round-robin 0"
        prio                   alua
        failback               immediate
        no_path_retry          10
        detect_prio            yes
        rr_min_io_rq           1
    }
}
```

For NVMe-oF connections, PowerStore uses native NVMe ANA multipathing — no `dm-multipath` configuration is needed.

Reference: [Dell PowerStore — Host Connectivity Guide](https://www.dell.com/support/home/en-us/product-support/product/powerstore/docs)

### Dell PowerMax

PowerMax is ALUA-based (when SCSI 3 Persistent Reservations are enabled):

```ini
devices {
    device {
        vendor                 "EMC"
        product                "SYMMETRIX"
        path_grouping_policy   group_by_prio
        path_selector          "service-time 0"
        prio                   alua
        failback               immediate
        no_path_retry          6
        detect_prio            yes
        rr_min_io_rq           1
    }
}
```

Reference: [Dell PowerMax — Host Connectivity Guide](https://www.dell.com/support/home/en-us/product-support/product/powermax/docs)

### Dell Unity XT

Unity XT is ALUA-based over FC and iSCSI:

```ini
devices {
    device {
        vendor                 "DGC"
        product                ".*"
        path_grouping_policy   group_by_prio
        path_selector          "round-robin 0"
        prio                   alua
        failback               immediate
        no_path_retry          5
        detect_prio            yes
        retain_attached_hw_handler yes
    }
}
```

A simpler defaults-only approach also works for POC environments:

```ini
defaults {
    user_friendly_names yes
    find_multipaths     yes
    polling_interval    5
}
blacklist {
}
```

Reference: [Dell Unity XT — Host Configuration Guide](https://www.dell.com/support/home/en-us/product-support/product/unity-xt/docs)

### Dell PowerFlex (VxFlex OS)

PowerFlex does **not** use standard SCSI multipathing. It uses its own Storage Data Client (SDC) kernel module that provides native multipathing at the application layer. Do not configure `dm-multipath` for PowerFlex volumes — the SDC handles all path management internally.

### HPE (3PAR / Primera / Alletra)

HPE arrays are ALUA-based:

```ini
devices {
    device {
        vendor                 "3PARdata"
        product                "VV"
        path_grouping_policy   group_by_prio
        path_selector          "round-robin 0"
        prio                   alua
        failback               immediate
        no_path_retry          18
        detect_prio            yes
        rr_min_io_rq           1
        fast_io_fail_tmo       10
        dev_loss_tmo           infinity
    }
}
```

Reference: [HPE Alletra Storage Server — Host Connectivity Guide](https://support.hpe.com)

### Pure Storage (FlashArray)

Pure Storage FlashArray is active/active symmetric, not ALUA:

```ini
devices {
    device {
        vendor                 "PURE"
        product                "FlashArray"
        path_grouping_policy   multibus
        path_selector          "queue-length 0"
        prio                   const
        failback               immediate
        no_path_retry          10
        fast_io_fail_tmo       10
        dev_loss_tmo           600
    }
}
```

Key difference: Pure is fully active/active symmetric, so it uses `multibus` (all paths in one group) and `prio const` (all paths equal priority) instead of ALUA-based grouping.

Reference: [Pure Storage — OpenShift Deployment Guide](https://support.purestorage.com)

## Multi-Vendor Clusters

If you run multiple storage arrays on the same cluster, merge all vendor `device {}` entries into a single `multipath.conf` delivered by one MachineConfig. Do not apply separate MachineConfigs for `/etc/multipath.conf` — the last one wins.

### Example: NetApp + Dell Unity XT

```ini
defaults {
    find_multipaths no
}

blacklist {
    device {
        vendor  ".*"
        product ".*"
    }
}

blacklist_exceptions {
    device {
        vendor  "NETAPP"
        product "LUN.*"
    }
    device {
        vendor  "DGC"
        product ".*"
    }
}

devices {
    device {
        vendor                 "NETAPP"
        product                "LUN.*"
        path_grouping_policy   group_by_prio
        path_selector          "round-robin 0"
        prio                   alua
        failback               immediate
        no_path_retry          queue
        detect_prio            yes
        features               "3 queue_if_no_path pg_init_retries 50"
        dev_loss_tmo           infinity
        fast_io_fail_tmo       5
    }
    device {
        vendor                 "DGC"
        product                ".*"
        path_grouping_policy   group_by_prio
        path_selector          "round-robin 0"
        prio                   alua
        failback               immediate
        no_path_retry          5
        detect_prio            yes
        retain_attached_hw_handler yes
    }
}
```

### MachineConfig Template

Encode your `multipath.conf` and deliver it via MachineConfig:

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
# Confirm multipathd is running
oc debug node/<worker-node> -- chroot /host systemctl status multipathd

# List multipath devices
oc debug node/<worker-node> -- chroot /host multipath -ll

# Check multipath configuration
oc debug node/<worker-node> -- chroot /host multipathd show config
```

Healthy output from `multipath -ll` shows multiple paths per device with `active ready` status:

```
mpath0 (360060160a1234567890abcdef1234567) dm-2 DGC,VRAID
size=100G features='1 queue_if_no_path' hwhandler='1 emc' wp=rw
|-+- policy='round-robin 0' prio=1 status=active
| `- 3:0:0:0 sda 8:0   active ready running
`-+- policy='round-robin 0' prio=1 status=enabled
  `- 4:0:0:0 sdb 8:16  active ready running
```

## Troubleshooting

### No Multipath Devices Visible

```bash
# Confirm the MachineConfig was applied
oc get mc | grep multipath

# Check the MachineConfigPool status
oc get mcp worker -o jsonpath='{.status.conditions[?(@.type=="Updated")].status}'

# Verify multipath.conf was written
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
# Check for degraded nodes
oc get mcp worker

# Review the failing MachineConfig
oc get mc 99-worker-multipath-conf -o yaml
```

Decode and validate the base64 content before reapplying:

```bash
echo "<base64-string>" | base64 -d
```
