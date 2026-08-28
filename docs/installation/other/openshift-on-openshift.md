# OpenShift on OpenShift (Hosted Control Planes)

Hosted Control Planes (formerly HyperShift) runs OpenShift control planes as workloads on an existing OpenShift cluster (the **management cluster**). Guest clusters get a dedicated control plane in pods; worker nodes are provisioned separately.

!!! warning "Not a first-day install path"
    This page assumes you already have a management cluster with [Multicluster Engine (MCE) or Advanced Cluster Management (ACM)](hub-and-spoke.md#install-advanced-cluster-management) installed. Do not start here if you are installing the first cluster — use the [Assisted Installer](../assisted-installer.md) or [Agent-Based Installer](../agent-based.md) instead.

## Architecture Overview

- **Management cluster** — The existing OpenShift cluster that hosts the control plane pods
- **Hosted cluster** — The guest OpenShift cluster whose API server, etcd, and controllers run as pods on the management cluster
- **NodePool** — Worker nodes that join the hosted cluster

## Prerequisites

- A running management cluster with cluster-admin access
- [MCE or ACM](hub-and-spoke.md#install-advanced-cluster-management) installed on the management cluster
- A pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
- DNS for the hosted cluster API and ingress (see [DNS Requirements](#dns-requirements))
- Capacity on the management cluster: about **5.5 vCPU and 19 GiB RAM per hosted control plane**, plus worker capacity for the guest cluster

## Enable Hosted Control Planes

1. Enable the HyperShift component in MCE:

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

Download `hcp` from the management cluster web console (**? → Command Line Tools → hcp**), or resolve the download URL:

```bash
oc get consoleclidownload hcp-cli-download -o jsonpath='{.spec.links[0].href}{"\n"}'
```

Extract the binary, put it on your `PATH`, and confirm:

```bash
chmod +x hcp
sudo mv hcp /usr/local/bin/
hcp version
```

Alternatively, download from the [OpenShift mirror](https://mirror.openshift.com/pub/openshift-v4/clients/hcp/).

!!! note
    Do not use `oc extract configmap/hcp-cli-download`. That ConfigMap is not a reliable source for the 4.22 CLI.

## Create a Hosted Cluster (KubeVirt workers)

This is the complete, supported path when the management cluster has [OpenShift Virtualization](../../post-installation/virtualization.md). Workers are VMs on the management cluster.

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
  --release-image=quay.io/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
```

Monitor rollout:

```bash
oc get hostedcluster -n clusters hosted-cluster-kv -w
oc get pods -n clusters-hosted-cluster-kv
```

## Create a Hosted Cluster (Agent-based workers)

The Agent platform is for bare metal or VMs booted with a discovery ISO. `--agent-namespace` is not enough by itself: you must also create an **InfraEnv**, register hosts (BareMetalHosts or discovery ISO), and approve agents before the NodePool can scale.

See [Provisioning a bare metal spoke cluster](hub-and-spoke.md#provision-a-bare-metal-spoke-cluster) and the [Hosted Control Planes documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/hosted_control_planes/index) for InfraEnv and agent inventory.

Once agents are available in the hardware inventory namespace:

```bash
hcp create cluster agent \
  --name=hosted-cluster-01 \
  --base-domain=ocp.basedomain.com \
  --pull-secret=/path/to/pull-secret.json \
  --ssh-key=/path/to/ssh-key.pub \
  --agent-namespace=hardware-inventory \
  --api-server-address=api.hosted-cluster-01.ocp.basedomain.com \
  --release-image=quay.io/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  --node-pool-replicas=3
```

!!! note
    Configure the DNS records in [DNS Requirements](#dns-requirements) before creating the cluster. The `--api-server-address` value must resolve before API server certificates are generated.

## Access the Hosted Cluster

1. Retrieve the kubeconfig:

  ```bash
  hcp create kubeconfig --name=hosted-cluster-kv --namespace=clusters > hosted-cluster-kv-kubeconfig
  ```

2. Verify access:

  ```bash
  export KUBECONFIG=hosted-cluster-kv-kubeconfig
  oc get nodes
  oc get clusterversion
  oc get clusteroperators
  ```

## DNS Requirements

Create DNS records for the hosted cluster:

| Record                                        | Value                                          |
| --------------------------------------------- | ---------------------------------------------- |
| `api.hosted-cluster-kv.ocp.basedomain.com`    | Load balancer or IP for the API server service |
| `*.apps.hosted-cluster-kv.ocp.basedomain.com` | Load balancer or IP for the ingress service    |

Retrieve the service addresses:

```bash
oc get svc -n clusters-hosted-cluster-kv kube-apiserver -o jsonpath='{.status.loadBalancer.ingress[0]}'
oc get svc -n clusters-hosted-cluster-kv router-default -o jsonpath='{.status.loadBalancer.ingress[0]}'
```

## Scaling NodePools

Add or remove workers by scaling the NodePool:

```bash
oc scale nodepool/hosted-cluster-kv -n clusters --replicas=5
```

Or create an additional NodePool with different characteristics:

```yaml
apiVersion: hypershift.openshift.io/v1beta1
kind: NodePool
metadata:
  name: hosted-cluster-kv-workers-gpu
  namespace: clusters
spec:
  clusterName: hosted-cluster-kv
  replicas: 2
  release:
    image: quay.io/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
  platform:
    type: KubeVirt
```

```bash
oc apply -f nodepool-gpu.yaml
```

## Destroy a Hosted Cluster

```bash
hcp destroy cluster kubevirt --name=hosted-cluster-kv
```

This removes the control plane pods and associated resources from the management cluster. Worker nodes need to be decommissioned separately depending on the platform.

## Documentation

- [Hosted Control Planes](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/hosted_control_planes/index)
- [HyperShift Project](https://hypershift-docs.netlify.app/)
