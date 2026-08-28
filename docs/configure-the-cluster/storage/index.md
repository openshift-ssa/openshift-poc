# Storage

After the cluster is running, install your vendor's CSI driver to provide persistent storage for workloads.

!!! warning "Storage Vendor Inclusion"
    It is **highly recommended** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. While the Red Hat sales engineers are multidisciplinary and bring tons of expertise, it is impossible for them to keep up with the nuances and best practices of every single storage provider in the market.

### OpenShift Virtualization Storage Requirements

If you are planning on running virtual machines using OpenShift Virtualization, the live migration feature requires shared storage with ReadWriteMany (RWX) access mode. A VM's disk PVCs must be RWX for it to migrate — during migration the VM runs briefly on both source and destination nodes, so the disk volume has to be mountable on two nodes at once, which RWO can't do.

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

If you are targeting ODF as your storage provider, see the dedicated [OpenShift Data Foundation](./odf.md) installation guide.

## NetApp Trident

If you are using NetApp ONTAP storage, see the [NetApp Trident](./netapp-trident.md) installation guide. Trident supports NFS (FlexVol and FlexGroup), iSCSI, NVMe/TCP, and Fibre Channel protocols.

[NetApp OpenShift virtualization solutions](https://docs.netapp.com/us-en/netapp-solutions-virtualization/openshift/index.html)

## Dell Unity XT

If you are using Dell Unity XT over iSCSI, see the [Dell Unity XT](./dell/dell-unity.md) installation guide.

[Dell Technologies Container Storage Modules Administrator Guide](https://www.dell.com/support/manuals/en-us/container-storage-modules/csm_installation)



## VMware vSphere CSI

If the cluster is VMs on vSphere with `platform: vsphere`, see the [VMware vSphere CSI](./vsphere-csi.md) guide.

## Multipathing

For FC and iSCSI block storage, multipathing must be configured at the RHCOS host layer via MachineConfig. If you are running multiple storage arrays or need to understand the vendor-specific tuning parameters, see the dedicated [Multipathing](./multipathing.md) guide.
