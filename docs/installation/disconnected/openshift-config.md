# Configuring OpenShift for a Disconnected Registry

This guide covers how to configure the OpenShift installer and post-install operators to pull images from your internal registry instead of public Red Hat registries.

**Before you begin**, you must have an internal registry already set up and populated using one of these methods:

- [Setting Up a Mirror Registry with oc-mirror](oc-mirror.md) — for fully air-gapped environments
- [Setting Up a Pull-Through Cache (Artifactory / Nexus)](pull-through-cache.md) — for environments with a caching proxy

---

## Step 1: Configure install-config.yaml

The standard installation process follows the [Agent-Based Installer](../agent-based.md) guide. For a disconnected environment, you add three fields to `install-config.yaml`:

| Field                   | Purpose                                                          |
| ----------------------- | ---------------------------------------------------------------- |
| `imageDigestSources`    | Routes image pulls to your internal registry                     |
| `additionalTrustBundle` | Adds your registry's CA certificate to cluster trust             |
| `pullSecret`            | Contains credentials for both Red Hat and your internal registry |

### imageDigestSources

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

### additionalTrustBundle

Include the CA certificate of your internal registry so cluster nodes trust HTTPS connections to it:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < your registry CA certificate >
  -----END CERTIFICATE-----
```

### pullSecret

Use the merged pull secret that contains credentials for both Red Hat registries and your internal registry (created during the registry setup step):

```yaml
pullSecret: '< contents of ~/merged-pull-secret.json >'
```

!!! warning "Anonymous registries require a blank auth entry"
    If your pull-through cache allows anonymous access, the pull secret must still contain an entry for the registry with an empty `auth` value — for example `"{{ artifactory_host }}": {"auth": ""}`. Do not use `podman login` or `oc registry login --auth-basic=":"` for this case; those write a non-empty credential. See [Pull-Through Cache — Create a Merged Pull Secret](pull-through-cache.md#create-a-merged-pull-secret).

### Complete Example

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

---

## Step 2: Install the Cluster

Follow the [Agent-Based Installer](../agent-based.md) guide for:

- Creating `agent-config.yaml` with host network configuration
- Generating the bootable ISO
- Booting nodes and monitoring installation

The installer uses the `imageDigestSources` to route all image pulls through your internal registry during bootstrap.

---

## Step 3: Post-Install Operator Configuration

After the cluster is running, configure the Operator Lifecycle Manager (OLM) to install operators from your internal registry.

### Disable Default Catalog Sources

The default catalog sources point to public registries. Disable them:

```bash
export KUBECONFIG=~/ocp/install/auth/kubeconfig

oc patch operatorhub.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"disableAllDefaultSources":true}}'
```

### Create Custom Catalog Sources

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

### Verify the Catalog Source

```bash
oc get pods -n openshift-marketplace
oc get catalogsource -n openshift-marketplace
oc get packagemanifest | head -10
```

The catalog pod should be `Running` and package manifests should be listed.

### Install Operators

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

### Worked Example: Per-Operator Mirror Paths (ODF)

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

---

## Step 4: Cluster Upgrades

### Mirror Registry (oc-mirror)

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

### Pull-Through Cache

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
