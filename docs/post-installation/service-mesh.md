# OpenShift Service Mesh (Ambient Mode)

[Red Hat OpenShift Service Mesh Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_service_mesh/3.3/html/installing/ossm-istio-ambient-mode)

OpenShift Service Mesh 3.x provides Istio ambient mode — a sidecar-less architecture that uses node-level Layer 4 (L4) proxies (ZTunnel) and optional Layer 7 (L7) waypoint proxies. This reduces resource overhead and operational complexity compared to traditional sidecar injection.

## Prerequisites

- OpenShift Container Platform 4.19 or later
- Cluster administrator privileges
- OVN-Kubernetes CNI configured for local gateway mode (see below)

## Install istioctl

`istioctl` is the CLI tool for managing Istio. Install it on the installation host:

```bash
curl -sL https://istio.io/downloadIstioctl | sh -
export PATH=$HOME/.istioctl/bin:$PATH
echo 'export PATH=$HOME/.istioctl/bin:$PATH' >> ~/.bashrc
```

Verify:

```bash
istioctl version
```

## Configure OVN-Kubernetes for Local Gateway Mode

Ambient mode requires OVN-Kubernetes to use local gateway mode. This must be done before installing the mesh.

1. Edit the Cluster Network Operator configuration:

  ```bash
  oc edit network.operator.openshift.io cluster
  ```

2. Set `routingViaHost` to `true` in the `gatewayConfig`:

  ```yaml
  spec:
    defaultNetwork:
      ovnKubernetesConfig:
        gatewayConfig:
          routingViaHost: true
  ```

  !!! warning
      Changing the gateway mode will cause a rolling restart of the OVN-Kubernetes pods across all nodes. Plan for a brief disruption window.

3. Wait for the network operator to reconcile:

  ```bash
  oc get co network -w
  ```

  Wait for `AVAILABLE=True` and `PROGRESSING=False`.

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "OpenShift Service Mesh" -> click the "Red Hat OpenShift Service Mesh" tile (version 3.x)
2. Click Install
3. Select the `stable` channel
4. Leave all other defaults and click Install
5. Wait for the Operator to install

## Install the Operator via YAML

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: servicemeshoperator3
  namespace: openshift-operators
spec:
  channel: stable
  installPlanApproval: Automatic
  name: servicemeshoperator3
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

```bash
oc apply -f servicemesh-operator.yaml
```

Wait for the operator:

```bash
oc get csv -n openshift-operators | grep servicemesh
```

The `PHASE` should show `Succeeded`.

## Deploy Istio Ambient Mode

### Install the Istio Control Plane

1. Create the namespace:

  ```bash
  oc create namespace istio-system
  ```

2. Create the Istio resource:

  ```yaml
  apiVersion: sailoperator.io/v1
  kind: Istio
  metadata:
    name: default
  spec:
    namespace: istio-system
    profile: ambient
    values:
      pilot:
        trustedZtunnelNamespace: ztunnel
  ```

  ```bash
  oc apply -f istio.yaml
  ```

3. Wait for the control plane to be ready:

  ```bash
  oc wait --for=condition=Ready istios/default --timeout=3m
  ```

### Install the Istio CNI

4. Create the namespace:

  ```bash
  oc create namespace istio-cni
  ```

5. Create the IstioCNI resource:

  ```yaml
  apiVersion: sailoperator.io/v1
  kind: IstioCNI
  metadata:
    name: default
  spec:
    namespace: istio-cni
    profile: ambient
  ```

  ```bash
  oc apply -f istio-cni.yaml
  ```

6. Wait for the CNI pods to be ready:

  ```bash
  oc wait --for=condition=Ready istiocni/default --timeout=3m
  ```

### Install the ZTunnel Proxy

7. Create the namespace:

  ```bash
  oc create namespace ztunnel
  ```

  !!! note
      The namespace name must match the `trustedZtunnelNamespace` value in the Istio resource.

8. Create the ZTunnel resource:

  ```yaml
  apiVersion: sailoperator.io/v1alpha1
  kind: ZTunnel
  metadata:
    name: default
  spec:
    namespace: ztunnel
    profile: ambient
  ```

  ```bash
  oc apply -f ztunnel.yaml
  ```

9. Wait for the ZTunnel pods to be ready:

  ```bash
  oc wait --for=condition=Ready ztunnel/default --timeout=3m
  ```

## Verify

```bash
oc get istio
oc get istiocni
oc get ztunnel
oc get pods -n istio-system
oc get pods -n istio-cni
oc get pods -n ztunnel
```

All resources should show `Ready` and all pods should be `Running`.

## Enroll a Namespace in the Mesh

To add a namespace to the ambient mesh, label it:

```bash
oc label namespace {{ namespace }} istio.io/dataplane-mode=ambient
```

All pods in that namespace will automatically have their traffic routed through the ZTunnel proxy with mTLS — no sidecar injection needed.

## Add a Waypoint Proxy (Optional L7 Features)

If you need Layer 7 features (HTTP routing, retries, traffic splitting) for a specific service account or namespace:

```bash
istioctl waypoint apply -n {{ namespace }}
```

Or create it declaratively:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: waypoint
  namespace: {{ namespace }}
  labels:
    istio.io/waypoint-for: service
spec:
  gatewayClassName: istio-waypoint
  listeners:
    - name: mesh
      port: 15008
      protocol: HBONE
```

```bash
oc apply -f waypoint.yaml
```
