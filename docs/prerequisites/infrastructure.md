# Infrastructure

Provision compute resources that meet or exceed the minimum requirements for each node type. Primary POC paths use **bare metal**, but [Agent-Based](../install-the-cluster/agent-based.md) and [vSphere IPI](../install-the-cluster/other-installation-methods/vmware-install.md) installs on virtual machines are also supported — see [Prerequisites](index.md).

!!! info "OpenShift Terminology"
    A quick note on terminology. In OpenShift, the same server can be described at three layers:  
    
    - **Host** (`BareMetalHost`, managed by the Bare Metal Operator) is the physical box and its BMC, answering how to power and provision the hardware  
    - **Machine** (`Machine`, managed by the Machine API and grouped into a `MachineSet`) is the infrastructure instance that backs a node and is the unit you scale which can be a physical box or a virtual machine  
    - **Node** (`Node`) is the Kubernetes-level member that runs a kubelet and that the scheduler places pods onto. 

## Required Hardware

Consider these recommended POC values — the more the better. 

!!! note "Official Minimums"
    The official OpenShift minimums are 4 vCPU / 16 GB / 100 GB (control plane) and 2 vCPU / 8 GB / 100 GB (compute), but POC workloads — especially OpenShift Virtualization — need significantly more.

    For Agent-based HA installations, the recommended minimum is 8 vCPU / 16 GB / 120 GB per node.

### Single Cluster Installation

| Host Type     | Count | CPU | Memory | Install Disk | Secondary Disk |
| ------------- | ----- | --- | ------ | ------------ | -------------- |
| Installation  | 1     | 4   | 16 GB  | 60 GB        | ---            |
| Control Plane | 3     | 16  | 32 GB  | 120 GB       | ---            |
| Worker        | 3     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |

### Fleet Management (Hub + Spoke) Installation

| Host Type           | Count | CPU | Memory | Install Disk | Secondary Disk |
| ------------------- | ----- | --- | ------ | ------------ | -------------- |
| Installation        | 1     | 4   | 16 GB  | 60 GB        | ---            |
| Hub (SNO)           | 1     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |
| Spoke Control Plane | 3     | 16  | 32 GB  | 120 GB       | ---            |
| Spoke Worker        | 3     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |

### Hardware Notes

!!! tip "Do I need an installation host?"
    No, as long as the computer you are working from can install the tools listed in [Installation Host](installation-host.md) without opening tickets (`oc`, `openshift-install`, `nmstatectl`, `git`, `podman`, and related utilities). Optional day-2 tools such as `helm`, `kustomize`, or `istioctl` are only needed for specific workloads. We **highly recommend** a centralized installation host so work does not stop if a laptop is unavailable. 

!!! note "Machine Type"
    The installation and hub machine can be either a virtual machine or bare metal host. They just need network access to the other hosts. Cluster nodes are typically bare metal for production-like POCs; virtual machines (for example on vSphere) are valid when following the Agent-Based or vSphere IPI guides. 

!!! note "CPU Architecture" 
    For the POC, prefer the same vendor and generation CPU architectures across all machines. 

