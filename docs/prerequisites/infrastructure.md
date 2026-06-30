# Infrastructure

All nodes are bare metal servers in an on-premise environment. Provision compute resources that meet or exceed the minimum requirements for each node type.

!!! info "OpenShift Terminology"
    A quick note on terminology. In OpenShift, the same server can be described at three layers:  
    
    - **Host** (`BareMetalHost`, managed by the Bare Metal Operator) is the physical box and its BMC, answering how to power and provision the hardware  
    - **Machine** (`Machine`, managed by the Machine API and grouped into a `MachineSet`) is the infrastructure instance that backs a node and is the unit you scale which can be a physical box or a virtual machine  
    - **Node** (`Node`) is the Kubernetes-level member that runs a kubelet and that the scheduler places pods onto. 

## Required Hardware

Consider these minimum values — the more the better. 

### Standalone Cluster

| Host Type     | Count | CPU | Memory | Install Disk | Secondary Disk |
| ------------- | ----- | --- | ------ | ------------ | -------------- |
| Installation  | 1     | 4   | 16 GB  | 60 GB        | ---            |
| Control Plane | 3     | 16  | 32 GB  | 120 GB       | ---            |
| Worker        | 3     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |

### Fleet Management (Hub + Spoke)

| Host Type             | Count | CPU | Memory | Install Disk | Secondary Disk |
| -------------         | ----- | --- | ------ | ------------ | -------------- |
| Installation          | 1     | 4   | 16 GB  | 60 GB        | ---            |
| Hub (SNO)             | 1     | 16  | 64 GB  | 120 GB       | 1 TB           |
| Spoke Control Plane   | 3     | 16  | 32 GB  | 120 GB       | ---            |
| Spoke Worker          | 3     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |

!!! note "Machine Types"
    The installation and hub machine can be either a virtual machine or bare metal host. They just need network access to the other hosts. 

!!! note "CPU Architecture" 
    For the POC, prefer the same vendor and generation CPU architectures across all machines. 

!!! warning "etcd Disk Requirements"
    For the install disk, run etcd on a block device that can write at least 50 IOPS of 8KB sequentially, including fdatasync, in under 10ms.

## Network Interface Requirements

Only a single NIC is required for OpenShift. To perform more advanced networking, 4 x 10 GbE is recommended for bond0/bond1.

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
    <td>10.0.0.2</td>
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
    <td>10.0.0.3</td>
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
    <td>A0:B1:C2:D3:E4:E1</td>
    <td>bond0</td>
    <td>10.0.0.4</td>
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
    <td>10.0.0.5</td>
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
    <td>10.0.0.6</td>
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
    <td>10.0.0.7</td>
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
    <td>10.0.0.8</td>
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
    <td>10.0.0.9</td>
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
| Dell iDRAC | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1`  |
| Cisco CIMC | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/{{ system_id }}`    |

Verify power state:

```bash
curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/1 -u {{ bmc_username }}:{{ bmc_password }} | jq '.PowerState'
```

Verify virtual media is available:

```bash
curl -sk https://{{ bmc_ip }}/redfish/v1/Managers/1/VirtualMedia -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
```

!!! tip
    If any of these commands fail, check that the BMC IP is reachable from the installation host, the credentials are correct, and HTTPS (port 443) is open between the installation host and the BMC network.

### BIOS/Firmware Settings

Ensure the following on all nodes:

- Boot mode set to UEFI
- Secure Boot supported (optional but recommended)
- Boot order set to local disk (the ISO is mounted via virtual media)
- Hardware clock set to UTC

### Schedulable Control Plane

There is an ability to run the control plane nodes as schedulable, making them effectively worker nodes as well. This is discouraged unless required by the environment constraints, such as testing to run edge systems.
