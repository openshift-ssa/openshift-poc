# Storage

After the cluster is running, install your vendor's CSI driver to provide persistent storage for workloads. 

!!! warning "Storage Vendor Inclusion"
    It is **highly recommend** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. While the Red Hat sales engineers are multidisciplinary and bring tons of expertise, it is impossible for them to keep up with the nuances and best practices of every single storage provider in the market. 

### OpenShift Virtualization Storage Requirements

If you are planning on running virtual machines using OpenShift Virtualization, the live migration feature requires shared storage with ReadWriteMany (RWX) access mode. The cluster must have shared storage with ReadWriteMany (RWX) access mode. A VM's disk PVCs must be RWX for it to migrate — virtual machines must have a persistent volume claim (PVC) with a shared ReadWriteMany (RWX) access mode to be live migrated. The reason is mechanical: during migration the VM runs briefly on both source and destination nodes, so the disk volume has to be mountable on two nodes at once, which RWO can't do.

## CSI Driver Installation

Most vendors provide an Operator available through OperatorHub or a Helm chart. The general process is:

1. Install the CSI driver Operator (or deploy via manifests provided by the vendor)
2. Configure the driver with storage array credentials and connectivity details
3. Create a StorageClass that references the CSI driver
4. Set the StorageClass as the cluster default

```bash
# Verify CSI driver is running
oc get csidrivers

# Verify StorageClass is available
oc get storageclass

# Set default StorageClass
oc patch storageclass {{ storage_class_name }} -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
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

To install Local Storage operator:

1. Go to Ecosystem -> Software Catalog -> Find "Local Storage", click it and then click install. 
2. Keep all the defaults and click Install
3. Go to Ecosystem -> Installed Operators -> Click on "Local Storage"
4. Click on "Local Volume Discovery" tab and click on "Create LocalVolumeDiscovery"
5. Select Disk on selected nodes and select the appropriate nodes with the extra disk for storage
6. Click Finish

To install OpenShift Data Foundation:

1. Go to Ecosystem -> Software Catalog -> Find "OpenShift Data Foundation", click it and then click install. 
2. Keep all the default values and click Install
3. Wait for the Operator to complete installation...
4. Wait for the menu item on the left hand side to show Storage has a new Data Foundation item
5. Go to Storage -> Storage cluster -> click on Configure Data Foundation 
6. Click on Create Storage Cluster
7. Select Create a new StorageClass using local storage devices. Click Next.
8. Select both `Use Ceph RBD as the default StorageClass` and `Set default StorageClass for virtualization`. Click Next.
9. Use "odf-local" for the LocalVolumeSet name, click "Disks on selected nodes" and select the nodes with the disks. Click Next. 
10. On the capacity page, wait for the calculation to happen. Select Balanced or Performance mode. Click Next. 
11. Ignore security selections. Click Next. 
12. Click Finish. 


