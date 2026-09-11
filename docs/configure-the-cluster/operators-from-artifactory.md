# Installing Operators from JFrog Artifactory

To install OpenShift operators sourced from JFrog Artifactory, you need to configure OpenShift's Operator Lifecycle Manager (OLM) to treat Artifactory as a private container registry.

In OpenShift, operators are packaged as container images (an index/catalog image, bundle images, and the actual workload operands). Assuming you have already pushed or mirrored your operator images into Artifactory, here is the step-by-step process to install them.

## Step 1: Authenticate OpenShift to Artifactory

OpenShift needs permission to pull the catalog and operator images from Artifactory. You must add your Artifactory credentials to the global cluster pull secret.

1. Create a base64 encoded auth string for your Artifactory credentials:

```bash
echo -n 'username:password' | base64
```

2. Download the current global pull secret:

{% raw %}
```bash
oc get secret/pull-secret -n openshift-config --template='{{index .data ".dockerconfigjson" | base64decode}}' > pull-secret.json
```
{% endraw %}

3. Add your Artifactory credentials to the existing pull secret (this safely merges without overwriting existing registry credentials):

```bash
oc registry login --registry="your-artifactory-domain.com" \
  --auth-basic="username:password" \
  --to=pull-secret.json
```

!!! warning
    Do not manually replace the contents of `pull-secret.json` with only your Artifactory credentials. The file must retain existing entries for `registry.redhat.io`, `quay.io`, and other registries, or cluster image pulls will break.

4. Apply the updated secret back to the cluster:

```bash
oc set data secret/pull-secret -n openshift-config --from-file=.dockerconfigjson=pull-secret.json
```

!!! warning
    Pull-secret updates are applied to nodes by the Machine Config Operator without a drain or reboot. Kubelet picks up the new credentials automatically. The rollout may take a few minutes on larger clusters.

## Step 2: Handle Image Redirection (If Mirrored)

If you used a tool like `oc-mirror` to copy public operators (e.g., from `registry.redhat.io` or `quay.io`) into Artifactory, the internal manifests of those operators still point to their original public URLs.

You must tell OpenShift to redirect those requests to Artifactory by applying an **ImageDigestMirrorSet**.

If you used `oc-mirror`, it will have automatically generated this YAML file for you in its output directory (usually named `imageDigestMirrorSet.yaml`). Older versions of `oc-mirror` may generate the deprecated `imageContentSourcePolicy.yaml` instead — if so, the file still works but consider upgrading `oc-mirror` to get the current `ImageDigestMirrorSet` API. Apply it:

```bash
oc apply -f <path-to-mirror-set-yaml>
```

!!! warning
    Applying an `ImageDigestMirrorSet` or `ImageTagMirrorSet` changes `/etc/containers/registries.conf`, which causes the Machine Config Operator to drain and uncordon each node. Plan a maintenance window for this change. Prefer `ImageDigestMirrorSet` (from `oc-mirror` output); `ImageContentSourcePolicy` is deprecated.

## Step 3: Create the CatalogSource

A `CatalogSource` is the resource that tells OpenShift's OperatorHub where to find the index image for your operators.

1. Create a file named `artifactory-catalog.yaml`:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: artifactory-catalog
  namespace: openshift-marketplace
spec:
  sourceType: grpc
  image: your-artifactory-domain.com/operator-repo/custom-index:v1.0
  displayName: "Artifactory Custom Catalog"
  publisher: "Internal"
  updateStrategy:
    registryPoll:
      interval: 45m
```

2. Apply the configuration:

```bash
oc apply -f artifactory-catalog.yaml
```

3. Verify that the catalog pod is running successfully:

```bash
oc get pods -n openshift-marketplace | grep artifactory-catalog
oc get catalogsource -n openshift-marketplace
```

## Step 4: Install the Operator

Once the `CatalogSource` is running, the operators hosted in Artifactory will appear natively in the OpenShift Web Console.

### Via the Web Console

1. Navigate to **Ecosystem** > **Software Catalog**
2. Filter the sources by your custom `displayName` (e.g., "Artifactory Custom Catalog")
3. Click on the operator you want, select your target namespace, and click **Install**

### Via the CLI

If you prefer infrastructure-as-code, you can install the operator by creating an `OperatorGroup` (to define namespace scope) and a `Subscription` (to trigger the install).

1. Create the `OperatorGroup` in your target namespace:

```yaml
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: my-operator-group
  namespace: my-target-namespace
spec:
  targetNamespaces:
    - my-target-namespace
```

2. Create the `Subscription`:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: my-artifactory-operator
  namespace: my-target-namespace
spec:
  channel: stable
  name: <operator-package-name>
  source: artifactory-catalog
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
```

3. Apply both files:

```bash
oc apply -f operator-group.yaml
oc apply -f subscription.yaml
```
