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
