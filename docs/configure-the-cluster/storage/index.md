# Storage

After the cluster is running, install your vendor's CSI driver to provide persistent storage for workloads.

!!! warning "Storage Vendor Inclusion"
    It is **highly recommended** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. While the Red Hat sales engineers are multidisciplinary and bring tons of expertise, it is impossible for them to keep up with the nuances and best practices of every single storage provider in the market.

## OpenShift Virtualization Storage Requirements

If you are planning on running virtual machines using OpenShift Virtualization, the live migration feature requires shared storage with ReadWriteMany (RWX) access mode. A VM's disk PVCs must be RWX for it to migrate — during migration the VM runs briefly on both source and destination nodes, so the disk volume has to be mountable on two nodes at once, which RWO can't do.

## Access Modes

Confirm with your storage vendor which access modes are supported:

| Access Mode | Description                      | Common Use                        |
| ----------- | -------------------------------- | --------------------------------- |
| RWO         | Read-Write Once (single node)    | Databases, monitoring             |
| RWX         | Read-Write Many (multiple nodes) | Registry, shared application data |
| ROX         | Read-Only Many (multiple nodes)  | Static content, shared configs    |

## Vendor Compatibility

Verify your storage vendor and driver version are listed in the [Red Hat Ecosystem Catalog](https://catalog.redhat.com) for your target OpenShift version. See the left navigation for vendor-specific installation guides.

## Storage Network

Storage traffic should run on a dedicated VLAN with jumbo frames (MTU 9000) for optimal performance. This applies to iSCSI, NVMe/TCP, and ODF inter-node replication — any protocol where storage I/O traverses Ethernet. FC traffic runs on its own fabric and is not affected by Ethernet MTU settings.

Every hop between the cluster nodes and the storage array must support the same MTU — switches, NICs, bond/VLAN interfaces, and the storage array ports. A single hop at MTU 1500 in the path will cause fragmentation or silent drops.

### Checklist

- [ ] Dedicated storage VLAN configured on switches
- [ ] All switch ports on the storage VLAN set to MTU 9000
- [ ] Storage array network ports configured for MTU 9000
- [ ] Cluster node NICs (or bond/VLAN interfaces used for storage) configured for MTU 9000 via [NMState NNCP](../networking.md#storage-network-bond-with-jumbo-frames-mtu-9000)

### Verify End-to-End MTU

After the cluster is installed and NMState NNCPs are applied, verify jumbo frames work end-to-end from a worker node to the storage array:

```bash
W=$(oc get nodes -l node-role.kubernetes.io/worker -o name | head -1)
oc debug $W -- chroot /host ping -M do -s 8972 -c 3 <storage-array-ip>
```

A successful response confirms MTU 9000 is working. If the ping fails with `Message too long`, there is an MTU mismatch somewhere in the path.

!!! warning
    If any single hop does not support jumbo frames, packets will be fragmented or dropped, causing severe performance degradation or connectivity failures. Common culprits are upstream router interfaces, inter-switch links, and VLAN trunk ports that were not explicitly configured for the higher MTU.

## Multipathing

For FC and iSCSI block storage, multipathing must be configured at the RHCOS host layer via MachineConfig. See the [Multipathing](./multipathing.md) guide for the framework, configuration structure, and delivery mechanism.

## CSI Driver Installation

Most vendors provide an Operator available through the Software Catalog or a Helm chart. The general process is:

1. Install the CSI driver Operator (or deploy via manifests provided by the vendor)
2. Configure the driver with storage array credentials and connectivity details
3. Create a StorageClass that references the CSI driver
4. Set the StorageClass as the cluster default:

  ```bash
  oc patch storageclass {{ storage_class_name }} -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
  ```

## Verify

```bash
oc get csidrivers
oc get storageclass
```
