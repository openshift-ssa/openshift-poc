# Setting Up a Pull-Through Cache (Artifactory / Nexus)

This guide covers configuring an artifact repository (JFrog Artifactory or Sonatype Nexus) as a pull-through cache for container images. Use this approach when **your artifact repository has outbound internet access** but cluster nodes do not.

Once the cache is configured, see [Configuring OpenShift for a Disconnected Registry](openshift-config.md) to configure the installer and operators to use it.

## Architecture

```
Upstream Registries ──> Artifactory / Nexus ──> Cluster Nodes
  (quay.io, etc.)       (has outbound access)    (no outbound access)
```

A pull-through cache acts as a transparent proxy. When the cluster requests an image, the cache fetches it from the upstream registry, stores a local copy, and serves it. Subsequent pulls are served from the cache. This is simpler than a full mirror because you do not need to pre-stage content.

## Prerequisites

- Artifact repository (Artifactory or Nexus) accessible from all cluster nodes over HTTPS
- Artifact repository has outbound access to:
  - `quay.io` / `cdn.quay.io`
  - `registry.redhat.io`
  - `registry.access.redhat.com`
  - `registry.connect.redhat.com`
- A Red Hat pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
- Credentials for the artifact repository
- The CA certificate for the artifact repository (if using an internal CA)

---

## Configure Remote Repositories

Create remote (proxy) repositories in your artifact manager for each upstream registry.

### JFrog Artifactory

Create **Remote Container Repositories** for each upstream:

| Repository Key | URL | Notes |
| -------------- | --- | ----- |
| `quay-remote` | `https://quay.io` | OpenShift release images |
| `redhat-registry-remote` | `https://registry.redhat.io` | Core Red Hat images |
| `redhat-access-remote` | `https://registry.access.redhat.com` | Legacy Red Hat images (UBI, etc.) |
| `redhat-connect-remote` | `https://registry.connect.redhat.com` | Certified partner operators |

For each remote repository:

1. Go to **Administration > Repositories > Remote**
2. Select **Docker** as the package type
3. Set the **URL** to the upstream registry
4. Enable **Token Authentication** or provide Red Hat pull secret credentials
5. Under **Advanced**, enable **Store Artifacts Locally** (cache)

!!! tip
    Create a **Virtual Repository** (e.g., `container-virtual`) that aggregates all the remote repositories under a single endpoint. This simplifies the cluster configuration.

### Sonatype Nexus

Create **container (proxy)** repositories for each upstream:

1. Go to **Repository > Repositories > Create repository**
2. Select **docker (proxy)**
3. Set the **Remote storage** URL to the upstream registry
4. Under **Container**, assign an HTTPS connector port (e.g., 5000)
5. Configure **Container Bearer Token Realm** in **Security > Realms**
6. Optionally create a **container (group)** repository to aggregate multiple proxy repos

---

## Configure Upstream Authentication

The upstream Red Hat registries require authentication. Configure the pull-through cache with valid credentials from your Red Hat pull secret.

**Artifactory:** Add credentials to each remote repository under **Advanced > Username/Password**, or use a token. The username is typically the service account token from your Red Hat pull secret.

**Nexus:** Add credentials in **Security > Realms** and associate them with each proxy repository.

---

## Configure TLS

If the artifact repository uses an internal CA or self-signed certificate, you will need the CA certificate for:

- The installation host's trust store (for `skopeo` and `oc` commands)
- The `additionalTrustBundle` in `install-config.yaml` (so cluster nodes trust the cache)

Add the CA to the installation host:

```bash
sudo cp /path/to/ca-cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

---

## Create a Merged Pull Secret

Create a combined pull secret that includes credentials for both Red Hat registries and your artifact repository:

```bash
cp ~/pull-secret.txt ~/merged-pull-secret.json

podman login {{ artifactory_host }} --authfile ~/merged-pull-secret.json
```

This produces `~/merged-pull-secret.json` containing credentials for all registries. You will use this file in `install-config.yaml`.

!!! warning "Anonymous pull-through caches still need a pull-secret entry"
    Even if Artifactory/Nexus allows **anonymous** image pulls (no credentials required), you **must** include a blank `auth` entry for the registry hostname in the pull secret. Without it, CRI-O will not attempt to pull from the host at all.

    If your cache does not require authentication, manually add a blank entry:

    ```bash
    oc registry login --registry {{ artifactory_host }} \
      --auth-basic=":"  --to ~/merged-pull-secret.json
    ```

    Or manually merge the entry into your pull secret JSON:

    ```json
    {
      "auths": {
        "{{ artifactory_host }}": {"auth": ""},
        "cloud.openshift.com": {"auth": "<redhat-token>"},
        "quay.io": {"auth": "<redhat-token>"},
        "registry.redhat.io": {"auth": "<redhat-token>"},
        "registry.connect.redhat.com": {"auth": "<redhat-token>"}
      }
    }
    ```

    The Red Hat credentials are still required so that Artifactory can authenticate to upstream registries on your behalf.

---

## Pre-Warm the Cache (Recommended)

While a pull-through cache populates on demand, pre-warming avoids slow first pulls during installation. **Pull** through the cache — do not `oc adm release mirror` / push into a remote (proxy) repository; those repos typically reject pushes.

```bash
podman image pull \
  --authfile ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64

podman image pull \
  --authfile ~/merged-pull-secret.json \
  {{ artifactory_host }}/redhat-registry-remote/redhat/redhat-operator-index:v{{ ocp_version }}
```

---

## Validate the Cache

Before proceeding with installation, validate that the cache is correctly proxying images.

### Verify TLS Connectivity

```bash
openssl s_client -connect {{ artifactory_host }}:443 -servername {{ artifactory_host }} </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
```

### Verify Registry Authentication

```bash
podman login {{ artifactory_host }}
skopeo login {{ artifactory_host }}
```

### Test Image Pulls Through the Cache

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

### Verify the Release Payload

```bash
oc adm release info \
  --registry-config ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
```

This should print release metadata. If it fails, the installer will also fail — resolve the issue before proceeding.

### Check the Cache UI

After running the above commands, verify in the repository UI that content has been cached:

- **Artifactory**: Navigate to **Application > Artifactory > Artifacts**, expand the remote repository, and confirm cached layers are present.
- **Nexus**: Navigate to **Browse > repository name** and verify image layers appear.

---

## Next Step

Once the cache is validated, proceed to [Configuring OpenShift for a Disconnected Registry](openshift-config.md) to set up `install-config.yaml` and post-install operator configuration.
