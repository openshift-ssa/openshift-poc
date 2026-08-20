# Disconnected Cluster: Artifactory Pull-Through Cache

In a restricted network environment, OpenShift nodes cannot reach public registries directly. JFrog Artifactory configured as a pull-through cache (remote repository) sits between the cluster and upstream registries, transparently proxying and caching images on first request.

This page covers configuring OpenShift to route all image pulls through Artifactory so that operators, workloads, and platform images are served from the local cache.

!!! note
    This page assumes Artifactory is already configured with remote repositories that proxy the required upstream registries (`registry.redhat.io`, `quay.io`, `docker.io`, etc.) and that the pull-through cache is functional.

## Prerequisites

- Artifactory accessible from all cluster nodes over HTTPS
- Remote repositories configured in Artifactory for:
  - `registry.redhat.io`
  - `quay.io`
  - `docker.io` (if pulling community images)
- A virtual repository in Artifactory that aggregates the remotes under a single hostname
- Artifactory credentials with pull access to the virtual repository
- The CA certificate for Artifactory (if using an internal CA)

## Step 1: Configure Cluster Certificate Trust

If Artifactory uses a certificate signed by an internal CA, the cluster must trust it before it can pull any images.

1. Create a ConfigMap with the Artifactory CA bundle. The key must be the registry hostname:

```bash
oc create configmap registry-cas \
  -n openshift-config \
  --from-file=artifactory.example.com=./artifactory-ca.crt
```

!!! tip
    If Artifactory uses a non-standard port, the key must include it with a `..` separator: `artifactory.example.com..8443`

2. Patch the cluster image config:

```bash
oc patch image.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"additionalTrustedCA":{"name":"registry-cas"}}}'
```

3. Wait for nodes to pick up the new CA:

```bash
oc get nodes -w
```

!!! warning
    This triggers a rolling restart of nodes. Wait for all nodes to return to `Ready` before proceeding.

## Step 2: Update the Global Pull Secret

The cluster needs credentials to authenticate to Artifactory when pulling images.

1. Export the current pull secret:

{% raw %}
```bash
oc get secret/pull-secret -n openshift-config \
  --template='{{index .data ".dockerconfigjson" | base64decode}}' > pull-secret.json
```
{% endraw %}

2. Add Artifactory credentials:

```bash
oc registry login --registry=artifactory.example.com \
  --auth-basic=<username>:<password> \
  --to=pull-secret.json
```

3. Apply the updated pull secret:

```bash
oc set data secret/pull-secret -n openshift-config \
  --from-file=.dockerconfigjson=pull-secret.json
```

!!! warning
    Updating the global pull secret triggers a rolling reboot of worker nodes.

## Step 3: Create the ImageDigestMirrorSet

Tell OpenShift to redirect image pulls from public registries to Artifactory. The pull-through cache handles the rest — if an image isn't cached yet, Artifactory fetches it from upstream and caches it for future requests.

```yaml
apiVersion: config.openshift.io/v1
kind: ImageDigestMirrorSet
metadata:
  name: artifactory-pull-through
spec:
  imageDigestMirrors:
    - mirrors:
        - artifactory.example.com/redhat-remote
      source: registry.redhat.io
    - mirrors:
        - artifactory.example.com/quay-remote
      source: quay.io
    - mirrors:
        - artifactory.example.com/docker-remote
      source: docker.io
```

!!! note
    Replace the mirror paths with the actual repository names configured in your Artifactory instance. These typically match the remote repository names (e.g., `redhat-remote`, `quay-remote`).

Apply and wait for nodes to restart:

```bash
oc apply -f image-digest-mirror-set.yaml
oc get nodes -w
```

Verify the mirror configuration:

```bash
oc get imagedigestmirrorset artifactory-pull-through -o yaml
```

## Step 4: Disable Default Catalog Sources

The default catalog sources point to `registry.redhat.io` directly. With the mirror set in place, they will route through Artifactory, but disabling them and creating explicit ones avoids confusion and gives you control over which catalogs are available.

```bash
oc patch operatorhub.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"disableAllDefaultSources":true}}'
```

## Step 5: Create Catalog Sources via Artifactory

Create catalog sources that reference the operator index images through Artifactory's pull-through path:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: redhat-operators
  namespace: openshift-marketplace
spec:
  sourceType: grpc
  image: artifactory.example.com/redhat-remote/redhat/redhat-operator-index:v{{ ocp_version }}
  displayName: "Red Hat Operators"
  publisher: "Red Hat (via Artifactory)"
  updateStrategy:
    registryPoll:
      interval: 60m
