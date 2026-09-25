# Network Policy and Microsegmentation

[OpenShift Network Policy Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/network_security/about-network-policy) · [Multi-Network Policy Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/multiple_networks/secondary-networks)

This page explains how OpenShift isolates workload traffic with Kubernetes `NetworkPolicy` (pod network) and `MultiNetworkPolicy` (secondary / additional networks), then walks through microsegmentation examples for container apps and OpenShift Virtualization VMs.

Secondary underlays (OVS bridges, CUDNs, NADs) are covered in [Networking](./networking.md). To observe allowed and denied flows after policies are in place, see [Network Observability](./network-observability.md).

## Concepts

### Default connectivity

Without any policies, pods in a project can reach other pods and network endpoints in the cluster. The first `NetworkPolicy` (or `MultiNetworkPolicy`) that selects a pod switches that pod to an allow-list model: only traffic permitted by **at least one** matching policy is accepted. Pods that no policy selects remain fully open.

Policies are **additive**. Two policies that select the same pods combine — a connection is allowed if either policy permits it. There is no "deny" rule type; you deny by omitting an allow.

OpenShift's own DNS and Ingress namespaces ship deny-by-default policies maintained by their operators. Do not delete or loosen those; do not run unmanaged pods in those namespaces.

### NetworkPolicy vs MultiNetworkPolicy

| Aspect                    | NetworkPolicy                                              | MultiNetworkPolicy                                                              |
| ------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------- |
| API                       | `networking.k8s.io/v1`                                     | `k8s.cni.cncf.io/v1beta1`                                                       |
| CLI resource              | `networkpolicy` / `netpol`                                 | `multi-networkpolicy`                                                           |
| Applies to                | Default / primary pod network                              | Secondary networks only (NAD-backed)                                            |
| Target network            | Implicit (cluster network)                                 | Explicit via `k8s.v1.cni.cncf.io/policy-for: <ns>/<nad>` annotation              |
| Enabled by default        | Yes (OVN-Kubernetes)                                       | No — set `spec.useMultiNetworkPolicy: true` on the cluster `Network` CR         |
| Typical use               | Container microsegmentation on the pod network             | VM and multi-homed pod traffic on localnet / macvlan / SR-IOV / OVN secondary   |

`MultiNetworkPolicy` implements the same rule shape as `NetworkPolicy` (`podSelector`, `ingress` / `egress`, `ipBlock`, ports), but it **cannot** manage the default cluster network or the primary network of a user-defined network (UDN). Use `NetworkPolicy` for those.

Supported secondary network types for multi-network policy include OVN-Kubernetes secondary networks, MacVLAN, IPVLAN, SR-IOV (kernel NICs only — not DPDK), and Bond CNI over SR-IOV.

### Selectors and OVN secondary networks

For OVN-Kubernetes secondary networks, which peer types you can use depends on whether the network defines `subnets` (OVN-managed IPAM):

| Secondary network has `subnets` | Valid peers                         |
| ------------------------------- | ----------------------------------- |
| Yes                             | `podSelector`, `namespaceSelector`, `ipBlock` |
| No                              | `ipBlock` only                      |

OpenShift Virtualization workloads on secondary networks must use **`ipBlock`** peers. Pod and namespace selectors are not supported for virtualization on those networks, and IPAM-based peers can block live migration when IPAM is disabled (the common VM localnet pattern). Label the VM's `spec.template.metadata` so the policy's `podSelector` matches the virt-launcher pod; use `ipBlock` for who may talk to it.

### Microsegmentation model

A practical pattern for both containers and VMs:

1. **Default deny** — empty `ingress: []` (and optionally empty `egress: []`) selecting the workloads you want to isolate
2. **Allow same namespace** — reopen east-west traffic inside the project if needed
3. **Allow specific peers** — frontend → API → database, or client CIDR → VM tier, by label or `ipBlock`
4. **Allow platform ingress** — OpenShift Ingress / router so Routes and Services still work (container pod network)
5. **Allow DNS / API** — egress to cluster DNS and the Kubernetes API when you also deny egress by default

## Enable MultiNetworkPolicy

Required before any `MultiNetworkPolicy` examples. Skip this section if you only need pod-network `NetworkPolicy`.

```bash
oc patch network.operator.openshift.io cluster --type=merge \
  -p '{"spec":{"useMultiNetworkPolicy":true}}'
```

Verify:

```bash
oc get network.operator.openshift.io cluster -o jsonpath='{.spec.useMultiNetworkPolicy}{"\n"}'
```

Expect `true`. The Cluster Network Operator deploys the multi-network policy controller (nftables backend on current OpenShift releases).

## Prerequisites for the examples

