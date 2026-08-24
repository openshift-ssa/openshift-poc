# Bookinfo (Service Mesh Demo)

[Istio Bookinfo Sample](https://istio.io/latest/docs/examples/bookinfo/)

!!! note "Out of POC baseline"
    This demo requires [OpenShift Service Mesh](../post-installation/service-mesh.md). Skip it unless mesh is explicitly in scope.

Bookinfo is the standard Istio sample application — a multi-service app that displays information about a book. It consists of four microservices that communicate over HTTP, making it ideal for demonstrating service mesh capabilities like mTLS, traffic management, and observability.

## Prerequisites

- [OpenShift Service Mesh](../post-installation/service-mesh.md) installed and ambient mode configured

## Architecture

```
Browser ──> productpage (Python) ──> details (Ruby)
                                 ──> reviews (Java) ──> ratings (Node.js)
```

The `reviews` service has three versions:

| Version | Behavior |
| --- | --- |
| v1 | No star ratings |
| v2 | Black star ratings (calls `ratings` service) |
| v3 | Red star ratings (calls `ratings` service) |

This multi-version setup is what makes Bookinfo useful for traffic management demos.

## Deploy the Application

1. Create and label the namespace for the mesh:

  ```bash
  oc new-project bookinfo
  oc label namespace bookinfo istio.io/dataplane-mode=ambient
  ```

2. Deploy a waypoint proxy. Ambient ZTunnel is L4 only — HTTPRoute traffic splitting requires a waypoint:

  ```yaml
  apiVersion: gateway.networking.k8s.io/v1
  kind: Gateway
  metadata:
    name: waypoint
    namespace: bookinfo
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
  oc label namespace bookinfo istio.io/use-waypoint=waypoint
  ```

3. Deploy the Bookinfo application:

  ```bash
  oc apply -n bookinfo \
    -f https://raw.githubusercontent.com/istio/istio/master/samples/bookinfo/platform/kube/bookinfo.yaml
  ```

4. Wait for all pods to be running:

  ```bash
  oc get pods -n bookinfo -w
  ```

  You should see pods for `productpage`, `details`, `reviews-v1`, `reviews-v2`, `reviews-v3`, and `ratings`.

5. Verify the app works internally:

  ```bash
  oc exec deploy/productpage-v1 -n bookinfo \
    -- curl -s productpage:9080/productpage | grep -o "<title>.*</title>"
  ```

  Expected: `<title>Simple Bookstore App</title>`

## Expose the Application

Create a Gateway and HTTPRoute to make the application accessible externally:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: bookinfo
spec:
  gatewayClassName: istio
  listeners:
    - name: http
      port: 80
      protocol: HTTP
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: bookinfo
  namespace: bookinfo
spec:
  parentRefs:
    - name: bookinfo-gateway
  rules:
    - matches:
        - path:
            type: Exact
            value: /productpage
        - path:
            type: PathPrefix
            value: /static
        - path:
            type: Exact
            value: /login
        - path:
            type: Exact
            value: /logout
        - path:
            type: PathPrefix
            value: /api/v1/products
      backendRefs:
        - name: productpage
          port: 9080
```

```bash
oc apply -f bookinfo-gateway.yaml
```

Get the application URL:

```bash
GATEWAY_HOST=$(oc get gateway bookinfo-gateway -n bookinfo -o jsonpath='{.status.addresses[0].value}')
echo "Application available at: http://$GATEWAY_HOST/productpage"
```

Open the URL in a browser. Refresh the page multiple times — you should see the reviews section alternate between no stars (v1), black stars (v2), and red stars (v3) as traffic round-robins across the three versions.

## Demonstrate Traffic Management

Traffic splitting requires per-version Services. The default Bookinfo deployment creates only the `reviews` Service. Create version-specific Services:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: bookinfo
spec:
  selector:
    app: reviews
    version: v1
  ports:
    - port: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v3
  namespace: bookinfo
spec:
  selector:
    app: reviews
    version: v3
  ports:
    - port: 9080
```

```bash
oc apply -f reviews-version-services.yaml
```

### Route All Traffic to v1

Send all traffic to `reviews` v1 (no stars):

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews
  namespace: bookinfo
spec:
  parentRefs:
    - group: ""
      kind: Service
      name: reviews
      port: 9080
  rules:
    - backendRefs:
        - name: reviews-v1
          port: 9080
```

```bash
oc apply -f reviews-v1-route.yaml
```

Refresh the product page — you should now only see reviews without stars.

### Shift Traffic to v3

Gradually shift traffic to v3 (red stars) with a 50/50 split:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews
  namespace: bookinfo
spec:
  parentRefs:
    - group: ""
      kind: Service
      name: reviews
      port: 9080
  rules:
    - backendRefs:
        - name: reviews-v1
          port: 9080
          weight: 50
        - name: reviews-v3
          port: 9080
          weight: 50
```

```bash
oc apply -f reviews-split.yaml
```

Refresh the product page repeatedly — you should see roughly half the requests show no stars (v1) and half show red stars (v3).

### Route 100% to v3

Complete the cutover:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews
  namespace: bookinfo
spec:
  parentRefs:
    - group: ""
      kind: Service
      name: reviews
      port: 9080
  rules:
    - backendRefs:
        - name: reviews-v3
          port: 9080
```

```bash
oc apply -f reviews-v3-route.yaml
```

## Demonstrate mTLS

With ambient mode, mTLS is automatic. Verify that traffic between services is encrypted:

```bash
oc get pods -n istio-system -l app=ztunnel -o wide
oc logs -n istio-system -l app=ztunnel --tail=50 | grep HBONE
```

The log output should show `HBONE` connections, indicating traffic is flowing through the encrypted ZTunnel. You can also use `istioctl` if installed (see [Service Mesh — Install istioctl](../post-installation/service-mesh.md#install-istioctl)):

```bash
istioctl ztunnel-config workloads -n istio-system
```

## What to Show in a Demo

- **Ambient mesh enrollment** — a single namespace label adds the mesh with no sidecar injection
- **Automatic mTLS** — all service-to-service traffic is encrypted without any application changes
- **Traffic splitting** — canary deployments and gradual rollouts using HTTPRoute weights
- **Multi-version routing** — route different users or percentages to different service versions
- **Zero application changes** — the Bookinfo app has no mesh-specific code

## Cleanup

```bash
oc delete project bookinfo
```
