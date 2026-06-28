# Storage

After the cluster is running, install your vendor's CSI driver to provide persistent storage for workloads.

!!! warning "Storage Vendor Inclusion"
    It is **highly recommended** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. While the Red Hat sales engineers are multidisciplinary and bring tons of expertise, it is impossible for them to keep up with the nuances and best practices of every single storage provider in the market.

### OpenShift Virtualization Storage Requirements

If you are planning on running virtual machines using OpenShift Virtualization, the live migration feature requires shared storage with ReadWriteMany (RWX) access mode. A VM's disk PVCs must be RWX for it to migrate — during migration the VM runs briefly on both source and destination nodes, so the disk volume has to be mountable on two nodes at once, which RWO can't do.

## CSI Driver Installation

Most vendors provide an Operator available through OperatorHub or a Helm chart. The general process is:

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

## Access Modes

Confirm with your storage vendor which access modes are supported:

| Access Mode | Description                      | Common Use                        |
| ----------- | -------------------------------- | --------------------------------- |
| RWO         | Read-Write Once (single node)    | Databases, monitoring             |
| RWX         | Read-Write Many (multiple nodes) | Registry, shared application data |
| ROX         | Read-Only Many (multiple nodes)  | Static content, shared configs    |

## Vendor Compatibility

Verify your storage vendor and driver version are listed in the [Red Hat Ecosystem Catalog](https://catalog.redhat.com) for your target OpenShift version.

## OpenShift Data Foundation

If you are looking at OpenShift Platform Plus (OPP) and are targeting ODF to be your storage provider, here's how to install it.

!!! warning "Jumbo Frames Required"
    The storage network must support jumbo frames (MTU 9000) end-to-end for ODF to perform properly. Ensure switches, node NICs, and storage interfaces are all configured for MTU 9000 before deploying ODF. See [Storage Network](../prerequisites/storage.md#storage-network) prerequisites and the [Storage Network NNCP example](networking.md#storage-network-bond-with-jumbo-frames-mtu-9000) for configuration details.

### Install Local Storage Operator

1. Go to Ecosystem -> Software Catalog -> filter for "Local Storage" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "Local Storage"
6. Click on "Local Volume Discovery" tab and click "Create LocalVolumeDiscovery"
7. Select "Disk on selected nodes" and select the appropriate nodes with the extra disk for storage
8. Click Finish

### Install OpenShift Data Foundation

1. Go to Ecosystem -> Software Catalog -> filter for "OpenShift Data Foundation" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Wait for the menu item on the left hand side to show Storage has a new Data Foundation item
6. Go to Storage -> Storage cluster -> click on "Configure Data Foundation"
7. Click on "Create Storage Cluster"
8. Select "Create a new StorageClass using local storage devices"

  -> Click Next

9. Select both `Use Ceph RBD as the default StorageClass` and `Set default StorageClass for virtualization`

  -> Click Next

10. Use "odf-local" for the LocalVolumeSet name, click "Disks on selected nodes" and select the nodes with the disks

  -> Click Next

11. On the capacity page, wait for the calculation to happen. Select Balanced or Performance mode.

  -> Click Next

12. Ignore security selections.

  -> Click Next

13. Click Finish