| Example set                         | Needs                                                                                          |
| ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| Container NetworkPolicy             | OVN-Kubernetes (default); a project you can create policies in                                 |
| VM MultiNetworkPolicy               | MultiNetworkPolicy enabled; secondary NAD / [CUDN](./networking.md#clusteruserdefinednetwork); [OpenShift Virtualization](./virtualization.md) |

Replace placeholders such as `{{ ns }}`, `{{ nad_name }}`, and CIDRs with values from your environment.

---

## Container workloads — NetworkPolicy microsegmentation

These examples use the default pod network. Create them in the application namespace.

### Scenario

Three tiers in one project:

| Role        | Label              | Port |
| ----------- | ------------------ | ---- |
| Frontend    | `app=shop`, `tier=frontend` | 8080 |
| API         | `app=shop`, `tier=api`      | 8080 |
| Database    | `app=shop`, `tier=db`       | 5432 |

Goal: external clients reach only the frontend (via Ingress); frontend talks to API; API talks to database; nothing else east-west.

### 1. Default deny ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: {{ ns }}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress: []
```

```bash
oc apply -f default-deny-ingress.yaml
```

Empty `podSelector: {}` selects every pod in the namespace. After this, all ingress is blocked until the allow policies below are applied.

### 2. Allow traffic from the OpenShift Ingress router

Routes and the Ingress controller need to reach frontend pods:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-openshift-ingress
  namespace: {{ ns }}
spec:
  podSelector:
    matchLabels:
      app: shop
      tier: frontend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              policy-group.network.openshift.io/ingress: ""
```

```bash
oc apply -f allow-from-openshift-ingress.yaml
```

The `policy-group.network.openshift.io/ingress: ""` label is the OVN-Kubernetes-supported way to select Ingress / router namespaces.

### 3. Frontend → API

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-from-frontend
  namespace: {{ ns }}
spec:
  podSelector:
    matchLabels:
      app: shop
      tier: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: shop
              tier: frontend
      ports:
        - protocol: TCP
          port: 8080
```

```bash
oc apply -f allow-api-from-frontend.yaml
```

### 4. API → database

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-db-from-api
  namespace: {{ ns }}
spec:
  podSelector:
    matchLabels:
      app: shop
      tier: db
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: shop
              tier: api
      ports:
        - protocol: TCP
          port: 5432
```

```bash
oc apply -f allow-db-from-api.yaml
```

### 5. Optional — default deny egress with DNS and API allow

Tighten outbound traffic so pods cannot scan the cluster or reach arbitrary destinations:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: {{ ns }}
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: {{ ns }}
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: openshift-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-server-egress
  namespace: {{ ns }}
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              policy-group.network.openshift.io/host-network: ""
      ports:
        - protocol: TCP
          port: 6443
```

```bash
oc apply -f egress-policies.yaml
```

Add further egress rules (for example API → database is same-namespace pod traffic and may still need an explicit egress allow if you deny all egress — include a same-namespace egress rule or port-specific rules for each tier).

### 6. Optional — allow same-namespace traffic

If you prefer a coarser project-level isolation (all pods in the project may talk; other projects cannot):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: {{ ns }}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector: {}
```

Use this **instead of** the tier-to-tier rules when you only need namespace boundaries, not per-tier microsegmentation.

### Verify container policies

```bash
oc get networkpolicy -n {{ ns }}
oc describe networkpolicy allow-db-from-api -n {{ ns }}
```

From a frontend pod, API and (via API) database paths should work; a scratch pod without the frontend label should not reach the API or database.

---

## Virtual machine workloads — MultiNetworkPolicy microsegmentation

VMs that attach only to the default pod network can be selected by ordinary `NetworkPolicy` (the policy matches the virt-launcher pod). When VMs use a **secondary** network (localnet CUDN, OVN L2 overlay, macvlan, and so on) — the usual pattern for routable or L2-adjacent VM traffic — segment them with `MultiNetworkPolicy` and `ipBlock` peers.

### Scenario

Two VMs on the same secondary network (`{{ nad_namespace }}/{{ nad_name }}`), for example a CUDN created in [Networking](./networking.md#clusteruserdefinednetwork):

| VM           | Template labels              | Secondary IP (example) |
| ------------ | ---------------------------- | ---------------------- |
| Web tier     | `app: shop-vm`, `tier: web`  | `10.4.0.10`            |
| Database VM  | `app: shop-vm`, `tier: db`   | `10.4.0.20`            |

Clients on the secondary subnet (`10.4.0.0/24`) should reach the web VM on TCP/80. Only the web VM should reach the database VM on TCP/5432. Everything else on that secondary network is denied.

### Label the VirtualMachines

`MultiNetworkPolicy` `podSelector` matches labels on the **virt-launcher pod**, which inherit from `spec.template.metadata.labels`:

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: shop-web
  namespace: {{ ns }}
spec:
  runStrategy: Always
  template:
    metadata:
      labels:
        app: shop-vm
        tier: web
    spec:
      domain:
        devices:
          interfaces:
            - name: secondary
              bridge: {}
          disks:
            - name: rootdisk
              disk:
                bus: virtio
        resources:
          requests:
            memory: 2Gi
      networks:
        - name: secondary
          multus:
            networkName: {{ nad_namespace }}/{{ nad_name }}
      volumes:
        - name: rootdisk
          containerDisk:
            image: quay.io/containerdisks/rhel:9
# ... remaining VM spec (cloud-init, storage, etc.)
```

Use the same pattern for `shop-db` with `tier: db`. Ensure the NAD / CUDN already exists and the VMs receive IPs on the secondary interface (OVN IPAM, DHCP, or static guest config).

### 1. Default deny on the secondary network

```yaml
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: deny-by-default
  namespace: {{ ns }}
  annotations:
    k8s.v1.cni.cncf.io/policy-for: {{ nad_namespace }}/{{ nad_name }}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress: []
```

```bash
oc apply -f mnp-deny-by-default.yaml
```

The `policy-for` annotation must match the NAD that the VMs attach to (`namespace/name`). After this policy, no ingress is accepted on that secondary interface for pods/VMs in this namespace until allow rules are added.

### 2. Allow client subnet → web VM (HTTP)

```yaml
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: allow-web-from-clients
  namespace: {{ ns }}
  annotations:
    k8s.v1.cni.cncf.io/policy-for: {{ nad_namespace }}/{{ nad_name }}
spec:
  podSelector:
    matchLabels:
      app: shop-vm
      tier: web
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 10.4.0.0/24
      ports:
        - protocol: TCP
          port: 80
```

```bash
oc apply -f mnp-allow-web-from-clients.yaml
```

Adjust the CIDR to your secondary subnet (or a narrower client range). Exclude addresses you never want as sources with `except` if needed:

```yaml
        - ipBlock:
            cidr: 10.4.0.0/24
            except:
              - 10.4.0.20/32
```

### 3. Allow web VM → database VM (PostgreSQL)

Because virtualization policies require `ipBlock`, pin the allowed source to the web VM's secondary IP:

```yaml
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: allow-db-from-web
  namespace: {{ ns }}
  annotations:
    k8s.v1.cni.cncf.io/policy-for: {{ nad_namespace }}/{{ nad_name }}
spec:
  podSelector:
    matchLabels:
      app: shop-vm
      tier: db
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 10.4.0.10/32
      ports:
        - protocol: TCP
          port: 5432
```

```bash
oc apply -f mnp-allow-db-from-web.yaml
```

Prefer **persistent** secondary IPs (CUDN with `ipam.lifecycle: Persistent`, or static guest addressing) so `/32` rules survive VM restarts and live migration.

### 4. Optional — restrict egress from the database VM

```yaml
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: db-egress-deny-except-dns
  namespace: {{ ns }}
  annotations:
    k8s.v1.cni.cncf.io/policy-for: {{ nad_namespace }}/{{ nad_name }}
spec:
  podSelector:
    matchLabels:
      app: shop-vm
      tier: db
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 10.4.0.1/32
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

```bash
oc apply -f mnp-db-egress.yaml
```

Replace `10.4.0.1` with the gateway or DNS reachable on that secondary segment. An empty `egress: []` with `policyTypes: [Egress]` is a full egress deny for that secondary interface.

### 5. Optional — allow only a management jump host to SSH

```yaml
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: allow-ssh-from-bastion
  namespace: {{ ns }}
  annotations:
    k8s.v1.cni.cncf.io/policy-for: {{ nad_namespace }}/{{ nad_name }}
spec:
  podSelector:
    matchLabels:
      app: shop-vm
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 10.4.0.5/32
      ports:
        - protocol: TCP
          port: 22
```

```bash
oc apply -f mnp-allow-ssh-from-bastion.yaml
```

### Verify VM policies

```bash
oc get multi-networkpolicy -n {{ ns }}
oc describe multi-networkpolicy allow-db-from-web -n {{ ns }}
```

From a host or VM on `10.4.0.0/24`:

- HTTP to `10.4.0.10:80` should succeed
- Direct TCP to `10.4.0.20:5432` from a client that is not `10.4.0.10` should fail
- From the web VM, PostgreSQL to `10.4.0.20:5432` should succeed

Use [Network Observability](./network-observability.md) if you need flow-level confirmation of drops and allows on the secondary interface.

## Quick reference

| Goal                                      | Resource             | Key fields                                                                 |
| ----------------------------------------- | -------------------- | -------------------------------------------------------------------------- |
| Isolate pods on the cluster network       | `NetworkPolicy`      | `podSelector`, `namespaceSelector`, ports                                  |
| Isolate VMs / pods on a secondary NAD     | `MultiNetworkPolicy` | `k8s.v1.cni.cncf.io/policy-for`, `ipBlock` (required for Virt)             |
| Turn on multi-network policy              | `Network` CR         | `spec.useMultiNetworkPolicy: true`                                         |
| Select a VM                               | labels on VM template | `spec.template.metadata.labels` → matched by policy `podSelector`         |
| Stable VM IP for `/32` rules              | CUDN IPAM            | `ipam.mode: Enabled`, `lifecycle: Persistent` — see [Networking](./networking.md) |

## Related pages

- [Networking](./networking.md) — NNCP, OVS bridges, CUDN / NAD underlay for secondary networks
- [OpenShift Virtualization](./virtualization.md) — install and attach VMs to secondary networks
- [Network Observability](./network-observability.md) — visualize policy-affected flows
- [Service Mesh](./service-mesh.md) — L4/L7 identity-based controls when mesh is in scope (complements, does not replace, NetworkPolicy)
