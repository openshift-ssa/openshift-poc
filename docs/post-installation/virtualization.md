# OpenShift Virtualization

[Red Hat OpenShift Virtualization Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_virtualization/latest)

!!! warning "Workload Availability Required for Live Migration Testing"
    If you plan to test any scenarios related to node loss and live migrations, you **must** install and configure [Workload Availability](workload-availability.md) prior to installing the OpenShift Virtualization Operator. The Descheduler and Node Health Check operators are what trigger live migrations when nodes become unhealthy.

## Prerequisites

- Storage configured with a default virtualization storage class
- Set annotation `storageclass.kubevirt.io/is-default-virt-class` to `true` on the storage class
- RWX access mode required for live migration
- NMState Operator installed and underlay networks created
- Optional but recommended: dedicated network for live migration

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "OpenShift Virtualization" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "OpenShift Virtualization"
6. Click on the "HyperConverged" tab and then click "Create HyperConverged"
7. Leave all the defaults and click Create
8. Wait for the deployment to complete — the Virtualization menu item will appear in the left navigation

## Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-cnv
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: kubevirt-hyperconverged-group
  namespace: openshift-cnv
spec:
  targetNamespaces:
    - openshift-cnv
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: hco-operatorhub
  namespace: openshift-cnv
spec:
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  name: kubevirt-hyperconverged
  channel: stable
  installPlanApproval: Automatic
```

```bash
oc apply -f virt-operator.yaml
```

Wait for the operator, then create the HyperConverged instance:

```yaml
apiVersion: hco.kubevirt.io/v1beta1
kind: HyperConverged
metadata:
  name: kubevirt-hyperconverged
  namespace: openshift-cnv
spec: {}
```

```bash
oc apply -f hyperconverged.yaml
```

## Verify

```bash
oc get csv -n openshift-cnv
oc get hyperconverged -n openshift-cnv
oc get pods -n openshift-cnv
```

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