```

```bash
oc apply -f catalog-source.yaml
```

Verify the catalog pod starts successfully:

```bash
oc get pods -n openshift-marketplace
oc get catalogsource -n openshift-marketplace
```

!!! tip
    The first time the catalog pod starts, Artifactory will cache the index image from upstream. Subsequent pulls are served from cache instantly.

## Step 6: Install Operators

With the pull-through cache in place, operator installation works exactly like a connected cluster:

1. Navigate to **Operators** > **OperatorHub** in the web console
2. Select and install operators as normal
3. All images are transparently pulled through Artifactory

Via CLI:

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

## Image Signature Verification (OCP 4.19+)

Starting with OCP 4.19, Red Hat publishes image signatures as **sigstore attachments** stored in the registry alongside the image (as `sha256-<digest>.sig` tags). A pull-through cache can serve these signatures — but only if Artifactory caches the `.sig` tags and CRI-O is configured to look for them.

### Confirm Artifactory caches `.sig` tags

This is the make-or-break item. When CRI-O verifies a signature, it requests a tag like `sha256-<digest>.sig`. Your Artifactory remote repository must pass that through and cache it.

Test from a client:

```bash
skopeo list-tags docker://artifactory.example.com/quay-remote/openshift-release-dev/ocp-release | grep '\.sig$'
```

If no `.sig` tags come back, verify the Artifactory remote repository is not filtering tags and can reach the upstream. Nothing downstream works until this does.

!!! note
    If your Artifactory cannot cache `.sig` tags, you must fall back to mirroring the detached web sigstore (`https://access.redhat.com/webassets/docker/content/sigstore`) into a location you serve internally and pointing a `registries.d` lookaside at it. This is the escape hatch, but significantly more complex.

### Enable sigstore attachment lookup at the mirror

With an `ImageDigestMirrorSet` in place (Step 3), the MCO (4.17+) automatically registers the mirrors for sigstore attachment lookup when a `ClusterImagePolicy` is applied. Confirm your IDMS includes the release image repositories:

```yaml
apiVersion: config.openshift.io/v1
kind: ImageDigestMirrorSet
metadata:
  name: release-mirror
spec:
  imageDigestMirrors:
    - source: quay.io/openshift-release-dev/ocp-release
      mirrors:
        - artifactory.example.com/quay-remote/openshift-release-dev/ocp-release
    - source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
      mirrors:
        - artifactory.example.com/quay-remote/openshift-release-dev/ocp-v4.0-art-dev
```

### Apply the ClusterImagePolicy

Get the Red Hat release signing public key and base64-encode it:

```bash
curl -s https://security.access.redhat.com/data/63405576.txt | base64 -w0
```

Apply a policy scoped to the mirror. The `signedIdentity: remapIdentity` section is essential — it tells the policy the signature was made for the `quay.io` identity even though the image is pulled from Artifactory:

```yaml
apiVersion: config.openshift.io/v1
kind: ClusterImagePolicy
metadata:
  name: openshift-release-mirror
spec:
  scopes:
    - artifactory.example.com/quay-remote/openshift-release-dev/ocp-release
  policy:
    rootOfTrust:
      policyType: PublicKey
      publicKey:
        keyData: <base64-key-from-above>
    signedIdentity:
      matchPolicy: RemapIdentity
      remapIdentity:
        prefix: artifactory.example.com/quay-remote/openshift-release-dev/ocp-release
        signedPrefix: quay.io/openshift-release-dev/ocp-release
```

Repeat the scope/remap for each mirrored repository you want enforced (`ocp-v4.0-art-dev` for component images, `registry.redhat.io/redhat/...` for operators).

!!! warning
    Do not create or edit a `ClusterImagePolicy` named `openshift` — that name is reserved for the built-in release policy.

### Verify signature configuration

The MCO rolls this out to every node, writing `/etc/containers/policy.json` and `/etc/containers/registries.d/sigstore-registries.yaml`. Wait for the MachineConfigPool to finish, then verify on a node:

```bash
oc debug node/<node> -- chroot /host cat /etc/containers/policy.json
oc debug node/<node> -- chroot /host cat /etc/containers/registries.d/sigstore-registries.yaml
```

Confirm the mirror appears with `use-sigstore-attachments: true`. Test a pull of a signed image — if the `.sig` tag is cached, it verifies against the Red Hat key without ever reaching `access.redhat.com`.

### Day-1 integration with agent-based installer

If you are using the [agent-based installer](../installation/agent-based.md) in a disconnected environment, you can embed the `ClusterImagePolicy` as a day-1 extra manifest so that signature enforcement exists from the moment the cluster comes up.