!!! warning "Install Disk"
    The etcd instances needs to run on a block device that can write at least 50 IOPS of 8 KB sequentially, including fdatasync, in under 10 ms. Heavily loaded clusters should target 500 sequential IOPS of 8 KB in 2 ms. See [etcd Storage](storage.md#etcd-storage) for the full disk performance requirements.

!!! note "Secondary Disk" 
    The secondary disk in the worker nodes can be used for storage if you decide to use OpenShift Data Foundation as your storage solution in the cluster. If you are using an already existing storage provider, the secondary disk is optional in the cluster. 

## Network Interface Requirements

Only a single NIC is required for OpenShift. To perform more advanced networking, 4 x 10 GbE is recommended for bond0/bond1. Production Virtualization setups typically use **two bonds** — mgmt (bond0) and a trunked data plane (bond1) with VLANs for VM, storage, and live migration — see [Networking](networking.md#production-multi-bond-architecture). A third physical bond for storage is optional when the network team requires a dedicated uplink instead of a storage VLAN. 

## Machine Information

Collect the interface names, MAC addresses for ALL NICs, and the install disk location on the machines. Below is an example table of values needed.

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpinstall</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:E0</td>
    <td>-</td>
    <td>10.0.0.5</td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocphub</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:E1</td>
    <td>-</td>
    <td>10.0.0.6</td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpcp01</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:ED</td>
    <td>bond0</td>
    <td>10.0.0.7</td>
  </tr>
  <tr>
    <td>eno2</td>
    <td>A0:B1:C2:D3:E4:E2</td>
    <td>bond0</td>
    <td></td>
  </tr>
  <tr>
    <td>eno3</td>
    <td>A0:B1:C2:D3:E4:E3</td>
    <td>bond1</td>
    <td></td>
  </tr>
  <tr>
    <td>eno4</td>
    <td>A0:B1:C2:D3:E4:E4</td>
    <td>bond1</td>
    <td></td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpcp02</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:E5</td>
    <td>bond0</td>
    <td>10.0.0.8</td>
  </tr>
  <tr>
    <td>eno2</td>
    <td>A0:B1:C2:D3:E4:E6</td>
    <td>bond0</td>
    <td></td>
  </tr>
  <tr>
    <td>eno3</td>
    <td>A0:B1:C2:D3:E4:E7</td>
    <td>bond1</td>
    <td></td>
  </tr>
  <tr>
    <td>eno4</td>
    <td>A0:B1:C2:D3:E4:E8</td>
    <td>bond1</td>
    <td></td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpcp03</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:E9</td>
    <td>bond0</td>
    <td>10.0.0.9</td>
  </tr>
  <tr>
    <td>eno2</td>
    <td>A0:B1:C2:D3:E4:EA</td>
    <td>bond0</td>
    <td></td>
  </tr>
  <tr>
    <td>eno3</td>
    <td>A0:B1:C2:D3:E4:EB</td>
    <td>bond1</td>
    <td></td>
  </tr>
  <tr>
    <td>eno4</td>
    <td>A0:B1:C2:D3:E4:EC</td>
    <td>bond1</td>
    <td></td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpw01</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:F1</td>
    <td>bond0</td>
    <td>10.0.0.10</td>
  </tr>
  <tr>
    <td>eno2</td>
    <td>A0:B1:C2:D3:E4:F2</td>
    <td>bond0</td>
    <td></td>
  </tr>
  <tr>
    <td>eno3</td>
    <td>A0:B1:C2:D3:E4:F3</td>
    <td>bond1</td>
    <td></td>
  </tr>
  <tr>
    <td>eno4</td>
    <td>A0:B1:C2:D3:E4:F4</td>
    <td>bond1</td>
    <td></td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpw02</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:F5</td>
    <td>bond0</td>
    <td>10.0.0.11</td>
  </tr>
  <tr>
    <td>eno2</td>
    <td>A0:B1:C2:D3:E4:F6</td>
    <td>bond0</td>
    <td></td>
  </tr>
  <tr>
    <td>eno3</td>
    <td>A0:B1:C2:D3:E4:F7</td>
    <td>bond1</td>
    <td></td>
  </tr>
  <tr>
    <td>eno4</td>
    <td>A0:B1:C2:D3:E4:F8</td>
    <td>bond1</td>
    <td></td>
  </tr>
</table>

<table>
  <tr>
    <td><b>Hostname</b></td>
    <td>hl01ocpw03</td>
    <td><b>Disk Hint</b></td>
    <td>/dev/sda</td>
  </tr>
  <tr>
    <td><b>BMC IP</b></td>
    <td></td>
    <td><b>BMC Credentials</b></td>
    <td></td>
  </tr>
  <tr>
    <td><b>Interface</b></td>
    <td><b>MAC Address</b></td>
    <td><b>Bond</b></td>
    <td><b>IP Address</b></td>
  </tr>
  <tr>
    <td>eno1</td>
    <td>A0:B1:C2:D3:E4:F9</td>
    <td>bond0</td>
    <td>10.0.0.12</td>
  </tr>
  <tr>
    <td>eno2</td>
    <td>A0:B1:C2:D3:E4:FA</td>
    <td>bond0</td>
    <td></td>
  </tr>
  <tr>
    <td>eno3</td>
    <td>A0:B1:C2:D3:E4:FB</td>
    <td>bond1</td>
    <td></td>
  </tr>
  <tr>
    <td>eno4</td>
    <td>A0:B1:C2:D3:E4:FC</td>
    <td>bond1</td>
    <td></td>
  </tr>
</table>

## Machine Details

### NIC Naming

On modern RHEL (RHEL CoreOS included), NICs use predictable network interface names generated at boot based on hardware topology and firmware information:

- `eno1`, `eno2` — onboard NICs (from BIOS/firmware)
- `ens1f0`, `ens1f1` — PCI Express slots ("s" = slot, "f" = function)
- `enp3s0` — PCI bus location (p3 = bus 3, s0 = slot 0)
- `enx` — fallback to MAC address if nothing else matches

!!! warning
    If you don't know what the values will be (disk name, NIC names), boot the boxes with a [RHEL ISO Boot iso](https://developers.redhat.com/products/rhel/download) and find out. Don't guess. You don't even need to install, just start the installer and you can see the information. 

### BMC / Out-of-Band Management

Each bare metal server must have out-of-band management access for remote operations:

| Management Type | Protocol | Purpose                       |
| --------------- | -------- | ----------------------------- |
| IPMI            | IPMI     | Power control, virtual media  |
| Redfish         | HTTPS    | Modern BMC API, virtual media |
| iLO / iDRAC     | HTTPS    | Vendor-specific BMC           |

Virtual media (mounting the discovery ISO remotely) is the recommended method for booting nodes during installation.

#### Testing BMC Access

Verify Redfish API connectivity from the installation host to each BMC before starting the install. This confirms credentials, network access, and helps you identify the correct system ID for each server.

List available systems:

```bash
curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/ -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
```

The BMC address format varies by vendor:

| Vendor     | Address Format                                                              |
| ---------- | --------------------------------------------------------------------------- |
| HPE iLO    | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/1`                  |
| Dell iDRAC | `idrac-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1`    |
| Cisco CIMC | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/{{ system_id }}`    |

!!! warning "Dell iDRAC Protocol"
    The `redfish-virtualmedia://` protocol is designed for HPE iLO and does not work on Dell iDRAC. Always use `idrac-virtualmedia://` for Dell servers.

Verify power state and virtual media by vendor:

=== "Dell iDRAC"

    ```bash
    curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1 -u {{ bmc_username }}:{{ bmc_password }} | jq '.PowerState'
    curl -sk https://{{ bmc_ip }}/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
    ```

=== "HPE iLO"

    ```bash
    curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/1 -u {{ bmc_username }}:{{ bmc_password }} | jq '.PowerState'
    curl -sk https://{{ bmc_ip }}/redfish/v1/Managers/1/VirtualMedia -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
    ```

!!! tip "Discover System IDs"
    List available systems first to find the correct system path for your hardware:

    ```bash
    curl -sk https://{{ bmc_ip }}/redfish/v1/Systems -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
    ```

!!! tip
    If any of these commands fail, check that the BMC IP is reachable from the installation host, the credentials are correct, and HTTPS (port 443) is open between the installation host and the BMC network.

### BIOS/Firmware Settings

Ensure the following on all nodes:

- Boot mode set to UEFI
- Secure Boot supported (optional but recommended)
- Boot order set to local disk (the ISO is mounted via virtual media)
- Before mounting the discovery/agent ISO, clear stale OS UEFI boot table entries (leftover entries from previous installations can cause the node to boot the wrong target). Use a one-time virtual-media/CD boot override for the first boot, then set boot order back to local disk after installation completes.
- Hardware clock set to UTC

### Disable POST Memory Test

Servers with large amounts of RAM (512 GB+) can spend 5–10 minutes running full memory diagnostics during every boot. For a POC where clusters are built and torn down frequently, disabling the POST memory test cuts each reboot cycle significantly with no reliability trade-off.

For a detailed runbook covering Dell, HPE, Cisco, and Lenovo — including when to disable, automation with Ansible, and a handback checklist — see [Faster Bare-Metal Boots in OpenShift PoCs](https://thomasphall.github.io/posts/poc-faster-bare-metal-boot-disable-memory-check/).

#### Dell iDRAC

```bash
racadm set BIOS.MemSettings.MemTest Disabled
racadm jobqueue create BIOS.Setup.1-1
racadm serveraction powercycle
```

Redfish equivalent:

```bash
curl -sk -X PATCH \
  https://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1/Bios/Settings \
  -u {{ bmc_username }}:{{ bmc_password }} \
  -H "Content-Type: application/json" \
  -d '{"Attributes":{"MemTest":"Disabled"}}'
```

#### HPE iLO

Enable Memory Fast Training (skips full initialization after first good boot):

```bash
ilorest set MemFastTraining=Enabled --selector=Bios.
ilorest commit
```

Redfish equivalent:

```bash
curl -sk -X PATCH \
  https://{{ bmc_ip }}/redfish/v1/Systems/1/Bios/Settings \
  -u {{ bmc_username }}:{{ bmc_password }} \
  -H "Content-Type: application/json" \
  -d '{"Attributes":{"MemFastTraining":"Enabled"}}'
```

#### Cisco CIMC

Redfish:

```bash
curl -sk -X PATCH \
  https://{{ bmc_ip }}/redfish/v1/Systems/{{ system_id }}/Bios/Settings \
  -u {{ bmc_username }}:{{ bmc_password }} \
  -H "Content-Type: application/json" \
  -d '{"Attributes":{"<memory-test-attribute>":"Disabled"}}'
```

!!! note
    The exact attribute name varies between C-series generations and firmware versions (often `POSTErrorPause` or a toggle under the memory RAS group). Query `/redfish/v1/Systems/{{ system_id }}/Bios` to find the correct attribute name for your hardware.

#### Declarative via HostFirmwareSettings (Metal³ / Ironic)

If the bare metal nodes are managed by Metal³/Ironic (BareMetalHost operator), skip per-BMC scripting and drive it declaratively through `HostFirmwareSettings`:

!!! warning "Assisted/Agent-Based Installs"
    Nodes provisioned via the Assisted Installer or Agent-based method are typically registered as `ExternallyProvisioned` in Metal³. In this state, `HostFirmwareSettings` edits will **not** be applied because Ironic does not manage the firmware lifecycle for externally provisioned hosts. Apply BIOS changes via `racadm` (Dell) or Redfish API **before** imaging the nodes.

!!! info "Reading Allowed Firmware Values"
    For IPI-provisioned hosts, read allowed attribute values from the `FirmwareSchema` CR referenced by `status.schema.name` and `status.schema.namespace` on the `HostFirmwareSettings` resource — not from `status.schema` itself, which only contains the reference.

```yaml
apiVersion: metal3.io/v1alpha1
kind: HostFirmwareSettings
metadata:
  name: {{ baremetalhost_name }}
  namespace: openshift-machine-api
spec:
  settings:
    MemTest: "Disabled"          # Dell
    # MemFastTraining: "Enabled" # HPE
```

Look up the correct attribute names from the node's firmware schema:

```bash
oc get hostfirmwaresettings {{ baremetalhost_name }} -n openshift-machine-api -o yaml
```

The `status.settings` field shows current values and `status.schema` shows allowed values per attribute. This keeps the change in your GitOps repo and reapplies on reprovision.

### Schedulable Control Plane

There is an ability to run the control plane nodes as schedulable, making them effectively worker nodes as well. This is discouraged unless required by the environment constraints, such as testing to run edge systems.
