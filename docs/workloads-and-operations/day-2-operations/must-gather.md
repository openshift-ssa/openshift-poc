# must-gather

[Red Hat must-gather Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/support/gathering-cluster-data)

`oc adm must-gather` collects cluster-wide diagnostic data for troubleshooting and Red Hat support cases. It captures logs, resource definitions, and configuration from cluster components into a local archive. Running a must-gather is the first step when opening a support case.

## Basic must-gather

Collect the default cluster diagnostics:

```bash
oc adm must-gather
```

This creates a directory named `must-gather.local.<id>` in your current working directory. The collection takes 5–15 minutes depending on cluster size.

!!! tip
    Run must-gather from the [installation host](../../prerequisites/installation-host.md) where `oc` is configured with cluster-admin credentials.

## What It Collects

The default must-gather captures:

| Category | Examples |
|----------|----------|
| Cluster resources | Nodes, ClusterOperators, ClusterVersion, MachineConfigPools |
| Namespaced resources | Pods, Services, Deployments, ConfigMaps, Secrets (metadata only) |
| Operator logs | Logs from all operator pods |
| Node logs | Journal logs from each node |
| etcd health | etcd member list and endpoint health |
| Network config | OVN/OVS state, network policies |
| Events | Cluster-wide events |

## Operator-Specific must-gather

Operators ship their own must-gather images that collect deeper diagnostics for their components. Use `--image` to run them:

!!! tip "Pin the image version to your installed operator"
    Prefer a version tag that matches the installed operator (for example `v4.17`) instead of `:latest`. Resolve the image from the cluster when possible:

    ```bash
    oc get csv -A -o custom-columns=NAME:.metadata.name,IMAGE:.spec.relatedImages[*].image | grep must-gather
    ```

### OpenShift Virtualization

```bash
oc adm must-gather --image=registry.redhat.io/container-native-virtualization/cnv-must-gather-rhel9:v4.17
```

### OpenShift Data Foundation

```bash
oc adm must-gather --image=registry.redhat.io/odf4/odf-must-gather-rhel9:v4.17
```

### OpenShift Logging

```bash
oc adm must-gather --image=registry.redhat.io/openshift-logging/cluster-logging-rhel9-operator:v6.6 -- /usr/bin/gather
```

### Advanced Cluster Management

```bash
oc adm must-gather --image=registry.redhat.io/rhacm2/acm-must-gather-rhel9:v2.12
```

### Network Observability

```bash
oc adm must-gather --image=registry.redhat.io/network-observability/network-observability-must-gather-rhel9:v1.8
```

### Multiple Operators at Once

Combine multiple images in a single run:

```bash
oc adm must-gather \
  --image=registry.redhat.io/container-native-virtualization/cnv-must-gather-rhel9:v4.17 \
  --image=registry.redhat.io/odf4/odf-must-gather-rhel9:v4.17
```

## Scoped Collection

### Specific Namespace

Limit collection to a single namespace:

```bash
oc adm must-gather -- /usr/bin/gather --namespace={{ namespace }}
```

### Since a Specific Time

Collect logs only from the last N minutes:

```bash
oc adm must-gather -- /usr/bin/gather --since=30m
```

## Create the Archive

The must-gather output is a directory. Compress it for upload:

```bash
tar czf must-gather-$(date +%Y%m%d-%H%M%S).tar.gz must-gather.local.*/
```

## Upload to Red Hat Support

1. Open or find your support case at [access.redhat.com](https://access.redhat.com/support/cases/)
2. Attach the `.tar.gz` archive to the case
3. If the file is too large (>250 MB), use the Red Hat SFTP dropbox documented in your support case. Typical flow:

  ```bash
  sftp <case-number>@sftp.access.redhat.com
  # password is provided in the case comment / SFTP instructions from Support
  put must-gather-*.tar.gz
  ```

  Reference the file name in your support case comments. Do not use a generic `must-gather@` account unless Support has directed you to.

## Troubleshooting must-gather

| Symptom | Cause | Fix |
|---------|-------|-----|
| `must-gather` pod stuck in Pending | No node has capacity for the gather pod | Free resources or specify a node: `--node-name=<node>` |
| Collection times out | Large cluster or slow storage | Increase timeout: `--timeout=30m` |
| Permission denied | Not running as cluster-admin | Switch to an admin kubeconfig: `export KUBECONFIG=...` |
| Operator-specific image pull fails | Disconnected cluster without the image mirrored | Mirror the must-gather image first, then use the mirrored path |
