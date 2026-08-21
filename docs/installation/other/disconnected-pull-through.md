# Disconnected Install: Pull-Through Cache (Artifactory / Nexus)

This guide covers installing OpenShift in an environment where **cluster nodes have no outbound internet access**, but a centralized artifact repository (JFrog Artifactory, Sonatype Nexus) has outbound access and can proxy images on demand.

If your environment has **zero outbound access** from any system, see [Disconnected Install: Air-Gapped](disconnected-airgapped.md) instead.

## Architecture

```
Upstream Registries ──> Artifactory / Nexus ──> Cluster Nodes
  (quay.io, etc.)       (has outbound access)    (no outbound access)
```

A pull-through cache acts as a transparent proxy. When the cluster requests an image, the cache fetches it from the upstream registry, stores a local copy, and serves it. Subsequent pulls are served from the cache without outbound traffic. This is significantly simpler than a full mirror because you do not need to pre-stage content.

## Prerequisites

- Complete the [prerequisites](../../prerequisites/index.md)
- Artifact repository (Artifactory or Nexus) accessible from all cluster nodes over HTTPS
- Artifact repository has outbound access to:
    - `quay.io` / `cdn.quay.io`
    - `registry.redhat.io`
    - `registry.access.redhat.com`
    - `registry.connect.redhat.com`
- Remote (proxy) repositories configured in the artifact repository for each upstream
- Credentials for the artifact repository
- The CA certificate for the artifact repository (if using an internal CA)
- `oc` and `openshift-install` binaries on the installation host

---

## Configure Remote Repositories

Create remote (proxy) repositories in your artifact manager for each upstream registry.

### JFrog Artifactory

Create **Remote Container Repositories** for each upstream:

| Repository Key               | URL                                     | Notes                                |
| ---------------------------- | --------------------------------------- | ------------------------------------ |
| `quay-remote`              | `https://quay.io`                     | OpenShift release images             |
| `redhat-registry-remote`  | `https://registry.redhat.io`          | Core Red Hat images                  |
| `redhat-access-remote`    | `https://registry.access.redhat.com`  | Legacy Red Hat images (UBI, etc.)    |
| `redhat-connect-remote`   | `https://registry.connect.redhat.com` | Certified partner operators          |

For each remote repository:

1. Go to **Administration > Repositories > Remote**
2. Select **Docker** as the package type
3. Set the **URL** to the upstream registry
4. Enable **Token Authentication** or provide Red Hat pull secret credentials
5. Under **Advanced**, enable **Store Artifacts Locally** (cache)

!!! tip
    Create a **Virtual Repository** (e.g., `container-virtual`) that aggregates all the remote repositories under a single endpoint. This simplifies the cluster configuration.

### Sonatype Nexus

Create **container (proxy)** repositories for each upstream:

1. Go to **Repository > Repositories > Create repository**
2. Select **docker (proxy)**
3. Set the **Remote storage** URL to the upstream registry
4. Under **Container**, assign an HTTPS connector port (e.g., 5000)
5. Configure **Container Bearer Token Realm** in **Security > Realms**
6. Optionally create a **container (group)** repository to aggregate multiple proxy repos

## Configure Authentication

The upstream Red Hat registries require authentication. Configure the pull-through cache with valid credentials from your pull secret.

For Artifactory, add the credentials to each remote repository under **Advanced > Username/Password** or use an access token with the upstream registry.

Create a merged pull secret that includes credentials for both Red Hat and your artifact repository:

```bash
cp ~/pull-secret.txt ~/merged-pull-secret.json

podman login {{ artifactory_host }} --authfile ~/merged-pull-secret.json
```

---

## Pre-Warm the Cache (Recommended)

While a pull-through cache populates on demand, pre-warming avoids slow first pulls during installation. From a host with access to both the internet and the cache:

```bash
oc adm release mirror \
  --from=quay.io/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  --to={{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release \
  --to-release-image={{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  -a ~/merged-pull-secret.json
```

## Validate the Pull-Through Cache

Before generating the ISO, validate that the cache is correctly proxying images. Catching misconfigurations here avoids a failed install.

### Verify TLS Connectivity

```bash
openssl s_client -connect {{ artifactory_host }}:443 -servername {{ artifactory_host }} </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
```

If using a self-signed or internal CA, add it to the installation host's trust store:

```bash
sudo cp /path/to/ca-cert.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

### Verify Registry Authentication

```bash
podman login {{ artifactory_host }}
skopeo login {{ artifactory_host }}
```

### Test Image Pulls Through the Cache

```bash
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64

skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-registry-remote/ubi9/ubi:latest

skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-access-remote/ubi9/ubi:latest
```

### Verify the Release Payload

```bash
oc adm release info \
  --registry-config ~/merged-pull-secret.json \
  {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64
```

This should print release metadata. If it fails, the installer will also fail — resolve the issue before proceeding.

### Verify the Operator Catalog

```bash
skopeo inspect \
  --authfile ~/merged-pull-secret.json \
  docker://{{ artifactory_host }}/redhat-registry-remote/redhat/redhat-operator-index:v{{ ocp_version }}
```

### Check the Cache UI

After running the above commands, verify in the artifact repository UI that content has been cached:

- **Artifactory**: Navigate to **Application > Artifactory > Artifacts**, expand the remote repository, and confirm cached layers are present.
- **Nexus**: Navigate to **Browse > repository name** and verify image layers appear.

---

## Create install-config.yaml

Create a working directory:

```bash
mkdir -p ocp && cd ocp
```

Create `install-config.yaml` with the full cluster configuration including `imageDigestSources` pointing to the pull-through cache:

```yaml
apiVersion: v1
baseDomain: {{ base_domain }}
metadata:
  name: {{ cluster_name }}
controlPlane:
  name: master
  architecture: amd64
  hyperthreading: Enabled
  replicas: 3
compute:
  - name: worker
    architecture: amd64
    hyperthreading: Enabled
    replicas: 3
networking:
  clusterNetwork:
    - cidr: 10.128.0.0/14
      hostPrefix: 23
  machineNetwork:
    - cidr: {{ machine_network_cidr }}
  networkType: OVNKubernetes
  serviceNetwork:
    - 172.30.0.0/16
platform:
  baremetal:
    apiVIPs:
      - {{ api_vip }}
    ingressVIPs:
      - {{ ingress_vip }}
pullSecret: '< contents of ~/merged-pull-secret.json >'
sshKey: '{{ public_key }}'
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  < artifact repository CA certificate >
  -----END CERTIFICATE-----
imageDigestSources:
  - mirrors:
      - {{ artifactory_host }}/quay-remote
    source: quay.io
  - mirrors:
      - {{ artifactory_host }}/quay-remote
    source: cdn.quay.io
  - mirrors:
      - {{ artifactory_host }}/redhat-registry-remote
    source: registry.redhat.io
  - mirrors:
      - {{ artifactory_host }}/redhat-access-remote
    source: registry.access.redhat.com
  - mirrors:
      - {{ artifactory_host }}/redhat-connect-remote
    source: registry.connect.redhat.com
```

!!! note
    Replace mirror paths with the actual repository names in your artifact repository. `cdn.quay.io` must be included — Quay redirects blob downloads to this CDN hostname.

### Compact 3-Node Cluster (No Workers)

For a compact cluster where control plane nodes also run workloads, set `compute[0].replicas` to `0`.

### Proxy Configuration

If your environment requires a proxy, add:

```yaml
proxy:
  httpProxy: http://user:password@proxy.example.com:3128
  httpsProxy: http://user:password@proxy.example.com:3128
  noProxy: .{{ base_domain }},{{ machine_network_cidr }},10.128.0.0/14,172.30.0.0/16,localhost,127.0.0.1,.cluster.local,.svc
```

## Create agent-config.yaml

The `agent-config.yaml` defines host-level configurations. Below is an example with a bonded interface and VLAN:

```yaml
apiVersion: v1beta1
kind: AgentConfig
metadata:
  name: {{ cluster_name }}
rendezvousIP: {{ rendezvous_ip }}
additionalNtpSources:
  - {{ ntp_server_1 }}
  - {{ ntp_server_2 }}
hosts:
  - hostname: {{ cluster_name }}-cp-01
    role: master
    rootDeviceHints:
      deviceName: "/dev/sda"
    interfaces:
      - name: eno1
        macAddress: AA:BB:CC:DD:EE:01
      - name: eno2
        macAddress: AA:BB:CC:DD:EE:02
    networkConfig:
      interfaces:
        - name: bond0
          type: bond
          state: up
          link-aggregation:
            mode: 802.3ad
            port:
              - eno1
              - eno2
            options:
              miimon: "100"
              lacp_rate: fast
          ipv4:
            enabled: false
          ipv6:
            enabled: false
        - name: bond0.{{ vlan_id }}
          type: vlan
          state: up
          vlan:
            base-iface: bond0
            id: {{ vlan_id }}
          ipv4:
            enabled: true
            address:
              - ip: {{ node_ip }}
                prefix-length: {{ prefix_length }}
            dhcp: false
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - {{ dns_server_1 }}
            - {{ dns_server_2 }}
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: {{ gateway }}
            next-hop-interface: bond0.{{ vlan_id }}
            table-id: 254
```

Repeat the host entry for each control plane and worker node, updating hostname, MAC addresses, IP addresses, and role (`master` or `worker`).

### Single NIC (No Bond)

```yaml
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          mac-address: AA:BB:CC:DD:EE:01
          ipv4:
            enabled: true
            address:
              - ip: {{ node_ip }}
                prefix-length: {{ prefix_length }}
            dhcp: false
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - {{ dns_server_1 }}
            - {{ dns_server_2 }}
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: {{ gateway }}
            next-hop-interface: eno1
            table-id: 254
```

## Generate the ISO

!!! warning
    `openshift-install` consumes and deletes `install-config.yaml` and `agent-config.yaml` during image creation. The script below copies them into a subdirectory first so your originals are preserved.

```bash
#!/bin/bash
rm -rf install
mkdir install
cp install-config.yaml agent-config.yaml install
[ -d cluster-manifests ] && cp -r cluster-manifests install
[ -d openshift ] && cp -r openshift install  # only if using extra manifests (e.g. ClusterImagePolicy)
openshift-install agent create image --dir=install --log-level=debug
```

```bash
chmod +x create-iso.sh
./create-iso.sh
```

This generates `install/agent.x86_64.iso`.

## Host the ISO

Serve the ISO from the installation host:

```bash
podman run -d --name iso-http \
  -p 8080:8080 \
  -v ~/ocp/install/agent.x86_64.iso:/var/www/html/agent.x86_64.iso:Z \
  {{ artifactory_host }}/redhat-registry-remote/rhel9/httpd-24:latest
```

Alternatively use Python:

```bash
cd ~/ocp/install && python3 -m http.server 8080
```

Verify the ISO is accessible:

```bash
curl -I http://{{ installation_host }}:8080/agent.x86_64.iso
```

## Boot and Install

Mount the ISO on each node via BMC virtual media (Redfish, iLO, iDRAC) and boot.

!!! warning
    If using the BMC web UI to attach a virtual drive, make a separate copy of the ISO file for each host. If more than one host boots against the same file, BMCs can encounter locking issues.

When all hosts are booted, monitor the install:

```bash
openshift-install agent wait-for bootstrap-complete --dir=install
openshift-install agent wait-for install-complete --dir=install
```

At the end of the process, credentials are available at `install/auth/kubeadmin-password` and `install/auth/kubeconfig`.

---

## Post-Install Configuration

### Disable Default Catalog Sources

The default catalog sources point to `registry.redhat.io` directly. While they will route through the cache via the `ImageDigestMirrorSet`, disabling them and creating explicit ones gives you control:

```bash
export KUBECONFIG=~/ocp/install/auth/kubeconfig

oc patch operatorhub.config.openshift.io/cluster --type=merge \
  -p '{"spec":{"disableAllDefaultSources":true}}'
```

### Create Catalog Sources via the Cache

Create catalog sources that reference operator index images through the pull-through path:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: redhat-operators
  namespace: openshift-marketplace
spec:
  sourceType: grpc
  image: {{ artifactory_host }}/redhat-registry-remote/redhat/redhat-operator-index:v{{ ocp_version }}
  displayName: "Red Hat Operators"
  publisher: "Red Hat (via pull-through cache)"
  updateStrategy:
    registryPoll:
      interval: 60m
```

```bash
oc apply -f catalog-source.yaml
```

Verify:

```bash
oc get pods -n openshift-marketplace
oc get catalogsource -n openshift-marketplace
```

!!! tip
    The first time the catalog pod starts, the cache fetches the index image from upstream. Subsequent pulls are served from cache instantly.

### Install Operators

With the pull-through cache in place, operator installation works exactly like a connected cluster:

1. Navigate to **Operators** > **OperatorHub** in the web console
2. Select and install operators as normal
3. All images are transparently pulled through the cache

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

---

## Image Signature Verification — Optional

!!! tip
    Image signature verification is **optional security hardening**. The cluster installs and operates correctly without it. Add this when you want cryptographic proof that images pulled through the cache are genuinely signed by Red Hat — recommended for production, but not required to get the cluster running.

Red Hat publishes image signatures as **sigstore attachments** stored in the registry alongside the image (as `sha256-<digest>.sig` tags). A pull-through cache can serve these signatures — but only if the cache stores `.sig` tags and CRI-O is configured to look for them.

### Confirm the cache stores `.sig` tags

This is the make-or-break item. When CRI-O verifies a signature, it requests a tag like `sha256-<digest>.sig`. Your remote repository must pass that through and cache it.

Test from a client:

```bash
skopeo list-tags docker://{{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release | grep '\.sig$'
```

If no `.sig` tags come back, verify the remote repository is not filtering tags and can reach the upstream. Nothing downstream works until this does.

!!! note
    If your cache cannot store `.sig` tags, you must fall back to mirroring the detached web sigstore (`https://access.redhat.com/webassets/docker/content/sigstore`) into a location you serve internally and pointing a `registries.d` lookaside at it.

### Apply the ClusterImagePolicy

Get the Red Hat release signing public key and base64-encode it:

```bash
curl -s https://security.access.redhat.com/data/63405576.txt | base64 -w0
```

Apply a policy scoped to the mirror. The `signedIdentity: remapIdentity` is essential — it tells the policy the signature was made for the `quay.io` identity even though the image is pulled from your cache:

```yaml
apiVersion: config.openshift.io/v1
kind: ClusterImagePolicy
metadata:
  name: openshift-release-mirror
spec:
  scopes:
    - {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release
  policy:
    rootOfTrust:
      policyType: PublicKey
      publicKey:
        keyData: <base64-key-from-above>
    signedIdentity:
      matchPolicy: RemapIdentity
      remapIdentity:
        prefix: {{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release
        signedPrefix: quay.io/openshift-release-dev/ocp-release
```

Repeat the scope/remap for each mirrored repository (`ocp-v4.0-art-dev`, `registry.redhat.io/redhat/...` for operators).

!!! warning
    Do not create or edit a `ClusterImagePolicy` named `openshift` — that name is reserved for the built-in release policy.

### Verify signature configuration

The MCO rolls this out to every node. Wait for the MachineConfigPool to finish, then verify:

```bash
oc debug node/<node> -- chroot /host cat /etc/containers/policy.json
oc debug node/<node> -- chroot /host cat /etc/containers/registries.d/sigstore-registries.yaml
```

Confirm the mirror appears with `use-sigstore-attachments: true`.

### Day-1 Integration (Extra Manifest)

You can embed the `ClusterImagePolicy` as a day-1 extra manifest so signature enforcement exists from the moment the cluster comes up.

The `imageDigestSources` in `install-config.yaml` automatically generates the `ImageDigestMirrorSet` — you do not create it manually. You only provide the `ClusterImagePolicy` as an extra manifest.

**Install directory layout:**

```
install/
├── install-config.yaml
├── agent-config.yaml
└── openshift/
    └── 99-cluster-image-policy.yaml
```

Place the `ClusterImagePolicy` YAML (from above) in `openshift/99-cluster-image-policy.yaml` before running `openshift-install agent create image`. The installer embeds it into the ISO's Ignition config, and the Assisted Service applies it during bootstrap.

!!! note "Bootstrap timing"
    The `ClusterImagePolicy` is applied by the MCO once the cluster API is up. The initial release payload pull during bootstrap is governed by the bootstrap node's own `policy.json` (seeded from the pull secret and mirror config), not by your CIP. The extra-manifest CIP governs the running cluster — day-2 pulls, operator images, and upgrades.

---

## Cluster Upgrades

With the `ImageDigestMirrorSet` in place, cluster upgrades pull release images through the cache automatically:

```bash
oc adm upgrade
```

The cluster checks the update graph and pulls the release image via the configured mirror. The cache stores the release image on first pull.

If the cluster cannot reach the update graph service (Cincinnati), specify the release image directly:

```bash
oc adm upgrade --to-image={{ artifactory_host }}/quay-remote/openshift-release-dev/ocp-release:{{ ocp_release }}-x86_64 \
  --allow-explicit-upgrade
```

---

## Verification

### Confirm Images Route Through the Cache

```bash
oc get events --all-namespaces --field-selector reason=Pulled | tail -10
```

Image references in events should show your cache hostname.

### Check MachineConfigPool Health

```bash
oc get mcp
```

All pools should show `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`.

### Verify Pods Are Using Cached Images

```bash
oc get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u | head -20
```

### Test a Manual Pull

```bash
oc run test --image={{ artifactory_host }}/redhat-registry-remote/ubi9/ubi:latest \
  --rm -it --restart=Never -- echo "Pull-through cache is working"
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
| ------- | ------------ | --- |
| `ImagePullBackOff` on any pod | Pull secret missing cache creds | Update global pull secret |
| `x509: certificate signed by unknown authority` | CA not trusted by nodes | Check `additionalTrustedCA` ConfigMap key matches hostname |
| CatalogSource pod not starting | Index image path incorrect | Verify remote repo name in image path |
| Image pulls slow on first request | Expected — cache is fetching from upstream | Subsequent pulls will be fast |
| `unauthorized: authentication required` | Credentials incorrect or expired | Regenerate and reapply pull secret |
| Operator shows available but install hangs | Bundle images routing to wrong remote repo | Add missing source to `ImageDigestMirrorSet` |
| Upgrade shows no available versions | Cincinnati service unreachable | Use `--to-image` with explicit release image |
| Nodes not restarting after mirror set change | MachineConfigPool paused | Check `oc get mcp` for paused pools |

For common installation issues, see [Troubleshooting](../troubleshooting.md).

## Documentation

- [About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring)
- [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)
- [Updating a cluster in a disconnected environment](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/updating-a-cluster-in-a-disconnected-environment)
