# OpenShift on OpenShift (Hosted Control Planes)

Hosted Control Planes (formerly HyperShift) allows you to run OpenShift control planes as workloads on an existing OpenShift cluster (the "management cluster"). Guest clusters get their own dedicated control plane running in pods, while worker nodes are provisioned separately. This drastically reduces infrastructure overhead and enables faster cluster provisioning.

## Architecture Overview

- **Management cluster** — The existing OpenShift cluster that hosts the control plane pods
- **Hosted cluster** — The guest OpenShift cluster whose API server, etcd, and controllers run as pods on the management cluster
- **NodePool** — Worker nodes that join the hosted cluster (can be bare metal, VMs, or agents)

## Prerequisites

- An existing OpenShift 4.14+ management cluster
- Cluster-admin access on the management cluster
- The `hcp` CLI (Hosted Control Planes CLI)
- A pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
- Sufficient resources on the management cluster (each hosted control plane requires ~4 vCPUs and 16 GiB RAM)

## Install the HyperShift Operator

1. Enable the Hosted Control Planes feature in the `multicluster-engine` operator. If you already have MCE or ACM installed:

  ```bash
  oc patch mce multiclusterengine --type=merge \
    -p '{"spec":{"overrides":{"components":[{"name":"hypershift","enabled":true}]}}}'
  ```

2. Verify the HyperShift operator is running:

  ```bash
  oc get pods -n hypershift
  ```

  You should see the `operator` pod in `Running` state.

## Install the hcp CLI

Download the `hcp` CLI from the management cluster:

```bash
oc extract configmap/hcp-cli-download -n hypershift --to=- > hcp
chmod +x hcp
sudo mv hcp /usr/local/bin/
hcp version
```

Alternatively, download from the [OpenShift mirror](https://mirror.openshift.com/pub/openshift-v4/clients/hcp/).

## Create a Hosted Cluster (Agent-Based Workers)

This approach uses the Agent platform, where workers are provisioned via the Discovery/Infrastructure environment (bare metal or VMs booted with a discovery ISO).

1. Create the hosted cluster:

  ```bash
  hcp create cluster agent \
    --name=hosted-cluster-01 \
    --base-domain=ocp.basedomain.com \
    --pull-secret=/path/to/pull-secret.json \
    --ssh-key=/path/to/ssh-key.pub \
    --agent-namespace=hardware-inventory \
    --api-server-address=api.hosted-cluster-01.ocp.basedomain.com \
    --release-image=quay.io/openshift-release-dev/ocp-release:4.16.0-x86_64 \
    --node-pool-replicas=3
  ```

2. Monitor the hosted cluster rollout:

  ```bash
  oc get hostedcluster -n clusters hosted-cluster-01 -w
  ```

3. Watch the control plane pods come up on the management cluster:

  ```bash
  oc get pods -n clusters-hosted-cluster-01
  ```

## Create a Hosted Cluster (KubeVirt Workers)

If your management cluster has OpenShift Virtualization installed, you can provision workers as VMs directly on the management cluster:

```bash
hcp create cluster kubevirt \
  --name=hosted-cluster-kv \
  --base-domain=ocp.basedomain.com \
  --pull-secret=/path/to/pull-secret.json \
  --ssh-key=/path/to/ssh-key.pub \
  --node-pool-replicas=2 \
  --memory=8Gi \
  --cores=4 \
  --root-volume-size=50 \
  --release-image=quay.io/openshift-release-dev/ocp-release:4.16.0-x86_64
```

This creates KubeVirt VirtualMachines as worker nodes for the hosted cluster.

## Access the Hosted Cluster

1. Retrieve the kubeconfig:

  ```bash
  hcp create kubeconfig --name=hosted-cluster-01 > hosted-cluster-01-kubeconfig
  ```

2. Verify access:

  ```bash
  export KUBECONFIG=hosted-cluster-01-kubeconfig
  oc get nodes
  oc get clusterversion
  oc get clusteroperators
  ```

## DNS Requirements

Create DNS records for the hosted cluster:

| Record | Value |
|--------|-------|
| `api.hosted-cluster-01.ocp.basedomain.com` | Load balancer or IP for the API server service |
| `*.apps.hosted-cluster-01.ocp.basedomain.com` | Load balancer or IP for the ingress service |

Retrieve the service addresses:

```bash
oc get svc -n clusters-hosted-cluster-01 kube-apiserver -o jsonpath='{.status.loadBalancer.ingress[0]}'
oc get svc -n clusters-hosted-cluster-01 router-default -o jsonpath='{.status.loadBalancer.ingress[0]}'
```

## Scaling NodePools

Add or remove workers by scaling the NodePool:

```bash
oc scale nodepool/hosted-cluster-01 -n clusters --replicas=5
```

Or create an additional NodePool with different characteristics:

```yaml
apiVersion: hypershift.openshift.io/v1beta1
kind: NodePool
metadata:
  name: hosted-cluster-01-workers-gpu
  namespace: clusters
spec:
  clusterName: hosted-cluster-01
  replicas: 2
  release:
    image: quay.io/openshift-release-dev/ocp-release:4.16.0-x86_64
  platform:
    type: Agent
```

```bash
oc apply -f nodepool-gpu.yaml
```

## Destroy a Hosted Cluster

```bash
hcp destroy cluster agent --name=hosted-cluster-01
```

This removes the control plane pods and associated resources from the management cluster. Worker nodes will need to be decommissioned separately depending on the platform.

## Documentation

- [Hosted Control Planes](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/hosted_control_planes/index)
- [HyperShift Project](https://hypershift-docs.netlify.app/)
