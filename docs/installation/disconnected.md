# Disconnected Install

[About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring) | [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)

A disconnected (air-gapped) installation is required when cluster nodes have no direct outbound access to the internet. Instead of pulling container images from Red Hat registries at install time, you pre-stage all required content in a local registry that the cluster can reach.

There are two approaches to making images available locally:

1. **Mirror Registry** — Use `oc-mirror` to download all required images and mirror them into a local container registry. This is the fully air-gapped approach for environments with no outbound connectivity at all.
2. **Pull-Through Cache** — Use an artifact repository like JFrog Artifactory or Sonatype Nexus as a transparent proxy that caches images on first pull. This works when the artifact repository has outbound access but the cluster nodes do not.

!!! info "Which approach should I use?"
    If the environment has **zero outbound access** from any system on the cluster network, use the mirror registry approach. If there is a centralized artifact repository that already has outbound access (common in enterprise environments), the pull-through cache is simpler to set up and maintain.

## Prerequisites

- Complete the [prerequisites](../prerequisites/index.md)
- Set up the [installation host](../prerequisites/installation-host.md)
- Familiarity with the [Agent-Based Installer](agent-based.md) — this guide builds on that workflow

---

## Obtaining the openshift-install Binary

The `openshift-install` binary is needed to generate the bootable ISO, but you cannot download it from the internet on a disconnected machine. The binary is embedded inside the OpenShift release container image itself — you extract it from the payload you mirrored to your internal registry.

### Transfer the oc CLI Across the Airgap

You need the `oc` CLI on the disconnected installation host before you can extract anything. On a workstation with internet access, download `oc` from the [Red Hat mirror site](https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/) and transfer it into the disconnected environment via bastion host, secure file transfer, or physical media.

### Extract the Installer from the Mirrored Payload

Once the release images have been mirrored to your internal registry and `oc` is available on the disconnected installation host, extract the installer:

```bash
oc adm release extract \
  -a ~/merged-pull-secret.json \
  --command=openshift-install \
  {{ mirror_host }}:8443/openshift/release-images:{{ ocp_release }}-x86_64
```

This pulls the `openshift-install` binary out of the release image in your internal registry and writes it to the current directory. The `--command` flag tells `oc` to extract only the named binary rather than the full image contents.

!!! tip "Why not just download the tarball?"
    You can download the `openshift-install` tarball from Red Hat at the same time you download `oc` on your connected workstation and transfer both across the airgap. However, using `oc adm release extract` guarantees that the installer version is an exact match for the release payload you mirrored — eliminating any risk of a version mismatch between the installer and the images it references.

## Option 1: Mirror Registry with oc-mirror

This approach uses `oc-mirror` to download all OpenShift release images, operator catalogs, and any additional images into a local registry. It is the only option for fully air-gapped environments.

### Architecture

```
Internet ──> Bastion Host ──> Portable Media ──> Mirror Registry ──> Cluster Nodes
              (oc-mirror)       (optional)        (on-site)
```

In some environments, the bastion host has temporary internet access and direct access to the mirror registry, eliminating the need for portable media.

### Install oc-mirror

Download `oc-mirror` on a host with internet access:

```bash
OCP_VERSION={{ ocp_version }}
wget "https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable-${OCP_VERSION}/oc-mirror.tar.gz" -P /tmp
sudo tar -xvzf /tmp/oc-mirror.tar.gz -C /usr/local/bin
chmod +x /usr/local/bin/oc-mirror
oc-mirror version
```

### Set Up the Mirror Registry

You need a container registry on the disconnected network. Options include:

