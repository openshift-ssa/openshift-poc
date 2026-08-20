# Disconnected Cluster: Artifactory as Internal Registry

In a disconnected (air-gapped) environment, OpenShift has no access to public registries like `registry.redhat.io` or `quay.io`. All container images — including operator catalogs, operator bundles, and release images — must be served from an internal registry.

This page covers configuring a disconnected OpenShift cluster to pull all content from JFrog Artifactory acting as the internal mirror registry.

!!! note
    This page assumes your Artifactory instance is already deployed, accessible from the cluster network, and that you have already mirrored the required content into it. For the mirroring process itself, see the [oc-mirror workflow](#mirror-content-with-oc-mirror) below.

## Prerequisites

- Artifactory instance accessible from all cluster nodes over HTTPS
- Sufficient storage in Artifactory for OpenShift release images, operator catalogs, and operator bundles
- `oc` CLI and `oc-mirror` plugin installed on a host with access to both the internet and Artifactory (the "bastion")
- A pull secret that includes credentials for both `registry.redhat.io` (source) and your Artifactory instance (destination)

## Mirror Content with oc-mirror

The `oc-mirror` plugin copies images from public registries into your internal Artifactory. Run this on a bastion host that can reach both the internet and Artifactory.

1. Create an `ImageSetConfiguration` file defining what to mirror:

```yaml
apiVersion: mirror.openshift.io/v1alpha2
kind: ImageSetConfiguration
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
        - name: loki-operator
        - name: openshift-gitops-operator
        - name: cluster-logging
  additionalImages:
    - name: registry.redhat.io/ubi9/ubi-minimal:latest
```

!!! tip
    Only mirror the operators you actually need. Each operator adds significant storage requirements. The list above is a common POC set — adjust to match your needs.

2. Run the mirror operation:

```bash
oc mirror --config=imageset-config.yaml \
  docker://artifactory.example.com/openshift-mirror
```

This produces:
- Mirrored images pushed directly to Artifactory
- An `oc-mirror-workspace/results-*` directory containing YAML files to apply to the cluster

3. Copy the results directory to a host that can reach the cluster API (or transfer via sneakernet if fully air-gapped).

## Configure Cluster Trust (If Using Self-Signed Certificates)

If Artifactory uses a certificate signed by an internal CA, the cluster nodes must trust it.

1. Create a ConfigMap with the CA bundle:

```bash
oc create configmap registry-cas \
  -n openshift-config \
  --from-file=artifactory.example.com=./artifactory-ca.crt
```

The key name must be the registry hostname (including port if non-standard, e.g., `artifactory.example.com..5000`  — use `..` for the port separator).

2. Patch the cluster image config to reference the CA:

```bash
oc patch image.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"additionalTrustedCA":{"name":"registry-cas"}}}'
```

!!! warning
    This triggers a rolling restart of the MachineConfigOperator-managed nodes as the CA bundle is distributed. Wait for all nodes to return to `Ready` before proceeding.

## Apply the ImageDigestMirrorSet

The `oc-mirror` output directory contains an `ImageDigestMirrorSet` (or `ImageContentSourcePolicy` for older clusters). This tells the cluster to redirect image pulls from public registries to Artifactory.

```bash
oc apply -f oc-mirror-workspace/results-*/imageDigestMirrorSet-*.yaml
```

Verify the mirrors are configured:

```bash
oc get imagedigestmirrorset
```

You can also inspect the rules:

```bash
oc get imagedigestmirrorset -o yaml | grep -A 3 "mirrors:"
```

!!! note
    After applying the mirror set, nodes will restart to pick up the new registry configuration. Monitor with `oc get nodes -w` and wait for all nodes to be `Ready`.

## Update the Global Pull Secret

The cluster needs credentials to authenticate against Artifactory.

1. Export the current pull secret:

{% raw %}
```bash
oc get secret/pull-secret -n openshift-config \
  --template='{{index .data ".dockerconfigjson" | base64decode}}' > pull-secret.json
```
{% endraw %}

2. Merge your Artifactory credentials into the pull secret:

```bash
oc registry login --registry=artifactory.example.com \
  --auth-basic=<username>:<password> \
  --to=pull-secret.json
```

Or manually edit `pull-secret.json` to add:

```json
{
  "auths": {
    "artifactory.example.com": {
      "auth": "<base64-encoded-username:password>"
    }
  }
}
```

3. Apply the updated pull secret:

```bash
oc set data secret/pull-secret -n openshift-config \
  --from-file=.dockerconfigjson=pull-secret.json
```

!!! warning
    Updating the global pull secret triggers a rolling reboot of worker nodes.

## Disable Default Catalog Sources

The default `CatalogSources` point to `registry.redhat.io` which is unreachable from a disconnected cluster. Disable them to prevent error logs and failed pod scheduling:

```bash
oc patch operatorhub.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"disableAllDefaultSources":true}}'
```

Verify:

```bash
oc get catalogsource -n openshift-marketplace
```

Only your custom catalog sources should remain.

## Create Custom Catalog Sources

The `oc-mirror` output includes a `CatalogSource` YAML pointing to your mirrored index image in Artifactory:

```bash
oc apply -f oc-mirror-workspace/results-*/catalogSource-*.yaml
```

If you need to create one manually:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: redhat-operators-disconnected
  namespace: openshift-marketplace
spec:
  sourceType: grpc
  image: artifactory.example.com/openshift-mirror/redhat/redhat-operator-index:v{{ ocp_version }}
  displayName: "Red Hat Operators (Disconnected)"
  publisher: "Internal Mirror"
  updateStrategy:
    registryPoll:
      interval: 60m
```

Verify the catalog pod is running:

```bash
oc get pods -n openshift-marketplace
oc get catalogsource -n openshift-marketplace
```

The catalog source should show `READY` status and the pod should be `Running`.

## Install Operators

With the disconnected catalog in place, operators appear in OperatorHub as normal:

1. Navigate to **Operators** > **OperatorHub** in the web console
2. Operators from your mirrored catalog are listed under the custom display name
3. Install as usual — all images pull from Artifactory transparently

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
  source: redhat-operators-disconnected
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
```

## Configure Release Image Mirroring

For cluster upgrades in a disconnected environment, the cluster must pull release images from Artifactory rather than `quay.io`.

The release image signature and graph data are part of the `oc-mirror` output. Apply the release signatures:

```bash
oc apply -f oc-mirror-workspace/results-*/release-signatures/
```

To perform an upgrade using the mirrored release image:

```bash
oc adm upgrade --to-image=artifactory.example.com/openshift-mirror/openshift/release-images:{{ ocp_release }}-x86_64 \
  --allow-explicit-upgrade --force
```

!!! note
    Use `--force` only if the signature verification has already been applied. Without the release signatures, the cluster will reject the upgrade.

## Ongoing Maintenance

### Adding New Operators

When you need to mirror additional operators:

1. Update the `ImageSetConfiguration` with the new package names
2. Re-run `oc mirror` — it performs incremental mirroring (only new content is transferred)
3. Apply the updated `ImageDigestMirrorSet` and `CatalogSource` from the new results directory

### Cluster Upgrades

1. Update `ImageSetConfiguration` with the target version in `channels`
2. Run `oc mirror` to pull the new release images
3. Apply the new mirror set and release signatures
4. Trigger the upgrade with `oc adm upgrade`

### Verifying Mirror Health

Periodically confirm all images resolve correctly:

```bash
oc adm upgrade  # Should show available upgrades from mirrored content
oc get co       # All ClusterOperators should be Available, not Degraded
```

Check for image pull failures:

```bash
oc get events --all-namespaces --field-selector reason=Failed | grep -i "pull\|image"
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
| ------- | ------------ | --- |
| CatalogSource pod `ImagePullBackOff` | Pull secret missing Artifactory creds | Update global pull secret |
| CatalogSource pod `CrashLoopBackOff` | Index image corrupted or wrong tag | Re-mirror the catalog index |
| Operator install hangs on `InstallPlan` | Bundle images not mirrored | Check `ImageDigestMirrorSet` covers the bundle repo |
| Nodes stuck in `NotReady` after mirror set | CA cert not trusted | Verify `additionalTrustedCA` ConfigMap |
| `x509: certificate signed by unknown authority` | CA bundle missing or wrong key name | Key must match hostname exactly |
| OperatorHub shows no operators | Default catalogs disabled, custom not ready | Check `oc get catalogsource -n openshift-marketplace` |
| Upgrade fails with signature error | Release signatures not applied | Apply `release-signatures/` from oc-mirror output |
