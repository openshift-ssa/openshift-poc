# Disconnected Environments

This guide covers installing OpenShift when cluster nodes cannot reach the internet. The process has two parts: set up an internal registry, then configure OpenShift to use it.

Choose one registry approach based on your environment:

| Approach                                        | When to Use                                                  |
| ----------------------------------------------- | ------------------------------------------------------------ |
| [Mirror Registry (oc-mirror)](#mirror-registry) | No system on the cluster network has outbound internet access (fully air-gapped) |
| [Pull-Through Cache](#pull-through-cache)       | Your artifact repository (Artifactory, Nexus) has outbound access but cluster nodes do not |

---

## Mirror Registry

[About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring) | [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)

Use this approach when **no system on the cluster network has outbound internet access** (fully air-gapped). You download content on a connected host, then transfer it to an internal registry.

### Architecture

```
Internet ──> Bastion Host ──> Portable Media ──> Mirror Registry ──> Cluster Nodes
              (oc-mirror)       (optional)        (on-site)           (no internet)
```

In some environments, the bastion host has temporary internet access and direct access to the mirror registry, eliminating the need for portable media.

### Prerequisites

- A bastion host with internet access (temporary or permanent) to download content
- At least 200 GB of available disk for the mirror registry storage
- A Red Hat pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
- The `oc` CLI available on the bastion host

### Install oc-mirror

On the bastion host with internet access:

```bash
OCP_VERSION={{ ocp_version }}
wget "https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable-${OCP_VERSION}/oc-mirror.tar.gz" -P /tmp
sudo tar -xvzf /tmp/oc-mirror.tar.gz -C /usr/local/bin
chmod +x /usr/local/bin/oc-mirror
oc-mirror version
```

### Install the Mirror Registry

You need a container registry on the disconnected network. Options include:

| Registry                                                                                                                                                                                                                                                        | Notes                                          |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift) | Purpose-built, minimal setup, runs with Podman |
| [Red Hat Quay](https://docs.redhat.com/en/documentation/red_hat_quay)                                                                                                                                                                                          | Full-featured, enterprise-grade                |
| JFrog Artifactory                                                                                                                                                                                                                                               | If already available in-house                  |
| Harbor                                                                                                                                                                                                                                                          | Open-source alternative                        |

To install the mirror registry for Red Hat OpenShift:

```bash
wget https://developers.redhat.com/content-gateway/rest/mirror/pub/openshift-v4/clients/mirror-registry/latest/mirror-registry.tar.gz -P /tmp
tar -xvzf /tmp/mirror-registry.tar.gz -C /tmp
sudo /tmp/mirror-registry install --quayHostname {{ mirror_host }} --quayRoot /opt/quay
```

!!! warning
    Ensure `/opt/quay` has at least 200 GB of available disk space. Mirroring an OCP release plus operators can easily exceed 100 GB.

The install command outputs the initial credentials (`init` user and generated password) and generates a self-signed root CA certificate at `/opt/quay/quay-rootCA/rootCA.pem`.

Add the root CA to the bastion host's trust store:

```bash
sudo cp /opt/quay/quay-rootCA/rootCA.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

Verify access:

```bash
podman login {{ mirror_host }}:8443
```

### Configure Authentication

`oc-mirror` needs credentials for both the source (Red Hat) and destination (mirror) registries. Create a combined pull secret:

```bash
cp ~/pull-secret.txt ~/merged-pull-secret.json

podman login {{ mirror_host }}:8443 --authfile ~/merged-pull-secret.json
```

This produces `~/merged-pull-secret.json` containing credentials for both Red Hat registries and your mirror. You will use this file during mirroring and later in `install-config.yaml`.

### Create the ImageSetConfiguration

The `ImageSetConfiguration` defines what content to mirror. Create `imageset-config.yaml`:

```yaml
apiVersion: mirror.openshift.io/v2alpha1
kind: ImageSetConfiguration
mirror:
  platform:
    graph: true
    channels:
      - name: stable-{{ ocp_version }}
        minVersion: {{ ocp_release }}
        maxVersion: {{ ocp_release }}
  operators:
    - catalog: registry.redhat.io/redhat/redhat-operator-index:v{{ ocp_version }}
      packages:
        - name: local-storage-operator
        - name: lvms-operator
        - name: odf-operator
        - name: kubernetes-nmstate-operator
        - name: kubevirt-hyperconverged
        - name: mtv-operator
        - name: oadp-operator
        - name: openshift-gitops-operator
        - name: cluster-logging
        - name: loki-operator
        - name: node-health-check-operator
        - name: self-node-remediation
        - name: cluster-kube-descheduler-operator
        - name: netobserv-operator
        - name: web-terminal
  additionalImages:
    - name: registry.redhat.io/ubi9/ubi:latest
```

!!! warning
    Do not include `storageConfig` in an oc-mirror **v2** `ImageSetConfiguration`. That field is v1-only and will cause the mirror to fail. v2 stores incremental state in the `--workspace` directory.

!!! tip
    Only mirror the operators you plan to install. Mirroring the entire catalog is very large (hundreds of GBs) and takes a long time. You can always re-run `oc-mirror` later to add more.

### Mirror the Content

=== "Direct (bastion has access to both networks)"

    ```bash
    mkdir -p oc-mirror-workspace
    oc-mirror --config imageset-config.yaml \
      --workspace file://oc-mirror-workspace \
      docker://{{ mirror_host }}:8443/openshift \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

=== "Air-Gapped (two-step with portable media)"

    On the internet-connected host, mirror to disk:

    ```bash
    mkdir -p oc-mirror-workspace
    oc-mirror --config imageset-config.yaml \
      --workspace file://oc-mirror-workspace \
      file:///mnt/mirror-data \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

    Transfer `/mnt/mirror-data` and `oc-mirror-workspace` to the disconnected network, then load into the registry:

    ```bash
    oc-mirror --config imageset-config.yaml \
      --workspace file://oc-mirror-workspace \
      --from file:///mnt/mirror-data \
      docker://{{ mirror_host }}:8443/openshift \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

### Output Files

oc-mirror v2 writes cluster resources to `oc-mirror-workspace/working-dir/cluster-resources/`:

| File                  | Purpose                                                                             |
| --------------------- | ----------------------------------------------------------------------------------- |
| `idms-oc-mirror.yaml` | `ImageDigestMirrorSet` — tells the cluster where to find mirrored images            |
| CatalogSource YAML    | Points OLM to the mirrored operator catalog                                        |
| UpdateService YAML    | Cincinnati graph for disconnected upgrades (`platform.graph: true` in this example) |

```bash
ls oc-mirror-workspace/working-dir/cluster-resources/
```

!!! warning
    The `imageDigestSources` values in your `install-config.yaml` must match the repository paths used by `oc-mirror`. Copy the mirror paths from the generated `idms-oc-mirror.yaml` — do not guess them.

### Extract the openshift-install Binary

The `openshift-install` binary is embedded inside the release image. Extract it from the mirrored payload:

```bash
oc adm release extract \
  -a ~/merged-pull-secret.json \
  --command=openshift-install \
  {{ mirror_host }}:8443/openshift/release-images:{{ ocp_release }}-x86_64
```

!!! tip
    You can also download `openshift-install` from the [Red Hat mirror site](https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/) on a connected workstation and transfer it across the airgap. However, `oc adm release extract` guarantees version alignment with the mirrored payload.

### Verify the Mirror

Confirm the release image is accessible:

```bash
oc adm release info \
  --registry-config ~/merged-pull-secret.json \
  {{ mirror_host }}:8443/openshift/release-images:{{ ocp_release }}-x86_64
```

Confirm the operator catalog is accessible:

```bash
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ mirror_host }}:8443/openshift/redhat/redhat-operator-index:v{{ ocp_version }}
```

### Adding More Content Later

Re-run `oc-mirror` with an updated `ImageSetConfiguration` to add new operators or release versions. The tool handles incremental updates:

```bash
oc-mirror --config imageset-config.yaml \
  --workspace file://oc-mirror-workspace \
  docker://{{ mirror_host }}:8443/openshift \
  --authfile ~/merged-pull-secret.json \
  --v2
```

---

## Pull-Through Cache

This section covers configuring an artifact repository (JFrog Artifactory or Sonatype Nexus) as a pull-through cache for container images. Use this approach when **your artifact repository has outbound internet access** but cluster nodes do not.

### Architecture

```
Upstream Registries ──> Artifactory / Nexus ──> Cluster Nodes
  (quay.io, etc.)       (has outbound access)    (no outbound access)
```

A pull-through cache acts as a transparent proxy. When the cluster requests an image, the cache fetches it from the upstream registry, stores a local copy, and serves it. Subsequent pulls are served from the cache. This is simpler than a full mirror because you do not need to pre-stage content.

### Prerequisites

- Artifact repository (Artifactory or Nexus) accessible from all cluster nodes over HTTPS
- Artifact repository has outbound access to:
  - `quay.io` / `cdn.quay.io`
  - `registry.redhat.io`
  - `registry.access.redhat.com`
  - `registry.connect.redhat.com`
- A Red Hat pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
- Credentials for the artifact repository (only if it requires authentication for pulls; anonymous access still needs a blank pull-secret entry — see below)
- The CA certificate for the artifact repository (if using an internal CA)

### Configure Remote Repositories

Create remote (proxy) repositories in your artifact manager for each upstream registry.

#### JFrog Artifactory

Create **Remote Container Repositories** for each upstream:

| Repository Key           | URL                                   | Notes                             |
| ------------------------ | ------------------------------------- | --------------------------------- |
| `quay-remote`            | `https://quay.io`                     | OpenShift release images          |
| `redhat-registry-remote` | `https://registry.redhat.io`          | Core Red Hat images               |
| `redhat-access-remote`   | `https://registry.access.redhat.com`  | Legacy Red Hat images (UBI, etc.) |
| `redhat-connect-remote`  | `https://registry.connect.redhat.com` | Certified partner operators       |

For each remote repository:

1. Go to **Administration > Repositories > Remote**
2. Select **Docker** as the package type
3. Set the **URL** to the upstream registry
4. Enable **Token Authentication** or provide Red Hat pull secret credentials
5. Under **Advanced**, enable **Store Artifacts Locally** (cache)

!!! tip
    Create a **Virtual Repository** (e.g., `container-virtual`) that aggregates all the remote repositories under a single endpoint. This simplifies the cluster configuration.

#### Sonatype Nexus

Create **container (proxy)** repositories for each upstream:

1. Go to **Repository > Repositories > Create repository**
2. Select **docker (proxy)**
3. Set the **Remote storage** URL to the upstream registry
4. Under **Container**, assign an HTTPS connector port (e.g., 5000)
5. Configure **Container Bearer Token Realm** in **Security > Realms**
6. Optionally create a **container (group)** repository to aggregate multiple proxy repos

### Configure Upstream Authentication

The upstream Red Hat registries require authentication. Configure the pull-through cache with valid credentials from your Red Hat pull secret.

**Artifactory:** Add credentials to each remote repository under **Advanced > Username/Password**, or use a token. The username is typically the service account token from your Red Hat pull secret.

**Nexus:** Add credentials in **Security > Realms** and associate them with each proxy repository.

### Configure TLS

If the artifact repository uses an internal CA or self-signed certificate, you will need the CA certificate for:

- The installation host's trust store (for `skopeo` and `oc` commands)
- The `additionalTrustBundle` in `install-config.yaml` (so cluster nodes trust the cache)

Add the CA to the installation host:

```bash
sudo cp /path/to/ca-cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

### Create a Merged Pull Secret

The pull secret used in `install-config.yaml` must include:

1. Your Red Hat pull secret (from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret))
2. An entry for your artifact repository hostname — **even if the cache allows anonymous pulls**

!!! warning "CRI-O requires a registry entry even for anonymous access"
    Without an `auths` entry for the artifact repository hostname, CRI-O will not attempt to pull from it at all — even when Artifactory/Nexus requires no credentials. The entry must exist; the `auth` value may be empty.

#### Artifact repository requires authentication

```bash
cp ~/pull-secret.txt ~/merged-pull-secret.json
podman login {{ artifactory_host }} --authfile ~/merged-pull-secret.json
```

#### Artifact repository allows anonymous access

Add a blank `auth` entry for the registry hostname. Do **not** use `podman login` or `oc registry login --auth-basic=":"` — those write a non-empty credential.

```bash
jq --arg host "{{ artifactory_host }}" \
  '.auths[$host] = {"auth": ""}' \
  ~/pull-secret.txt > ~/merged-pull-secret.json
```

The resulting file looks like:

```json
{
  "auths": {
    "cloud.openshift.com": {"auth": "<redhat-token>"},
    "quay.io": {"auth": "<redhat-token>"},
    "registry.redhat.io": {"auth": "<redhat-token>"},
    "registry.connect.redhat.com": {"auth": "<redhat-token>"},
    "{{ artifactory_host }}": {"auth": ""}
  }
}
```

!!! note
    The Red Hat credentials remain in the pull secret for install-time use. Upstream authentication from Artifactory to Red Hat registries is configured separately on each remote repository (see [Configure Upstream Authentication](#configure-upstream-authentication)).

### Pre-Warm the Cache (Recommended)

While a pull-through cache populates on demand, pre-warming avoids slow first pulls during installation. **Pull** through the cache — do not `oc adm release mirror` / push into a remote (proxy) repository; those repos typically reject pushes.

```bash
podman image pull \
  --authfile ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64

podman image pull \
  --authfile ~/merged-pull-secret.json \
  {{ artifactory_host }}/redhat-registry-remote/redhat/redhat-operator-index:v{{ ocp_version }}
```

### Validate the Cache

Before proceeding with installation, validate that the cache is correctly proxying images.

#### Verify TLS Connectivity

```bash
openssl s_client -connect {{ artifactory_host }}:443 -servername {{ artifactory_host }} </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
```

#### Verify Registry Authentication

```bash
podman login {{ artifactory_host }}
skopeo login {{ artifactory_host }}
```

#### Test Image Pulls Through the Cache

Verify that images can actually be pulled through the cache using `podman`:

```bash
podman image pull \
  --authfile ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
```

If this succeeds, the cache is correctly proxying from `quay.io`. You can also inspect images without downloading all layers using `skopeo`:

```bash
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64

skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-registry-remote/ubi9/ubi:latest
```

!!! tip
    If `podman pull` fails but `skopeo inspect` succeeds, the issue is usually TLS trust or credential format. Check that the CA is in `/etc/pki/ca-trust/source/anchors/` and that `update-ca-trust` has been run.

#### Verify the Release Payload

```bash
oc adm release info \
  --registry-config ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
```

This should print release metadata. If it fails, the installer will also fail — resolve the issue before proceeding.

#### Check the Cache UI

After running the above commands, verify in the repository UI that content has been cached:

- **Artifactory**: Navigate to **Application > Artifactory > Artifacts**, expand the remote repository, and confirm cached layers are present.
- **Nexus**: Navigate to **Browse > repository name** and verify image layers appear.

---

## Configure OpenShift for the Internal Registry

This section covers how to configure the OpenShift installer and post-install operators to pull images from your internal registry instead of public Red Hat registries.

### Step 1: Configure install-config.yaml

The standard installation process follows the [Agent-Based Installer](../agent-based.md) guide. For a disconnected environment, you add three fields to `install-config.yaml`:

| Field                   | Purpose                                                          |
| ----------------------- | ---------------------------------------------------------------- |
| `imageDigestSources`    | Routes image pulls to your internal registry                     |
| `additionalTrustBundle` | Adds your registry's CA certificate to cluster trust             |
| `pullSecret`            | Contains credentials for both Red Hat and your internal registry |

#### imageDigestSources

This tells the cluster to pull images from your internal registry instead of the upstream source.

!!! warning "Order matters — most specific sources first"
    CRI-O evaluates mirror rules sequentially from top to bottom. If a broad entry like `registry.redhat.io` appears before a more specific subpath like `registry.redhat.io/odf4`, the runtime matches the broad rule first and never reaches the specific one. Always list **more specific source paths above less specific ones**.

=== "Mirror Registry (oc-mirror)"

    The exact values come from `oc-mirror-workspace/working-dir/cluster-resources/idms-oc-mirror.yaml`. A typical configuration:

    ```yaml
    imageDigestSources:
      - mirrors:
          - {{ mirror_host }}:8443/openshift/release-images
        source: quay.io/openshift-release-dev/ocp-release
      - mirrors:
          - {{ mirror_host }}:8443/openshift/release
        source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
    ```

    !!! warning
        Always use the paths from the generated `idms-oc-mirror.yaml`. The paths depend on how `oc-mirror` was invoked and may differ from this example.

=== "Pull-Through Cache (Artifactory / Nexus)"

    Map each upstream registry to the corresponding remote repository in your cache:

    ```yaml
    imageDigestSources:
      - mirrors:
          - {{ artifactory_host }}/quay-remote
        source: quay.io
      - mirrors:
          - {{ artifactory_host }}/quay-remote
        source: cdn.quay.io
      - mirrors:
          - {{ artifactory_host }}/redhat-registry-remote
        source: registry.redhat.io
      - mirrors:
          - {{ artifactory_host }}/redhat-access-remote
        source: registry.access.redhat.com
      - mirrors:
          - {{ artifactory_host }}/redhat-connect-remote
        source: registry.connect.redhat.com
    ```

    !!! note
        `cdn.quay.io` must be included — Quay redirects blob downloads to this CDN hostname. Replace mirror paths with the actual repository names in your artifact repository.

#### additionalTrustBundle

Include the CA certificate of your internal registry so cluster nodes trust HTTPS connections to it:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < your registry CA certificate >
  -----END CERTIFICATE-----
```

#### pullSecret

Use the merged pull secret that contains credentials for both Red Hat registries and your internal registry (created during the registry setup step):

```yaml
pullSecret: '< contents of ~/merged-pull-secret.json >'
```

!!! warning "Anonymous registries require a blank auth entry"
    If your pull-through cache allows anonymous access, the pull secret must still contain an entry for the registry with an empty `auth` value — for example `"{{ artifactory_host }}": {"auth": ""}`. Do not use `podman login` or `oc registry login --auth-basic=":"` for this case; those write a non-empty credential. See [Pull-Through Cache — Create a Merged Pull Secret](#create-a-merged-pull-secret).

#### Complete Example

A full `install-config.yaml` for a disconnected environment (pull-through cache example):

```yaml
apiVersion: v1
baseDomain: {{ base_domain }}
metadata:
  name: {{ cluster_name }}
controlPlane:
  name: master
  architecture: amd64
  hyperthreading: Enabled
  replicas: 3
compute:
  - name: worker
    architecture: amd64
    hyperthreading: Enabled
    replicas: 3
networking:
  clusterNetwork:
    - cidr: 10.128.0.0/14
      hostPrefix: 23
  machineNetwork:
    - cidr: {{ machine_network_cidr }}
  networkType: OVNKubernetes
  serviceNetwork:
    - 172.30.0.0/16
platform:
  baremetal:
    apiVIPs:
      - {{ api_vip }}
    ingressVIPs:
      - {{ ingress_vip }}
pullSecret: '< contents of ~/merged-pull-secret.json >'
sshKey: '{{ public_key }}'
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < your registry CA certificate >
  -----END CERTIFICATE-----
imageDigestSources:
  - mirrors:
      - {{ artifactory_host }}/quay-remote
    source: quay.io
  - mirrors:
      - {{ artifactory_host }}/quay-remote
    source: cdn.quay.io
  - mirrors:
      - {{ artifactory_host }}/redhat-registry-remote
    source: registry.redhat.io
  - mirrors:
      - {{ artifactory_host }}/redhat-access-remote
    source: registry.access.redhat.com
  - mirrors:
      - {{ artifactory_host }}/redhat-connect-remote
    source: registry.connect.redhat.com
```

### Step 2: Install the Cluster

Follow the [Agent-Based Installer](../agent-based.md) guide for:

- Creating `agent-config.yaml` with host network configuration
- Generating the bootable ISO
- Booting nodes and monitoring installation

The installer uses the `imageDigestSources` to route all image pulls through your internal registry during bootstrap.

### Step 3: Post-Install Operator Configuration

After the cluster is running, configure the Operator Lifecycle Manager (OLM) to install operators from your internal registry.

#### Disable Default Catalog Sources

The default catalog sources point to public registries. Disable them:

```bash
export KUBECONFIG=~/ocp/install/auth/kubeconfig

oc patch operatorhub.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"disableAllDefaultSources":true}}'
```

#### Create Custom Catalog Sources

=== "Mirror Registry (oc-mirror)"

    Apply the catalog source generated by `oc-mirror`:

    ```bash
    oc apply -f oc-mirror-workspace/working-dir/cluster-resources/
    ```

=== "Pull-Through Cache (Artifactory / Nexus)"

    Create a catalog source that pulls the operator index through the cache:

    ```yaml
    apiVersion: operators.coreos.com/v1alpha1
    kind: CatalogSource
    metadata:
      name: redhat-operators
      namespace: openshift-marketplace
    spec:
      sourceType: grpc
      image: {{ artifactory_host }}/redhat-registry-remote/redhat/redhat-operator-index:v{{ ocp_version }}
      displayName: "Red Hat Operators"
      publisher: "Red Hat (via internal registry)"
      updateStrategy:
        registryPoll:
          interval: 60m
    ```

    ```bash
    oc apply -f catalog-source.yaml
    ```

#### Verify the Catalog Source

```bash
oc get pods -n openshift-marketplace
oc get catalogsource -n openshift-marketplace
oc get packagemanifest | head -10
```

The catalog pod should be `Running` and package manifests should be listed.

#### Install Operators

With the catalog source active, operators install normally:

- **Web Console**: Navigate to **Ecosystem > Software Catalog**, find the operator, and click **Install**
- **CLI**: Create a `Subscription` resource referencing your catalog source:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: odf-operator
  namespace: openshift-storage
spec:
  channel: stable-{{ ocp_version }}
  name: odf-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
```

#### Worked Example: Per-Operator Mirror Paths (ODF)

!!! note
    Use this pattern only when operator images live in **dedicated repository paths** (for example `{{ artifactory_host }}/odf4`) rather than the full-registry remotes configured in Step 1 (`redhat-registry-remote`, etc.). If you already mirrored `registry.redhat.io` wholesale via `imageDigestSources` / CatalogSource above, skip this section — install ODF from that catalog normally.

When operators are staged under separate Artifactory paths, you need an additional `ImageDigestMirrorSet` for those paths **and** a CatalogSource that points at the mirrored index.

!!! tip "IDMS ordering with mixed mirrors"
    If you have both a broad mirror for `registry.redhat.io` (from your install-config `imageDigestSources`) and a per-operator IDMS for a subpath like `registry.redhat.io/odf4`, the **per-operator IDMS must be applied separately** or its entries must appear **above** the broad entry. CRI-O evaluates rules top-to-bottom; the first match wins. A broad `registry.redhat.io` rule before `registry.redhat.io/odf4` will route ODF pulls to the wrong mirror path.

1. Disable default catalog sources (if not already done):

  ```bash
  oc patch operatorhub.config.openshift.io/cluster --type=merge \
    -p '{"spec":{"disableAllDefaultSources":true}}'
  ```

2. Create an `ImageDigestMirrorSet` for the operator image paths:

  ```yaml
  apiVersion: config.openshift.io/v1
  kind: ImageDigestMirrorSet
  metadata:
    name: odf-artifactory-mirror
  spec:
    imageDigestMirrors:
      - mirrors:
          - {{ artifactory_host }}/odf4
        source: registry.redhat.io/odf4
      - mirrors:
          - {{ artifactory_host }}/rhel9
        source: registry.redhat.io/rhel9
  ```

  ```bash
  oc apply -f odf-idms.yaml
  ```

!!! warning
    Applying an IDMS triggers a rolling reboot of all nodes as the Machine Config Operator updates `/etc/containers/registries.conf`. Wait for all nodes to return to `Ready` (`oc get nodes -w`) before proceeding.

3. Deploy a CatalogSource pointing at the mirrored operator index. Adjust the image path to match your Artifactory layout:

  ```yaml
  apiVersion: operators.coreos.com/v1alpha1
  kind: CatalogSource
  metadata:
    name: odf-catalog
    namespace: openshift-marketplace
  spec:
    sourceType: grpc
    image: {{ artifactory_host }}/olm/redhat-operator-index:v{{ ocp_version }}
    displayName: "Local ODF Artifactory Catalog"
    publisher: "Internal Artifactory"
    updateStrategy:
      registryPoll:
        interval: 30m
  ```

  ```bash
  oc apply -f odf-catalog.yaml
  ```

4. Verify the catalog pod starts:

  ```bash
  oc get pods -n openshift-marketplace
  oc get catalogsource odf-catalog -n openshift-marketplace
  ```

5. Install the operator:

  - **Web Console**: **Ecosystem > Software Catalog** → search for "OpenShift Data Foundation" → Install
  - **CLI**: Create a Subscription that references this catalog by name (`source: odf-catalog`):

  ```yaml
  apiVersion: operators.coreos.com/v1alpha1
  kind: Subscription
  metadata:
    name: odf-operator
    namespace: openshift-storage
  spec:
    channel: stable-{{ ocp_version }}
    name: odf-operator
    source: odf-catalog
    sourceNamespace: openshift-marketplace
    installPlanApproval: Automatic
  ```

### Step 4: Cluster Upgrades

#### Mirror Registry (oc-mirror)

Mirror the new release version before starting the upgrade:

```bash
# Update imageset-config.yaml with the new version range, then:
oc-mirror --config imageset-config.yaml \
  --workspace file://oc-mirror-workspace \
  docker://{{ mirror_host }}:8443/openshift \
  --authfile ~/merged-pull-secret.json \
  --v2
```

Apply the updated cluster resources (including the `UpdateService` CR from `platform.graph: true`), then initiate the upgrade:

```bash
oc apply -f oc-mirror-workspace/working-dir/cluster-resources/
oc get updateservice -A
oc adm upgrade
```

The `UpdateService` provides the Cincinnati graph so `oc adm upgrade` can list and select versions without reaching `api.openshift.com`. Bump `minVersion`/`maxVersion` in `imageset-config.yaml` to `{{ new_ocp_release }}` before the mirror run.

#### Pull-Through Cache

The cache fetches the new release image on demand. Simply initiate the upgrade:

```bash
oc adm upgrade
```

If the cluster cannot reach the update graph service, specify the release image directly:

```bash
oc adm upgrade --to-image={{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ new_ocp_release }}-x86_64 \
  --allow-explicit-upgrade
```

---

## Image Signature Verification — Optional

!!! tip
    Image signature verification is **optional security hardening**. The cluster installs and operates correctly without it. Add this when you want cryptographic proof that images pulled from your internal registry are genuinely signed by Red Hat.

Red Hat publishes image signatures as **sigstore attachments** stored alongside images (as `sha256-<digest>.sig` tags). If your registry serves these `.sig` tags, you can enforce signature verification with a `ClusterImagePolicy`.

### Confirm .sig tags are available

```bash
skopeo list-tags docker://{{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release | grep '\.sig$'
```

If no `.sig` tags appear, your registry is not caching signature attachments and this feature cannot be used.

### Apply the ClusterImagePolicy

Fetch the Red Hat release signing public key on a **connected** host (the disconnected bastion cannot reach `security.access.redhat.com`). Transfer the base64 string to the install host:

```bash
# On a host with outbound internet
curl -s https://security.access.redhat.com/data/63405576.txt | base64 -w0
```

Apply a policy with `remapIdentity` — this tells the policy the signature was made for the `quay.io` identity even though images are pulled from your registry:

```yaml
apiVersion: config.openshift.io/v1
kind: ClusterImagePolicy
metadata:
  name: openshift-release-mirror
spec:
  scopes:
    - {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release
  policy:
    rootOfTrust:
      policyType: PublicKey
      publicKey:
        keyData: <base64-key-from-above>
    signedIdentity:
      matchPolicy: RemapIdentity
      remapIdentity:
        prefix: {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release
        signedPrefix: quay.io/openshift-release-dev/ocp-release
```

!!! warning
    Do not create or edit a `ClusterImagePolicy` named `openshift` — that name is reserved for the built-in release policy.

### Day-1 Integration (Extra Manifest)

To enforce signature verification from first boot, place the `ClusterImagePolicy` in the `openshift/` directory before generating the ISO:

```
install/
├── install-config.yaml
├── agent-config.yaml
└── openshift/
    └── 99-cluster-image-policy.yaml
```

The installer embeds it into the ISO's Ignition config and applies it during bootstrap.

!!! note "Bootstrap timing"
    The `ClusterImagePolicy` is applied by the MCO once the cluster API is up. The initial release payload pull during bootstrap is governed by the bootstrap node's own `policy.json` (seeded from the pull secret and mirror config). The extra-manifest CIP governs the running cluster — day-2 pulls, operator images, and upgrades.

---

## Verification

### Check Image Mirroring Configuration

```bash
oc get imagedigestmirrorset -o yaml
```

### Verify Node-Level Image Pulls

```bash
oc debug node/<worker-node> -- chroot /host \
  crictl pull {{ artifactory_host }}/redhat-registry-remote/ubi9/ubi:latest
```

### Check MachineConfigPool Health

```bash
oc get mcp
```

All pools should show `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`.

### Verify Pods Are Using Internal Registry Images

```bash
oc get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u | head -20
```

---

## Troubleshooting

| Symptom                                         | Likely Cause                        | Fix                                          |
| ----------------------------------------------- | ----------------------------------- | -------------------------------------------- |
| `ImagePullBackOff` on any pod                   | Pull secret missing registry creds  | Update global pull secret                    |
| `x509: certificate signed by unknown authority` | CA not in `additionalTrustBundle`   | Add registry CA certificate                  |
| CatalogSource pod not starting                  | Catalog image path incorrect        | Verify remote repo name in image path        |
| Operator shows available but install hangs      | Bundle images routing to wrong repo | Add missing source to `ImageDigestMirrorSet` |
| MachineConfigPool degraded                      | `imageDigestSources` mismatch       | Verify paths match registry layout           |
| Upgrade shows no available versions             | Update graph unreachable            | Use `--to-image` with explicit release image |

For common installation issues, see [Troubleshooting](../troubleshooting.md).

## Documentation

- [About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring)
- [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)
- [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift)