| Registry                                                                                                                                                                                                                                                       | Notes                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift) | Purpose-built, minimal setup, runs with Podman |
| [Red Hat Quay](https://docs.redhat.com/en/documentation/red_hat_quay)                                                                                                                                                                                           | Full-featured, enterprise-grade                |
| JFrog Artifactory                                                                                                                                                                                                                                              | If already available in-house                  |
| Harbor                                                                                                                                                                                                                                                         | Open-source alternative                        |

To install the mirror registry for Red Hat OpenShift on the installation host:

```bash
wget https://developers.redhat.com/content-gateway/rest/mirror/pub/openshift-v4/clients/mirror-registry/latest/mirror-registry.tar.gz -P /tmp
tar -xvzf /tmp/mirror-registry.tar.gz -C /tmp
sudo /tmp/mirror-registry install --quayHostname {{ mirror_host }} --quayRoot /opt/quay
```

The install command outputs the initial credentials (`init` user and generated password) and generates a self-signed root CA certificate at `/opt/quay/quay-rootCA/rootCA.pem`. Save the credentials — you will need them to log in to the registry.

Add the root CA to the installation host's trust store so tools like `podman` and `oc-mirror` trust the registry's TLS certificate:

```bash
sudo cp /opt/quay/quay-rootCA/rootCA.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

You can view the certificate to confirm it matches your mirror host:

```bash
openssl x509 -in /opt/quay/quay-rootCA/rootCA.pem -noout -subject -issuer
```

Verify access:

```bash
podman login {{ mirror_host }}:8443
```

!!! warning
    You will need the contents of this same `rootCA.pem` file later for the `additionalTrustBundle` field in `install-config.yaml`. Without it, the cluster nodes will not trust the mirror registry and image pulls will fail.

### Configure Authentication

`oc-mirror` needs credentials for both the source (Red Hat) and destination (mirror) registries. Create a combined pull secret:

```bash
# Start with your Red Hat pull secret
cp ~/pull-secret.txt ~/merged-pull-secret.json

# Login to the mirror registry (this updates the auth file)
podman login {{ mirror_host }}:8443 --authfile ~/merged-pull-secret.json
```

### Create the ImageSetConfiguration

The `ImageSetConfiguration` defines what content to mirror. Create `imageset-config.yaml`:

```yaml
kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v2alpha1
mirror:
  platform:
    channels:
      - name: stable-{{ ocp_version }}
        minVersion: {{ ocp_release }}
        maxVersion: {{ ocp_release }}
  operators:
    - catalog: registry.redhat.io/redhat/redhat-operator-index:v{{ ocp_version }}
      packages:
        - name: local-storage-operator
        - name: odf-operator
        - name: kubernetes-nmstate-operator
        - name: kubevirt-hyperconverged
  additionalImages:
    - name: registry.redhat.io/ubi9/ubi:latest
```

!!! tip
    Only mirror the operators you plan to install. Mirroring the entire catalog is very large (hundreds of GBs) and takes a long time. You can always re-run `oc-mirror` later to add more operators.

### Mirror the Content

=== "Direct (bastion has access to both networks)"

    ```bash
    oc-mirror --config imageset-config.yaml \
      docker://{{ mirror_host }}:8443/openshift \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

=== "Air-Gapped (two-step with portable media)"

    On the internet-connected host, mirror to disk:

    ```bash
    oc-mirror --config imageset-config.yaml \
      file:///mnt/mirror-data \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

    Transfer `/mnt/mirror-data` to the disconnected network, then load into the registry:

    ```bash
    oc-mirror --from file:///mnt/mirror-data \
      docker://{{ mirror_host }}:8443/openshift \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

`oc-mirror` generates output files in the `oc-mirror-workspace/results-*` directory. You will need these during install:

| File                              | Purpose                                         |
| --------------------------------- | ----------------------------------------------- |
| `imageDigestMirrorSet.yaml`     | Tells the cluster where to find mirrored images |
| `catalogSource.yaml`            | Points OLM to the mirrored operator catalog     |
| `updateService.yaml`            | Points the update service to the mirror         |

### Configure install-config.yaml

Start with the standard `install-config.yaml` from the [Agent-Based Installer](agent-based.md) guide and add three disconnected-specific fields: the image mirror routing, the combined pull secret, and the registry's TLS trust bundle.

#### Image Mirror Routing

`imageDigestSources` tells the installer which public registries map to your internal mirror. When you ran `oc-mirror`, it generated these exact mappings in `imageDigestMirrorSet.yaml` — copy the values from there.

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
    The `imageDigestSources` values must match the repository paths used by `oc-mirror`. Check the generated `imageDigestMirrorSet.yaml` for the exact values.

!!! note
    `imageDigestSources` was introduced in OpenShift 4.14. If you are on 4.13 or older, use the legacy `imageContentSources` key instead.

#### Combined Pull Secret

The default Red Hat pull secret only authenticates against `quay.io` and `registry.redhat.io`. In a disconnected environment, you must combine it with credentials for your internal registry. The `merged-pull-secret.json` created in the [Configure Authentication](#configure-authentication) step already contains both — use its contents as the `pullSecret` value:

```yaml
pullSecret: '< contents of ~/merged-pull-secret.json >'
```

The value must be a single JSON string containing the base64-encoded auth tokens for both Red Hat and your mirror registry.

#### Additional Trust Bundle

Internal registries almost always use self-signed or internal CA certificates. Without the CA certificate in the install config, cluster nodes will reject TLS connections to the mirror and image pulls will fail. Paste the PEM-encoded CA certificate (the `rootCA.pem` generated during [mirror registry setup](#set-up-the-mirror-registry)) under `additionalTrustBundle`:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < contents of /opt/quay/quay-rootCA/rootCA.pem >
  -----END CERTIFICATE-----
```

#### Putting It All Together

When appended to your base configuration, the disconnected-specific portion of `install-config.yaml` looks like this:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < contents of /opt/quay/quay-rootCA/rootCA.pem >
  -----END CERTIFICATE-----
imageDigestSources:
  - mirrors:
      - {{ mirror_host }}:8443/openshift/release-images
    source: quay.io/openshift-release-dev/ocp-release
  - mirrors:
      - {{ mirror_host }}:8443/openshift/release
    source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
pullSecret: '< contents of ~/merged-pull-secret.json >'
```

!!! warning
    Always make a backup copy of your `install-config.yaml` before running the installer. The installation process consumes and deletes this file when generating Ignition configurations.

### Generate and Boot the ISO

Follow the same ISO generation, hosting, and boot process from the [Agent-Based Installer](agent-based.md#generate-the-iso) guide.

### Post-Install: Apply Catalog Source

After the cluster is running, apply the generated catalog source so operators can be installed from the mirror:

```bash
export KUBECONFIG=~/ocp/install/auth/kubeconfig
oc apply -f oc-mirror-workspace/results-*/catalogSource.yaml
```

Disable the default OperatorHub sources since they are unreachable:

```bash
oc patch OperatorHub cluster --type json \
  -p '[{"op": "add", "path": "/spec/disableAllDefaultSources", "value": true}]'
```

---

## Option 2: Pull-Through Cache (Artifactory / Nexus)

A pull-through cache acts as a transparent proxy between the cluster and upstream registries. When the cluster requests an image, the cache fetches it from the upstream registry, stores a local copy, and serves it. Subsequent pulls are served from the cache without outbound traffic.

This approach is significantly simpler than a full mirror because you do not need to pre-stage content — the cache populates itself on demand.

### Architecture

```
Upstream Registries ──> Artifactory / Nexus ──> Cluster Nodes
  (quay.io, etc.)       (has outbound access)    (no outbound access)
```

### Configure Remote Repositories

Create remote (proxy) repositories in your artifact manager for each upstream registry the cluster needs.

#### JFrog Artifactory

In Artifactory, create **Remote Container Repositories** for each upstream:

| Repository Key               | URL                                     | Notes                                |
| ---------------------------- | --------------------------------------- | ------------------------------------ |
| `quay-remote`              | `https://quay.io`                     | OpenShift release images             |
| `redhat-registry-remote`  | `https://registry.redhat.io`          | Core Red Hat images                  |
| `redhat-access-remote`    | `https://registry.access.redhat.com`  | Core Red Hat images                  |
| `redhat-connect-remote`   | `https://registry.connect.redhat.com` | Certified partner operators          |

For each remote repository:

1. Go to **Administration > Repositories > Remote**
2. Select **Docker** as the package type
3. Set the **URL** to the upstream registry
4. Enable **Token Authentication** or provide Red Hat pull secret credentials
5. Under **Advanced**, enable **Store Artifacts Locally** (cache)

!!! tip
    Create a **Virtual Repository** (e.g., `container-virtual`) that aggregates all the remote repositories under a single endpoint. This simplifies the cluster configuration.

#### Sonatype Nexus

In Nexus, create **container (proxy)** repositories for each upstream:

1. Go to **Repository > Repositories > Create repository**
2. Select **docker (proxy)**
3. Set the **Remote storage** URL to the upstream registry
4. Under **Container**, assign an HTTPS connector port (e.g., 5000)
5. Configure **Container Bearer Token Realm** in **Security > Realms**
6. Optionally create a **container (group)** repository to aggregate multiple proxy repos

### Configure Authentication

If the upstream registries require authentication (they do for Red Hat registries), configure the pull-through cache with valid credentials from your pull secret.

For Artifactory, add the credentials to each remote repository under **Advanced > Username/Password** or use an access token with the upstream registry.

### Configure install-config.yaml

Add `imageDigestSources` to redirect image pulls to your cache and the trust bundle if the cache uses internal TLS certificates. Start with the standard `install-config.yaml` from the [Agent-Based Installer](agent-based.md) guide and add:

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

If the artifact repository uses a self-signed or internal TLS certificate:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < certificate content >
  -----END CERTIFICATE-----
```

### Update the Pull Secret

The cluster pull secret must include credentials for your artifact repository. Merge them with the Red Hat pull secret:

```bash
# Login to the artifact repository
podman login {{ artifactory_host }} --authfile ~/merged-pull-secret.json
```

Use the merged pull secret in the `pullSecret` field of `install-config.yaml`.

### Pre-Warm the Cache (Recommended)

While a pull-through cache populates on demand, you can pre-warm it to avoid slow first pulls during installation. From a host with access to both the internet and the cache, pull the release images through the cache:

```bash
oc adm release mirror \
  --from=quay.io/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  --to={{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release \
  --to-release-image={{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  -a ~/merged-pull-secret.json
```

### Validate the Pull-Through Cache

Before generating the ISO, validate that the cache is correctly proxying images. Catching misconfigurations here avoids a failed install.

#### 1. Verify TLS Connectivity

Confirm the installation host trusts the artifact repository's TLS certificate:

```bash
openssl s_client -connect {{ artifactory_host }}:443 -servername {{ artifactory_host }} </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
```

If using a self-signed or internal CA, add it to the trust store:

```bash
sudo cp /path/to/ca-cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

#### 2. Verify Registry Authentication

Confirm credentials are valid for both the cache and upstream:

```bash
podman login {{ artifactory_host }}
skopeo login {{ artifactory_host }}
```

#### 3. Test Image Pulls Through the Cache

Use `skopeo inspect` to verify the cache can fetch image metadata from each upstream registry without downloading the full image:

```bash
# Test quay.io proxy
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64

# Test registry.redhat.io proxy
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-registry-remote/ubi9/ubi:latest

# Test registry.access.redhat.com proxy
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-access-remote/ubi9/ubi:latest
```

If any of these fail, check the remote repository configuration and upstream credentials in Artifactory/Nexus.

#### 4. Verify the Release Payload

Confirm the full release payload is resolvable through the cache:

```bash
oc adm release info \
  --registry-config ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
```

This should print the release metadata (component images, versions, and digests). If it fails, the installer will also fail — resolve the issue before proceeding.

#### 5. Verify the Operator Catalog

If the cluster will install operators through the cache, verify the catalog index is accessible:

```bash
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-registry-remote/redhat/redhat-operator-index:v{{ ocp_version }}
```

#### 6. Check the Cache Repository (Artifactory/Nexus UI)

After running the `skopeo inspect` or pre-warm commands, verify in the artifact repository UI that content has been cached:

- **Artifactory**: Navigate to **Application > Artifactory > Artifacts**, expand the remote repository (e.g., `quay-remote-cache`), and confirm cached layers and manifests are present.
- **Nexus**: Navigate to **Browse > <repository name>** and verify that image layers appear under the proxied paths.

If the repositories are empty after running the above commands, the proxy configuration or upstream authentication is incorrect.

### Generate and Boot the ISO

Follow the same ISO generation, hosting, and boot process from the [Agent-Based Installer](agent-based.md#generate-the-iso) guide.

---

## Post-Install Verification

After installation, verify the cluster is pulling images from the local source.

### Check Image Mirroring Configuration

```bash
oc get imagedigestmirrorset -o yaml
```

### Verify Node-Level Image Pulls

Test pulling an image from a cluster node through the mirror or cache:

```bash
oc debug node/{{ worker_node_name }} -- chroot /host \
  podman pull {{ mirror_or_cache_host }}/ubi9/ubi:latest
```

### Check MachineConfigPool Health

A degraded MCP is a common symptom of mirror misconfiguration (bad certificates, incorrect `imageDigestSources`):

```bash
oc get mcp
```

All pools should show `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`.

### Verify Pods Are Using Cached Images

Spot-check that running pods resolved their images through the cache, not directly from upstream:

```bash
oc get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u | head -20
```

The image references should reflect the mirror/cache paths, not the upstream registries.

### Verify Operator Catalog Access

If using OLM operators through the cache, confirm the catalog source is healthy:

```bash
oc get catalogsource -n openshift-marketplace
oc get packagemanifest | head -10
```

Both commands should return results without errors.

## Ongoing Maintenance

### Adding New Content

For mirror registries, re-run `oc-mirror` with an updated `ImageSetConfiguration` to add new operators or update to a new OpenShift release. The tool handles incremental updates.

For pull-through caches, no action is required — new content is cached on first pull. However, verify that your cache retention policies do not evict images that are still in use by the cluster.

### Updating the Cluster

For mirror registries, mirror the new release version before starting the upgrade:

```bash
# Update imageset-config.yaml with the new version range, then:
oc-mirror --config imageset-config.yaml \
  docker://{{ mirror_host }}:8443/openshift \
  --authfile ~/merged-pull-secret.json \
  --v2
```

Apply the updated `ImageDigestMirrorSet` and `CatalogSource` if they changed, then initiate the upgrade through the web console or CLI.

For pull-through caches, the upgrade process pulls new images on demand through the cache. No pre-staging is required, but pre-warming is still recommended to avoid timeouts during the upgrade.

## Documentation

- [About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring)
- [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)
- [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift)
- [Updating a cluster in a disconnected environment](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/updating-a-cluster-in-a-disconnected-environment)
