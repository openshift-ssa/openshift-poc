# Hardware Firmware Updates

[Firmware requirements for virtual media](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_on_bare_metal/index#ipi-install-firmware-requirements-for-installing-with-virtual-media_ipi-install-prerequisites) · [Live firmware updates](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_on_bare_metal/index#bmo-performing-a-live-update-to-the-hostfirmwarecomponents-resource_bare-metal-postinstallation-configuration)

Update BIOS, BMC, NIC, and storage-adapter firmware on bare metal servers. Do this twice in a POC: once before imaging, so every host boots a vendor-validated baseline, and again as a day-2 task on the running cluster, one node at a time.

BIOS *settings* (UEFI, virtualization extensions, boot order) are a separate step. A firmware flash can reset them. Re-check [BIOS/Firmware Settings](../../prerequisites/infrastructure.md#biosfirmware-settings) after every BIOS update.

!!! warning "One node at a time"
    Firmware updates reboot the host. Drain and update a single node, wait until it is `Ready`, then move to the next. Never take more than one control plane node down — etcd needs a quorum. Do not cancel a BMC firmware job once it has started. If it stalls, use the hardware vendor's recovery procedure.

## Prerequisites

- BMC reachability from the installation host (HTTPS/443). See [BMC / Out-of-Band Management](../../prerequisites/infrastructure.md#bmc-out-of-band-management).
- A firmware image the vendor has validated for that server generation. Red Hat publishes BMC versions tested with Redfish virtual media for installer-provisioned clusters in the link above. Assisted Installer and Agent-based installs have the same practical requirement: virtual media fails on old iDRAC and iLO firmware.
- The BMC must be able to download the image. The node does not fetch it. Serve the file from an HTTP(S) host on the BMC network, or upload it through the BMC UI.
- For a live cluster: `oc` logged in as a cluster admin, and a maintenance window.

| Component       | Examples                           | How to apply it                                                     |
| --------------- | ---------------------------------- | ------------------------------------------------------------------- |
| BIOS / UEFI     | System ROM                         | Metal³ `bios` component, or the BMC                                 |
| BMC             | iDRAC, iLO, CIMC                   | Metal³ `bmc` component, or the BMC                                  |
| NIC             | Intel E810, ConnectX-6, ConnectX-7 | Metal³ `nic:<id>` on supported adapters, otherwise the BMC          |
| HBA, RAID, disk | Storage controller, NVMe drive     | Vendor BMC only                                                     |

## Record the current versions

Collect versions before changing anything, and again after the host comes back. Keep them with the node record in the [POC Checklist](../../prerequisites/poc-checklist.md).

### From the BMC

This works before the cluster exists.

```bash
curl -sk "https://{{ bmc_ip }}/redfish/v1/UpdateService/FirmwareInventory?\$expand=." \
  -u {{ bmc_username }}:{{ bmc_password }} \
  | jq -r '.Members[]? | "\(.Name // .Id): \(.Version // "unknown")"'
```

If `$expand` is not supported, list `Members[]."@odata.id"` and GET each entry.

### From the cluster

Installer-provisioned hosts have a `HostFirmwareComponents` resource. Assisted Installer and Agent-based hosts are usually `externallyProvisioned`, so this inventory may be missing or stale. Use the BMC query above for those hosts.

```bash
oc get hostfirmwarecomponents -n openshift-machine-api
oc get hostfirmwarecomponents <host_name> -n openshift-machine-api -o yaml
```

Read `status.components`. Each entry has `component` (`bios`, `bmc`, or `nic:<id>`) and `currentVersion`.

## Update hosts outside Metal³

Use this path for [Assisted Installer](../../install-the-cluster/assisted-installer.md) and [Agent-based](../../install-the-cluster/agent-based.md) clusters, and for any device Metal³ does not flash (HBA, RAID, disk, unsupported NICs).

!!! warning "Externally provisioned hosts"
    Nodes installed with the Assisted Installer or Agent-based installer are typically `externallyProvisioned`. Ironic does not apply `HostFirmwareComponents` or `HostFirmwareSettings` changes on those hosts. Update them from the BMC.

Skip the drain steps when the host is not yet part of a cluster. Apply the image, power cycle, confirm the new version, then continue with [BIOS/Firmware Settings](../../prerequisites/infrastructure.md#biosfirmware-settings) and installation.

### On a running node

1. Pause node remediation so a reboot is not treated as a failure. Skip this if no `MachineHealthCheck` exists.

    ```bash
    oc -n openshift-machine-api annotate mhc <mhc_name> cluster.x-k8s.io/paused=""
    ```

2. If OpenShift Virtualization is installed, live-migrate virtual machines off the node before draining it. See [VM Failover Test](../operational-validation/vm-failover.md).

3. Cordon and drain the node:

    ```bash
    oc adm cordon <node_name>
    oc adm drain <node_name> --ignore-daemonsets --delete-emptydir-data --force
    ```

4. Apply the firmware image from the BMC (next section) and power cycle the host if the job does not reboot it for you.

5. Wait until the node is `Ready` and the BMC reports the new version:

    ```bash
    oc get node <node_name>
    ```

6. Uncordon the node and resume remediation:

    ```bash
    oc adm uncordon <node_name>
    oc -n openshift-machine-api annotate mhc <mhc_name> cluster.x-k8s.io/paused-
    ```

7. Confirm UEFI, virtualization extensions, and boot order survived the flash. Then start the next node.

### Apply the image with Redfish

`SimpleUpdate` is the common path on current iDRAC, iLO, and CIMC firmware. The `ImageURI` must be reachable from the BMC.

```bash
curl -sk -D - -o /dev/null -X POST \
  "https://{{ bmc_ip }}/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate" \
  -u {{ bmc_username }}:{{ bmc_password }} \
  -H "Content-Type: application/json" \
  -d '{"ImageURI":"https://firmware.example.com/BIOS.exe","TransferProtocol":"HTTPS"}'
```

The response `Location` header is the task to watch. When the task completes, power cycle if the host did not reboot on its own:

```bash
curl -sk -X POST \
  "https://{{ bmc_ip }}/redfish/v1/Systems/{{ system_id }}/Actions/ComputerSystem.Reset" \
  -u {{ bmc_username }}:{{ bmc_password }} \
  -H "Content-Type: application/json" \
  -d '{"ResetType":"PowerCycle"}'
```

Use the system id from [Testing BMC Access](../../prerequisites/infrastructure.md#testing-bmc-access). Dell hosts use `System.Embedded.1`. HPE hosts often use `1`.

=== "Dell iDRAC"

    Use a Dell Update Package (DUP) for that server generation. iDRAC 9 virtual media for installation is reliable on firmware **4.40.00.00 or newer**. If `SimpleUpdate` is disabled, start the update from the iDRAC web UI (**Maintenance → System Update**) or with remote RACADM:

    ```bash
    racadm -r {{ bmc_ip }} -u {{ bmc_username }} -p {{ bmc_password }} update -f BIOS.exe -l https://firmware.example.com/
    ```

=== "HPE iLO"

    Use an HPE firmware package (`.fwpkg`) for that server generation. iLO 5 **2.63 or later** is the floor Red Hat tested for installer-provisioned virtual media; newer generations need their own tested iLO build. If `SimpleUpdate` is disabled, upload the package in the iLO web UI under **Firmware & OS Software**.

=== "Cisco CIMC"

    Standalone UCS C-series and Intersight-managed servers should be on the CIMC or Intersight release listed in Red Hat's virtual-media firmware table before installation. Apply the vendor host upgrade package from CIMC or Intersight. Do not rely on `SimpleUpdate` unless the installed CIMC build documents that action.

## Update installer-provisioned hosts with Metal³

Use this path when the Bare Metal Operator provisioned the host (installer-provisioned infrastructure) and the component is `bios`, `bmc`, or a supported NIC. The live update does not deprovision the node. It still reboots the host.

Supported NIC updates are the Intel Ethernet 800 Series (`ice`) and NVIDIA Mellanox ConnectX-6 and ConnectX-7 (`mlx5`), validated on Dell hardware. Redfish may apply one NIC image to every adapter of that type in the server. Some BMCs show NIC inventory but reject the update — if `HostFirmwareComponents` will not accept a `nic:<id>` entry, flash that adapter from the BMC instead.

### Allow firmware updates on reboot

By default, `HostUpdatePolicy` blocks firmware changes after provisioning. Set `firmwareUpdates` to `onReboot` for the host you are updating:

```bash
oc edit hostupdatepolicy <host_name> -n openshift-machine-api
```

```yaml
spec:
  firmwareUpdates: onReboot
```

Leave `firmwareSettings` unchanged unless you also intend to push BIOS setting changes on the same reboot.

### Request the new image

```bash
oc patch hostfirmwarecomponents <host_name> -n openshift-machine-api --type merge -p \
  '{"spec":{"updates":[{"component":"bios","url":"https://firmware.example.com/BIOS.exe"}]}}'
```

`component` is `bios`, `bmc`, or `nic:<id>` from `status.components`. Add one list entry per component. A new URL is what triggers the update; repeating the same URL does not flash again.

### Apply the update

Live updates are disruptive. Try the image on a non-production host before using it on a control plane node. Clusters with fewer than three workers can go degraded while a worker is down.

```bash
oc adm cordon <node_name>
oc adm drain <node_name> --ignore-daemonsets --delete-emptydir-data --force

oc patch bmh <host_name> -n openshift-machine-api --type merge -p '{"spec":{"online":false}}'
```

Wait five minutes so controllers observe the node as offline, then power it back on. The Bare Metal Operator sets `status.operationalStatus` to `servicing` while the BMC applies the image, then back to `OK`. On failure it moves to `error` and retries.

```bash
oc patch bmh <host_name> -n openshift-machine-api --type merge -p '{"spec":{"online":true}}'

oc get bmh <host_name> -n openshift-machine-api -o jsonpath='{.status.operationalStatus}{"\n"}'
oc get hostfirmwarecomponents <host_name> -n openshift-machine-api -o jsonpath='{range .status.components[*]}{.component}{" "}{.currentVersion}{"\n"}{end}'
```

When `operationalStatus` is `OK` and the node is `Ready`, uncordon it and unpause `MachineHealthCheck` as in the out-of-band procedure. Confirm BIOS settings, then continue with the next host.
