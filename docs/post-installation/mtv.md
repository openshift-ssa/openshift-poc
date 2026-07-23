# Migration Toolkit for Virtualization

[Migration Toolkit for Virtualization Documentation](https://docs.redhat.com/en/documentation/migration_toolkit_for_virtualization/latest)

The Migration Toolkit for Virtualization (MTV) enables migration of virtual machines from VMware vSphere, Red Hat Virtualization, OpenStack, or other OpenShift Virtualization clusters into your OpenShift Virtualization environment. It provides a web-based wizard for planning and executing migrations at scale.

## Prerequisites

- OpenShift Virtualization operator installed and configured
- Storage configured with a default StorageClass (RWX recommended)
- Network connectivity between the OpenShift cluster and the source hypervisor (vCenter, RHV Manager, etc.)
- Cluster administrator privileges
- If performing OVA conversion, an NFS share is required

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Migration Toolkit for Virtualization" -> click the tile
2. Click Install
3. Leave all the defaults (installs to `openshift-mtv` namespace) and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "Migration Toolkit for Virtualization Operator"
6. Click on the "ForkliftController" tab and then click "Create ForkliftController"
7. Leave all the defaults and click Create
8. Wait for all MTV pods to reach Running state

## Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-mtv
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: migration
  namespace: openshift-mtv
spec:
  targetNamespaces:
    - openshift-mtv
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: mtv-operator
  namespace: openshift-mtv
spec:
  channel: release-v2.11
  installPlanApproval: Automatic
  name: mtv-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

```bash
oc apply -f mtv-operator.yaml
```

Wait for the operator:

```bash
oc get csv -n openshift-mtv -w
```

The `PHASE` should show `Succeeded`.

## Create the ForkliftController

```yaml
apiVersion: forklift.konveyor.io/v1beta1
kind: ForkliftController
metadata:
  name: forklift-controller
  namespace: openshift-mtv
spec:
  olm_managed: true
  feature_ui_plugin: "true"
  feature_validation: "true"
  feature_volume_populator: "true"
```

```bash
oc apply -f forklift-controller.yaml
```

## Verify

```bash
oc get pods -n openshift-mtv
```

All pods should be Running. The Migration menu item will appear in the left navigation of the WebUI.

## Add a Source Provider

A source provider is the hypervisor environment you are migrating VMs from. A default `host` provider (representing the local OpenShift Virtualization cluster) is created automatically.

### Add vSphere Provider via WebUI

1. Go to Migration -> Providers for virtualization
2. Click "Create Provider"
3. Select "vSphere"
4. Fill in the details:
    - Name: a friendly name for this provider
    - vCenter host or ESXi host: the FQDN or IP of the vCenter server
    - Username: a vCenter user with at least read access to the VMs
    - Password: the vCenter password
    - SHA-1 fingerprint of the vCenter certificate (or skip verification for POC)
5. Click Create

### Add vSphere Provider via YAML

1. Create the vCenter credentials secret:

  ```bash
  oc create secret generic vsphere-credentials \
    --from-literal=user={{ vcenter_username }} \
    --from-literal=password={{ vcenter_password }} \
    -n openshift-mtv
  ```

2. Create the Provider resource:

  ```yaml
  apiVersion: forklift.konveyor.io/v1beta1
  kind: Provider
  metadata:
    name: vsphere-source
    namespace: openshift-mtv
  spec:
    type: vsphere
    url: "https://{{ vcenter_fqdn }}/sdk"
    secret:
      name: vsphere-credentials
      namespace: openshift-mtv
  ```

  ```bash
  oc apply -f vsphere-provider.yaml
  ```

3. Verify the provider is ready:

  ```bash
  oc get provider -n openshift-mtv
  ```

  The `READY` column should show `True`.

## Set Up the VMware Virtual Disk Development Kit (VDDK)

It is strongly recommended that MTV be used with the VMware Virtual Disk Development Kit (VDDK) SDK when transferring virtual disks from VMware vSphere. Using MTV without VDDK is not recommended and could result in significantly lower migration speeds. You must use a VDDK image if the source VMs are backed by VMware vSAN.

You will download the VDDK, build a container image, and push it to your image registry.

!!! warning "VMware License"
    Storing the VDDK image in a public registry might violate the VMware license terms.

### Prerequisites

- OpenShift image registry (internal or external accessible from OpenShift Virtualization)
- `podman` installed
- You are working on a file system that preserves symbolic links (symlinks) — the VDDK package contains symlinks

### Create a Working Directory

```bash
mkdir /tmp/vddk && cd /tmp/vddk
```

### Download VDDK from VMware

1. Open the [VMware VDDK 8 download page](https://developer.broadcom.com/sdks/vmware-virtual-disk-development-kit-vddk/8.0)
2. Download version **8.0.1** (Red Hat's current documented version)

    !!! note "OpenShift Virtualization 4.12"
        If you are running OpenShift Virtualization 4.12, download VDDK version **7.0.3.2** from the [VMware VDDK version 7 download page](https://developer.broadcom.com/sdks/vmware-virtual-disk-development-kit-vddk/7.0) instead.

3. Save `VMware-vix-disklib-<version>.x86_64.tar.gz` into `/tmp/vddk`

### Extract the VDDK Archive

```bash
tar -xzf VMware-vix-disklib-*.x86_64.tar.gz
```

Verify the extracted directory:

```bash
ls   # should show vmware-vix-disklib-distrib/
```

### Create the VDDK Container Image

Create a `Dockerfile`:

```bash
cat > Dockerfile <<'EOF'
FROM registry.access.redhat.com/ubi9/ubi-minimal
USER 1001
COPY vmware-vix-disklib-distrib /vmware-vix-disklib-distrib
RUN mkdir -p /opt
ENTRYPOINT ["cp", "-r", "/vmware-vix-disklib-distrib", "/opt"]
EOF
```

### Push to the OpenShift Internal Registry

Enable the default registry route if it is not already exposed:

```bash
oc patch configs.imageregistry.operator.openshift.io/cluster --type merge \
  -p '{"spec":{"defaultRoute":true}}'
```

Get the registry hostname:

```bash
REGISTRY=$(oc get route default-route -n openshift-image-registry \
  -o jsonpath='{.spec.host}')
```

Create the target namespace (if it does not already exist):

```bash
oc new-project openshift-mtv 2>/dev/null || true
```

Authenticate podman to the internal registry:

```bash
podman login -u $(oc whoami) -p $(oc whoami -t) $REGISTRY --tls-verify=false
```

Build and push the VDDK image:

```bash
podman build . -t $REGISTRY/openshift-mtv/vddk:latest
podman push $REGISTRY/openshift-mtv/vddk:latest --tls-verify=false
```

Ensure the image is accessible to your OpenShift Virtualization environment. If you are using an external registry, verify that OpenShift can pull from it.

### Configure MTV to Use the VDDK Image

Update the `ForkliftController` to reference the VDDK init image:

```bash
oc patch forkliftcontroller forklift-controller -n openshift-mtv --type merge \
  -p "{\"spec\":{\"controller_vddk_init_image\":\"$REGISTRY/openshift-mtv/vddk:latest\"}}"
```

Verify the patch:

```bash
oc get forkliftcontroller forklift-controller -n openshift-mtv \
  -o jsonpath='{.spec.controller_vddk_init_image}'
```

## Create a Migration Plan

Once providers are configured, create a migration plan using the WebUI wizard:

1. Go to Migration -> Plans for virtualization
2. Click "Create Plan"
3. Select the source provider (e.g., `vsphere-source`)
4. Select the target provider (`host` — the local OpenShift Virtualization cluster)
5. Select the VMs to migrate
6. Configure network mappings (source network -> target network)
7. Configure storage mappings (source datastore -> target StorageClass)
8. Review and click "Create"

### Migration Types

| Type | Description                                                                  |
| ---- | ---------------------------------------------------------------------------- |
| Cold | VM is powered off before migration. Simplest and most reliable.              |
| Warm | Pre-copies data while VM is running, then does a final cutover (less downtime) |

!!! tip "Start with Cold Migrations"
    For POC environments, use cold migrations. They are simpler to troubleshoot and don't require VMware Changed Block Tracking (CBT) or VDDK configuration.

## Run the Migration

1. Go to Migration -> Plans for virtualization
2. Click the "Start" button on your plan
3. Monitor progress in the plan details view

Each VM will go through: `Pending` -> `Disk Transfer` -> `Convert` -> `Succeeded`

## Post-Migration

After migration completes:

- Verify the VM is running in Virtualization -> VirtualMachines
- Check that networking and storage are attached correctly
- Remove VMware Tools from the guest OS (if applicable)
- Install the QEMU guest agent for better integration with OpenShift Virtualization
