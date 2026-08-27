# Migration Toolkit for Virtualization

[Migration Toolkit for Virtualization Documentation](https://docs.redhat.com/en/documentation/migration_toolkit_for_virtualization/latest)

The Migration Toolkit for Virtualization (MTV) enables migration of virtual machines from VMware vSphere, Red Hat Virtualization, OpenStack, or other OpenShift Virtualization clusters into your OpenShift Virtualization environment. It provides a web-based wizard for planning and executing migrations at scale.

## Prerequisites

- [OpenShift Virtualization](virtualization.md) operator installed and configured
- [Storage](storage/index.md) configured with a default StorageClass (RWX recommended)
- Network connectivity between the OpenShift cluster and the source hypervisor (vCenter, RHV Manager, etc.)
- Cluster administrator privileges
- If performing OVA conversion, an NFS share is required
- VMware Virtual Disk Development Kit (VDDK) image — see [Obtaining the VDDK](#obtaining-the-vddk) below

## Obtaining the VDDK

!!! warning "Action Required Before Migration"
    Broadcom has restricted access to the VMware Virtual Disk Development Kit (VDDK). If you plan to migrate VMs from VMware vSphere to OpenShift Virtualization, you **must** open a support ticket with Broadcom to request access to the VDDK download. This can take several business days, so initiate the request early in your POC planning.

To obtain the VDDK:

1. Log in to the [Broadcom Support Portal](https://support.broadcom.com)
2. Open a support ticket requesting the **VMware Virtual Disk Development Kit (VDDK)** for your licensed vSphere version
3. Broadcom support will provide the VDDK archive directly — it is no longer available for self-service download from the developer portal
4. Match the VDDK version to your source vSphere version (e.g., VDDK 8.0.x for vSphere 8.0)

Without the VDDK, migrations fall back to a slower transfer method (`virt-v2v`). The VDDK is strongly recommended for all VMware migrations.

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
  channel: release-v2.12
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
    - VDDK init image: upload the VDDK archive or paste an existing image URL (see [Upload the VDDK Image via WebUI](#upload-the-vddk-image-via-webui))
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

## vSphere Provider Inventory — Why Only a Subset of VMs Appears

The MTV vSphere provider connects to **vCenter**, not to a single cluster. The list of virtual machines it shows is whatever the service account is allowed to enumerate through vCenter's VM folder tree. That is not the same as "VMs running on this cluster," and it is not the same as what the vSphere Client shows under **Hosts and Clusters**.

Typical observed behavior:

| Permission scope                                      | VMs visible in MTV                                                    |
| ----------------------------------------------------- | --------------------------------------------------------------------- |
| Cluster-level Admin                                   | A small subset (e.g. 8), spread across the ESXi hosts in that cluster |
| Datacenter-level Admin (propagate)                    | All VMs in that datacenter, including VMs on other clusters           |
| Cluster + specific VM folders + datastores + networks | Only the intended cluster's VMs, without exposing other clusters      |

This behavior is expected.

### How MTV Discovers VMs

MTV (Forklift) logs into vCenter with the provider credentials and walks inventory via the vSphere SOAP API (`PropertyCollector`). It starts at the vCenter root folder and follows two different trees under the datacenter:

| vCenter tree                      | What MTV uses it for           |
| --------------------------------- | ------------------------------ |
| Hosts and Clusters (`hostFolder`) | Clusters, ESXi hosts           |
| VMs and Templates (`vmFolder`)    | Virtual machines               |
| Storage / Networking folders      | Datastores, networks, switches |

Virtual machines are **not** children of the cluster in vCenter's inventory model. They run on hosts in the cluster, but their inventory location is almost always a VM folder at the datacenter level (for example `Discovered virtual machine` or an application folder).

MTV lists a VM only if it can walk down to that VM through **VMs and Templates** (or a vApp). It does not ask each host "which VMs are on you?"

Therefore:

- **Cluster Admin** is enough to see hosts and a few VMs whose inventory parent is actually under the cluster (resource pool, vApp, or a reachable folder). It is **not** enough to list VMs that live in datacenter VM folders, even if those VMs are running on that cluster's hosts.
- **Datacenter Admin with propagate** unlocks all four trees (VM folders, clusters, datastores, networks) — which is why MTV then shows VMs on other clusters too.

MTV also hides templates and incomplete "ghost" VMs (no UUID and no host). That usually accounts for a few objects, not most of the inventory.

### Why the vSphere Client and MTV Disagree

The vSphere HTML5 Client and MTV do not use the same view:

| Tool                                | Path used                                                                    | Result with cluster-level Admin               |
| ----------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------- |
| vSphere Client (Hosts and Clusters) | VMs shown as related to hosts/cluster — VMs inherit rights from cluster/host | All ~127 VMs can appear                       |
| MTV provider inventory              | Walk of VMs and Templates folders                                            | Only VMs in folders the account can enumerate |

Seeing every VM in the vSphere Client with a service account does **not** mean MTV can inventory them. Confirm by logging in as the same user stored in the MTV provider secret and switching to **VMs and Templates**, not Hosts and Clusters.

### Recommended Permission Layout

Do not grant Admin on the whole datacenter if other clusters must stay hidden. Use a dedicated MTV role with the [documented VMware privileges](https://docs.redhat.com/en/documentation/migration_toolkit_for_virtualization/latest/html/installing_and_using_the_migration_toolkit_for_virtualization/prerequisites#vmware-privileges_mtv) (interaction, provisioning, snapshot, datastore browse/low-level file, session validate, crypto if disks are encrypted).

| vCenter object                                | Permission          | Propagate                                                                               |
| --------------------------------------------- | ------------------- | --------------------------------------------------------------------------------------- |
| vCenter root                                  | Read-only           | No                                                                                      |
| Datacenter                                    | Read-only           | No — lets MTV traverse without inheriting every cluster, folder, datastore, and network |
| Intended cluster                              | MTV role (or Admin) | Yes — covers hosts and compute                                                          |
| VM folder(s) containing the target VMs        | MTV role (or Admin) | Yes — **this grant is what makes VMs appear in MTV**                                    |
| Datastores used by those VMs                  | MTV role (or Admin) | Yes                                                                                     |
| Networks / distributed switches / port groups | MTV role (or Admin) | Yes                                                                                     |

If the VMs are spread across many folders, either grant on each folder or move in-scope VMs into one dedicated folder and grant only there.

!!! warning
    Do not grant rights only on the VM objects. MTV still needs parent folders, datastores, and networks. Red Hat requires rights on the objects a VM **uses**, not only on the VM itself.

After changing permissions, wait for MTV to refresh provider inventory (or reconnect/reconcile the provider) and confirm the VM count.

### How to Verify

1. Log into the vSphere Client as the exact account in the MTV provider secret
2. Open **VMs and Templates** (not Hosts and Clusters)
3. Compare a VM that MTV shows vs. one it does not — the missing VM will typically sit in a datacenter VM folder that has no grant for this account

Optionally check MTV inventory logs for skipped or permission-related objects:

```bash
oc logs -n openshift-mtv deploy/forklift-controller -c inventory \
  | grep -E 'ghost VM|Skipping template|NoPermission|permission'
```

On newer MTV versions, also review the Provider resource for reported missing vSphere privileges:

```bash
oc get provider vsphere-source -n openshift-mtv -o jsonpath='{.status.conditions}' | jq
```

## Set Up the VMware Virtual Disk Development Kit (VDDK)

It is strongly recommended that MTV be used with the VMware Virtual Disk Development Kit (VDDK) SDK when transferring virtual disks from VMware vSphere. Without the VDDK, MTV falls back to the slower `virt-v2v` transfer path, which can result in significantly longer migration times.

Download the VDDK archive from VMware, then either upload it through the MTV WebUI (MTV builds the init image for you) or build and push the container image yourself with `podman`.

!!! warning "VMware License"
    Storing the VDDK image in a public registry might violate the VMware license terms.

### Obtain VDDK from Broadcom

Match the VDDK version to your source vSphere (vCenter/ESXi) version. Broadcom aligns VDDK version numbers with vSphere (for example, use VDDK **8.0.x** with vSphere **8.0**). Prefer the VDDK release that corresponds to your environment's major.minor version so disk-transfer features and compatibility stay aligned.

!!! note
    The VDDK is no longer available for self-service download from the Broadcom developer portal. You must open a support ticket and Broadcom will provide the archive directly. See [Obtaining the VDDK](#obtaining-the-vddk) above.

1. Open a support ticket at the [Broadcom Support Portal](https://support.broadcom.com) requesting VDDK for your vSphere version
2. Broadcom support will provide the `VMware-vix-disklib-<version>.x86_64.tar.gz` archive
3. Save the archive locally (for example, into `/tmp/vddk`)

### Upload the VDDK Image via WebUI

The MTV console can upload the VDDK archive and build the init image when you create or edit a vSphere provider. This is the simplest path for POC environments.

1. Go to Migration -> Providers for virtualization
2. Click **Create Provider** (or open an existing vSphere provider and edit it)
3. Select **vSphere** / **VMware**
4. Fill in the provider details (name, URL, credentials, certificate options)
5. In the **VDDK init image** section, either:
    - **Upload the archive (recommended for POC):**
        1. Click **Browse** next to the VDDK init image archive field
        2. Select your downloaded `VMware-vix-disklib-<version>.x86_64.tar.gz` and click **Select**
        3. Click **Upload**
        4. Wait for the upload to finish — MTV builds the init image and populates the image URL
    - **Use an existing image:** paste the image path (for example, `image-registry.openshift-image-registry.svc:5000/openshift-mtv/vddk:latest`)
6. Click **Create provider** (or save the edit)
7. Wait until the provider status is `Ready` (this can take a few minutes while the image is built)

!!! tip
    Prefer creating the provider in the `openshift-mtv` project so the built VDDK image lands in that namespace. If you migrate VMs into other namespaces, grant those namespaces pull access as described in [Allow Target Namespaces to Pull the VDDK Image](#allow-target-namespaces-to-pull-the-vddk-image).

### Build and Push the VDDK Image via CLI

Use this path when you need to push the VDDK image to a specific registry yourself, or when you want to set a cluster-wide default on the `ForkliftController`.

#### Prerequisites

- OpenShift image registry (internal or external accessible from OpenShift Virtualization)
- `podman` installed
- You are working on a file system that preserves symbolic links (symlinks) — the VDDK package contains symlinks

#### Create a Working Directory

```bash
mkdir /tmp/vddk && cd /tmp/vddk
```

#### Extract the VDDK Archive

```bash
tar -xzf VMware-vix-disklib-*.x86_64.tar.gz
```

Verify the extracted directory:

```bash
ls   # should show vmware-vix-disklib-distrib/
```

#### Create the VDDK Container Image

Create a `Containerfile`:

```bash
cat > Containerfile <<'EOF'
FROM registry.redhat.io/ubi9/ubi-minimal
USER 1001
COPY vmware-vix-disklib-distrib /vmware-vix-disklib-distrib
RUN mkdir -p /opt
ENTRYPOINT ["cp", "-r", "/vmware-vix-disklib-distrib", "/opt"]
EOF
```

#### Push to the OpenShift Internal Registry

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

#### Configure MTV to Use the VDDK Image

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

You can also set the same image URL on a vSphere provider in the WebUI (**VDDK init image** field) instead of patching the controller.

### Allow Target Namespaces to Pull the VDDK Image

MTV runs VDDK init and disk-transfer pods in the **target namespace** of the migration plan (where the VMs are created), not in `openshift-mtv`. When the VDDK image is stored in the OpenShift internal registry under `openshift-mtv`, those pods cannot pull it until service accounts in the target namespace are granted the `system:image-puller` role in the image's namespace.

#### Single target namespace

Grant pull access to all service accounts in the migration target namespace (recommended — MTV/CDI may use more than the `default` service account):

```bash
TARGET_NAMESPACE={{ target_namespace }}

oc adm policy add-role-to-group system:image-puller \
  system:serviceaccounts:${TARGET_NAMESPACE} \
  -n openshift-mtv
```

Or grant pull access to only the `default` service account:

```bash
oc adm policy add-role-to-user system:image-puller \
  system:serviceaccount:${TARGET_NAMESPACE}:default \
  -n openshift-mtv
```

Repeat for each additional target namespace that will receive migrated VMs.

#### All namespaces (POC / lab)

To allow service accounts in every namespace to pull the VDDK image:

```bash
oc adm policy add-role-to-group system:image-puller \
  system:serviceaccounts \
  -n openshift-mtv
```

!!! warning
    Granting `system:image-puller` to `system:serviceaccounts` lets any service account on the cluster pull images from `openshift-mtv`. Prefer the per-namespace form outside of POC environments.

Verify the role bindings:

```bash
oc get rolebinding -n openshift-mtv | grep image-puller
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

| Type | Description                                                                    |
| ---- | ------------------------------------------------------------------------------ |
| Cold | VM is powered off before migration. Simplest and most reliable.                |
| Warm | Pre-copies data while VM is running, then does a final cutover (less downtime) |

!!! tip "Start with Cold Migrations"
    For POC environments, start with cold migrations. They are simpler to troubleshoot and do not require VMware Changed Block Tracking (CBT).

    Migrations can run without VDDK but will use the slower `virt-v2v` fallback. VDDK is strongly recommended for acceptable transfer speeds. See [Obtaining the VDDK](#obtaining-the-vddk).

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
