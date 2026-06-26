# OpenShift Virtualization

!!! warning "Workload Availability Required for Live Migration Testing"
    If you plan to test any scenarios related to node loss and live migrations, you **must** install and configure [Workload Availability](workload-availability.md) prior to installing the OpenShift Virtualization Operator. The Descheduler and Node Health Check operators are what trigger live migrations when nodes become unhealthy.

## Prerequisites

- Storage configured with a default virtualization storage class
- Set annotation `storageclass.kubevirt.io/is-default-virt-class` to `true` on the storage class
- RWX access mode required for live migration
- NMState Operator installed and underlay networks created
- Optional but recommended: dedicated network for live migration

## Install

Install the OpenShift Virtualization Operator via the web console OperatorHub.

## Example cloud-init for Static IP

```yaml
networkData: |
  version: 2
  ethernets:
    eth1:
      dhcp4: no
      addresses:
        - 10.37.0.50/24
      gateway4: 10.37.0.1
      nameservers:
        addresses:
          - 10.3.0.3
          - 9.9.9.9
      dhcp6: no
      accept-ra: false
userData: |
  #cloud-config
  user: cloud-user
  password: Pass123!
  chpasswd:
    expire: false
```

## Descheduler for Live Migration

If running OpenShift Virtualization with the Kube Descheduler Operator, use the `DevPreviewLongLifecycle` profile. This handles long-running VM workloads and triggers live migrations instead of pod deletions when rebalancing.

Each `VirtualMachine` must be annotated to opt in to descheduler evictions:

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: example-vm
spec:
  template:
    metadata:
      annotations:
        descheduler.alpha.kubernetes.io/evict: "true"
```

!!! note
    The VM must have a `LiveMigrate` eviction strategy set for the descheduler to trigger a live migration rather than deleting the pod.
