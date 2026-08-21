# Setting Up a Mirror Registry with oc-mirror

[About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring) | [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)

This guide covers setting up an internal container registry and populating it with OpenShift content using `oc-mirror`. Use this approach when **no system on the cluster network has outbound internet access** (fully air-gapped).

Once the registry is populated, see [Configuring OpenShift for a Disconnected Registry](openshift-config.md) to configure the installer and operators to use it.

## Architecture

```
Internet ──> Bastion Host ──> Portable Media ──> Mirror Registry ──> Cluster Nodes
              (oc-mirror)       (optional)        (on-site)           (no internet)
```

In some environments, the bastion host has temporary internet access and direct access to the mirror registry, eliminating the need for portable media.

## Prerequisites

- A bastion host with internet access (temporary or permanent) to download content
- At least 200 GB of available disk for the mirror registry storage
- A Red Hat pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
- The `oc` CLI available on the bastion host

---

## Install oc-mirror

On the bastion host with internet access:

```bash
OCP_VERSION={{ ocp_version }}
wget "https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable-${OCP_VERSION}/oc-mirror.tar.gz" -P /tmp
sudo tar -xvzf /tmp/oc-mirror.tar.gz -C /usr/local/bin
chmod +x /usr/local/bin/oc-mirror
oc-mirror version
```

## Install the Mirror Registry

You need a container registry on the disconnected network. Options include:

| Registry | Notes |
| -------- | ----- |
| [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift) | Purpose-built, minimal setup, runs with Podman |
| [Red Hat Quay](https://docs.redhat.com/en/documentation/red_hat_quay) | Full-featured, enterprise-grade |
| JFrog Artifactory | If already available in-house |
| Harbor | Open-source alternative |

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

## Configure Authentication

`oc-mirror` needs credentials for both the source (Red Hat) and destination (mirror) registries. Create a combined pull secret:

```bash
cp ~/pull-secret.txt ~/merged-pull-secret.json

podman login {{ mirror_host }}:8443 --authfile ~/merged-pull-secret.json
```

This produces `~/merged-pull-secret.json` containing credentials for both Red Hat registries and your mirror. You will use this file during mirroring and later in `install-config.yaml`.

## Create the ImageSetConfiguration

The `ImageSetConfiguration` defines what content to mirror. Create `imageset-config.yaml`:

```yaml
apiVersion: mirror.openshift.io/v2alpha1
kind: ImageSetConfiguration
storageConfig:
  local:
    path: /tmp/oc-mirror-metadata
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
        - name: mtv-operator
        - name: oadp-operator
        - name: openshift-gitops-operator
        - name: cluster-logging
        - name: loki-operator
  additionalImages:
    - name: registry.redhat.io/ubi9/ubi:latest
```

!!! tip
    Only mirror the operators you plan to install. Mirroring the entire catalog is very large (hundreds of GBs) and takes a long time. You can always re-run `oc-mirror` later to add more.

## Mirror the Content

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

## Output Files

`oc-mirror` generates output files in the `oc-mirror-workspace/results-*` directory:

| File | Purpose |
| ---- | ------- |
| `imageDigestMirrorSet.yaml` | Tells the cluster where to find mirrored images |
| `catalogSource.yaml` | Points OLM to the mirrored operator catalog |
| `updateService.yaml` | Points the update service to the mirror |

!!! warning
    The `imageDigestSources` values in your `install-config.yaml` must match the repository paths used by `oc-mirror`. Check the generated `imageDigestMirrorSet.yaml` for the exact mirror paths.

## Extract the openshift-install Binary

The `openshift-install` binary is embedded inside the release image. Extract it from the mirrored payload:

```bash
oc adm release extract \
  -a ~/merged-pull-secret.json \
  --command=openshift-install \
  {{ mirror_host }}:8443/openshift/release-images:{{ ocp_release }}-x86_64
```

!!! tip
    You can also download `openshift-install` from the [Red Hat mirror site](https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/) on a connected workstation and transfer it across the airgap. However, `oc adm release extract` guarantees version alignment with the mirrored payload.

## Verify the Mirror

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

---

## Adding More Content Later

Re-run `oc-mirror` with an updated `ImageSetConfiguration` to add new operators or release versions. The tool handles incremental updates:

```bash
oc-mirror --config imageset-config.yaml \
  docker://{{ mirror_host }}:8443/openshift \
  --authfile ~/merged-pull-secret.json \
  --v2
```

---

## Next Step

Once the mirror registry is populated, proceed to [Configuring OpenShift for a Disconnected Registry](openshift-config.md) to set up `install-config.yaml` and post-install operator configuration.

## Documentation

- [About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring)
- [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)
- [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift)