The mirror configuration goes in `install-config.yaml` under `imageDigestSources` + `additionalTrustBundle`. The installer converts this into an `ImageDigestMirrorSet` automatically — you do not create the IDMS manually. You only need to provide the `ClusterImagePolicy` as an extra manifest.

**Install directory layout** (before generating the ISO):

```
install/
├── install-config.yaml
├── agent-config.yaml
└── openshift/
    └── 99-cluster-image-policy.yaml
```

**Mirror config in install-config.yaml:**

```yaml
imageDigestSources:
  - source: quay.io/openshift-release-dev/ocp-release
    mirrors:
      - artifactory.example.com/quay-remote/openshift-release-dev/ocp-release
  - source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
    mirrors:
      - artifactory.example.com/quay-remote/openshift-release-dev/ocp-v4.0-art-dev
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  <artifactory CA certificate>
  -----END CERTIFICATE-----
```

This produces the IDMS on the running cluster, and (4.17+) the MCO automatically adds these mirrors to the sigstore attachment registry config.

**ClusterImagePolicy as an extra manifest** (`install/openshift/99-cluster-image-policy.yaml`):

```yaml
apiVersion: config.openshift.io/v1
kind: ClusterImagePolicy
metadata:
  name: openshift-release-mirror
spec:
  scopes:
    - artifactory.example.com/quay-remote/openshift-release-dev/ocp-release
  policy:
    rootOfTrust:
      policyType: PublicKey
      publicKey:
        keyData: <base64 of https://security.access.redhat.com/data/63405576.txt>
    signedIdentity:
      matchPolicy: RemapIdentity
      remapIdentity:
        prefix: artifactory.example.com/quay-remote/openshift-release-dev/ocp-release
        signedPrefix: quay.io/openshift-release-dev/ocp-release
```

You can include multiple YAML documents (or multiple files) in `openshift/` for additional scopes (`ocp-v4.0-art-dev`, `registry.redhat.io` operator repos, etc.).

**Generate and boot:**

```bash
openshift-install agent create image --dir=install --log-level=debug
```

The installer embeds the extra manifests into the ISO's Ignition config. During bootstrap, the Assisted Service applies them alongside the generated IDMS.

!!! note "Bootstrap timing"
    The `ClusterImagePolicy` is applied by the MCO once the cluster API is up. The initial release payload pull during bootstrap is governed by the bootstrap node's own `policy.json` (seeded from the pull secret and mirror config), not by your CIP. The extra-manifest CIP governs the running cluster — day-2 pulls, operator images, and upgrades — which is where you need enforcement. Bootstrap release verification relies on the mirror + release signature ConfigMap path instead.

## Cluster Upgrades

With the `ImageDigestMirrorSet` in place, cluster upgrades pull release images through Artifactory automatically:

```bash
oc adm upgrade
```

The cluster checks the update graph and pulls the release image via the configured mirror. Artifactory caches the release image on first pull.

If the cluster cannot reach the update graph service (Cincinnati), you can specify the release image directly:

```bash
oc adm upgrade --to-image=artifactory.example.com/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  --allow-explicit-upgrade
```

## Verifying the Pull-Through Cache

Confirm images are being served through Artifactory:

```bash
oc get events --all-namespaces --field-selector reason=Pulled | tail -10
```

The image references in events should show your Artifactory hostname. You can also check Artifactory's UI or API for cache hit statistics on the remote repositories.

Test a manual pull through the cache:

```bash
oc run test --image=artifactory.example.com/redhat-remote/ubi9/ubi-minimal:latest \
  --rm -it --restart=Never -- echo "Pull-through cache is working"
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
| ------- | ------------ | --- |
| `ImagePullBackOff` on any pod | Pull secret missing Artifactory creds | Update global pull secret |
| `x509: certificate signed by unknown authority` | CA not trusted by nodes | Check `additionalTrustedCA` ConfigMap key matches hostname |
| CatalogSource pod not starting | Index image path incorrect | Verify Artifactory remote repo name in image path |
| Image pulls slow on first request | Expected — Artifactory is caching from upstream | Subsequent pulls will be fast from cache |
| `unauthorized: authentication required` | Artifactory credentials incorrect or expired | Regenerate and reapply pull secret |
| Operator shows available but install hangs | Bundle images routing to wrong remote repo | Add missing source to `ImageDigestMirrorSet` |
| Upgrade shows no available versions | Cincinnati service unreachable | Use `--to-image` with explicit release image |
| Nodes not restarting after mirror set change | MachineConfigPool paused | Check `oc get mcp` for paused pools |
