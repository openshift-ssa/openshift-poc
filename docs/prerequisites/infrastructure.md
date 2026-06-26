# Infrastructure

All nodes are bare metal servers in an on-premise environment. Provision compute resources that meet or exceed the minimum requirements for each node type.

## Required Hardware

Consider these minimum values — the more the better. Disks must be SSD/NVMe.

### Standalone Cluster

| Host          | Count | CPU | Memory | Install Disk | Secondary Disk |
| ------------- | ----- | --- | ------ | ------------ | -------------- |
| Installation  | 1     | 4   | 16 GB  | 60 GB        | ---            |
| Control Plane | 3     | 16  | 32 GB  | 120 GB       | ---            |
| Worker        | 3     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |

### Fleet Management (Hub + Spoke)

| Host          | Count | CPU | Memory | Install Disk | Secondary Disk |
| ------------- | ----- | --- | ------ | ------------ | -------------- |
| Installation  | 1     | 4   | 16 GB  | 60 GB        | ---            |
| Hub (SNO)     | 1     | 16  | 64 GB  | 120 GB       | 1 TB           |
| Spoke CP      | 3     | 16  | 32 GB  | 120 GB       | ---            |
| Spoke Worker  | 3     | 16  | 64 GB  | 120 GB       | 1 TB (opt)     |

The installation host and hub host can be either a virtual machine or a bare metal host.

!!! note
    Prefer the same vendor and generation CPU architectures across all machines. Worker node sizing dictates workload max sizing.

!!! warning "etcd Disk Requirements"
    Run etcd on a block device that can write at least 50 IOPS of 8KB sequentially, including fdatasync, in under 10ms.

## Network Interface Requirements

1 x 10 GbE is required for the hosts. To perform more advanced networking, 4 x 10 GbE is recommended for bond0/bond1.

## Machine Information

Collect the interface names, MAC addresses for ALL NICs, and the install disk location on the machines. Below is an example table of values needed.

| Hostname   | Interface | MAC Address       | Bond  | IP   | Disk Hint | BMC IP    |
| ---------- | --------- | ----------------- | ----- | --------- | --------- | --------- |
| installation | eno1    | A0:B1:C2:D3:E4:E0 | ---  | 10.0.0.2  | /dev/sda  | ---       |
| hub        | eno1      | A0:B1:C2:D3:E4:E1 | ---  | 10.0.0.3  | /dev/sda  | 10.2.0.3  |
| spoke-cp01 | eno1      | A0:B1:C2:D3:E4:E1 | bond0 | 10.0.0.4 | /dev/sda  | 10.2.0.4 |
|            | eno2      | A0:B1:C2:D3:E4:E2 | bond0 |           |           |           |
|            | eno3      | A0:B1:C2:D3:E4:E3 | bond1 |           |           |           |
|            | eno4      | A0:B1:C2:D3:E4:E4 | bond1 |           |           |           |
| spoke-cp02 | eno1      | A0:B1:C2:D3:E4:E5 | bond0 | 10.0.0.5 | /dev/sda  | 10.2.0.5 |
|            | eno2      | A0:B1:C2:D3:E4:E6 | bond0 |           |           |           |
|            | eno3      | A0:B1:C2:D3:E4:E7 | bond1 |           |           |           |
|            | eno4      | A0:B1:C2:D3:E4:E8 | bond1 |           |           |           |
| spoke-cp03 | eno1      | A0:B1:C2:D3:E4:E9 | bond0 | 10.0.0.6 | /dev/sda  | 10.2.0.6 |
|            | eno2      | A0:B1:C2:D3:E4:EA | bond0 |           |           |           |
|            | eno3      | A0:B1:C2:D3:E4:EB | bond1 |           |           |           |
|            | eno4      | A0:B1:C2:D3:E4:EC | bond1 |           |           |           |
| spoke-w01  | eno1      | A0:B1:C2:D3:E4:F1 | bond0 | 10.0.0.7 | /dev/sda  | 10.2.0.7 |
|            | eno2      | A0:B1:C2:D3:E4:F2 | bond0 |           |           |           |
|            | eno3      | A0:B1:C2:D3:E4:F3 | bond1 |           |           |           |
|            | eno4      | A0:B1:C2:D3:E4:F4 | bond1 |           |           |           |
| spoke-w02  | eno1      | A0:B1:C2:D3:E4:F5 | bond0 | 10.0.0.8 | /dev/sda  | 10.2.0.8 |
|            | eno2      | A0:B1:C2:D3:E4:F6 | bond0 |           |           |           |
|            | eno3      | A0:B1:C2:D3:E4:F7 | bond1 |           |           |           |
|            | eno4      | A0:B1:C2:D3:E4:F8 | bond1 |           |           |           |
| spoke-w03  | eno1      | A0:B1:C2:D3:E4:F9 | bond0 | 10.0.0.9 | /dev/sda  | 10.2.0.9 |
|            | eno2      | A0:B1:C2:D3:E4:FA | bond0 |           |           |           |
|            | eno3      | A0:B1:C2:D3:E4:FB | bond1 |           |           |           |
|            | eno4      | A0:B1:C2:D3:E4:FC | bond1 |           |           |           |

---

## Details

### NIC Naming

On modern RHEL (RHEL CoreOS included), NICs use predictable network interface names generated at boot based on hardware topology and firmware information:

- `eno1`, `eno2` — onboard NICs (from BIOS/firmware)
- `ens1f0`, `ens1f1` — PCI Express slots ("s" = slot, "f" = function)
- `enp3s0` — PCI bus location (p3 = bus 3, s0 = slot 0)
- `enx` — fallback to MAC address if nothing else matches

!!! warning
    If you don't know what the values will be (disk name, NIC names), boot the boxes with a [RHEL ISO](https://developers.redhat.com/products/rhel/download) and find out. Don't guess.

### BMC / Out-of-Band Management

Each bare metal server must have out-of-band management access for remote operations:

| Management Type | Protocol | Purpose                      |
| --------------- | -------- | ---------------------------- |
| IPMI            | IPMI     | Power control, virtual media |
| Redfish         | HTTPS    | Modern BMC API, virtual media |
| iLO / iDRAC     | HTTPS    | Vendor-specific BMC          |

Virtual media (mounting the discovery ISO remotely) is the recommended method for booting nodes during installation.

### BIOS/Firmware Settings

Ensure the following on all nodes:

- Boot mode set to UEFI
- Secure Boot supported (optional but recommended)
- Boot order set to local disk (the ISO is mounted via virtual media)
- Hardware clock set to UTC

### Schedulable Control Plane

There is an ability to run the control plane nodes as schedulable, making them effectively worker nodes as well. This is discouraged unless required by the environment constraints, such as testing to run edge systems.
