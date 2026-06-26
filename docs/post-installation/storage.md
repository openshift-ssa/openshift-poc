# Storage

After the cluster is running, install your vendor's CSI driver to provide persistent storage for workloads.

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
