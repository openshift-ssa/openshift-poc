# OpenShift Virtualization

[Red Hat OpenShift Virtualization Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_virtualization/latest)

!!! warning "Workload Availability Required for Live Migration Testing"
    If you plan to test any scenarios related to node loss and live migrations, you **must** install and configure [Workload Availability](../workload-availability/workload-availability.md) prior to installing the OpenShift Virtualization Operator. The Descheduler and Node Health Check operators are what trigger live migrations when nodes become unhealthy.

## Prerequisites

- Storage configured with a default virtualization storage class
- Set annotation `storageclass.kubevirt.io/is-default-virt-class` to `true` on the storage class
- RWX access mode required for live migration
- [NMState Operator](../required/nmstate.md) installed
- Optional: [underlay / CUDN networks](../optional/networking.md) for VM IP persistence and a [dedicated live-migration network](../optional/networking.md). Needed for failover IP-sameness tests; not required to install Virtualization.

!!! note "Planning VM Migrations from VMware?"
    If you plan to migrate VMs from VMware vSphere using the [Migration Toolkit for Virtualization](./mtv.md), you must obtain the VDDK image from Broadcom ahead of time. Broadcom has restricted access and requires a support ticket. See [Obtaining the VDDK](./mtv.md#obtaining-the-vddk) for details.

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
      routes:
        - to: default
          via: 10.37.0.1
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

If running the Kube Descheduler Operator alongside OpenShift Virtualization, see the [Workload Availability — Kube Descheduler](../workload-availability/workload-availability.md#kube-descheduler-operator) section for profile selection and configuration. The recommended profile for mixed clusters with VMs is `KubeVirtRelieveAndMigrate`.
