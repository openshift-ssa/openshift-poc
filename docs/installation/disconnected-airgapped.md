# Disconnected Install: Air-Gapped (Mirror Registry)

[About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring) | [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)

This guide covers installing OpenShift in a fully air-gapped environment where **no system on the cluster network has outbound internet access**. All required container images are pre-staged into a local mirror registry using `oc-mirror` before installation begins.

If your environment has an artifact repository (Artifactory, Nexus) with outbound access that can proxy images on demand, see [Disconnected Install: Pull-Through Cache](disconnected-pull-through.md) instead.

## Architecture

```
Internet ──> Bastion Host ──> Portable Media ──> Mirror Registry ──> Cluster Nodes
              (oc-mirror)       (optional)        (on-site)           (no internet)
```

In some environments, the bastion host has temporary internet access and direct access to the mirror registry, eliminating the need for portable media.

## Prerequisites

- Complete the [prerequisites](../prerequisites/index.md)
- A bastion host with internet access (temporary or permanent) to download content
- A container registry accessible from the cluster network (see [Set Up the Mirror Registry](#set-up-the-mirror-registry))
- At least 200 GB of available disk for the mirror registry storage
- The `oc` CLI transferred to the disconnected installation host

---

## Transfer the oc CLI Across the Airgap

You need the `oc` CLI on the disconnected installation host before you can extract anything. On a workstation with internet access, download `oc` from the [Red Hat mirror site](https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/) and transfer it into the disconnected environment via bastion host, secure file transfer, or physical media.

## Install oc-mirror

Download `oc-mirror` on a host with internet access:

```bash
OCP_VERSION={{ ocp_version }}
wget "https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable-${OCP_VERSION}/oc-mirror.tar.gz" -P /tmp
sudo tar -xvzf /tmp/oc-mirror.tar.gz -C /usr/local/bin
chmod +x /usr/local/bin/oc-mirror
oc-mirror version
```

## Set Up the Mirror Registry

You need a container registry on the disconnected network. Options include:

| Registry                                                                                                                                                                                                                                                       | Notes                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift) | Purpose-built, minimal setup, runs with Podman |
| [Red Hat Quay](https://docs.redhat.com/en/documentation/red_hat_quay)                                                                                                                                                                                           | Full-featured, enterprise-grade                |
| JFrog Artifactory                                                                                                                                                                                                                                              | If already available in-house                  |
| Harbor                                                                                                                                                                                                                                                         | Open-source alternative                        |

To install the mirror registry for Red Hat OpenShift on the installation host:

```bash
wget https://developers.redhat.com/content-gateway/rest/mirror/pub/openshift-v4/clients/mirror-registry/latest/mirror-registry.tar.gz -P /tmp
tar -xvzf /tmp/mirror-registry.tar.gz -C /tmp
sudo /tmp/mirror-registry install --quayHostname {{ mirror_host }} --quayRoot /opt/quay
```

!!! warning
    Ensure `/opt/quay` has at least 200 GB of available disk space. Mirroring an OCP release plus operators can easily exceed 100 GB.

The install command outputs the initial credentials (`init` user and generated password) and generates a self-signed root CA certificate at `/opt/quay/quay-rootCA/rootCA.pem`. Save the credentials — you will need them to log in to the registry.

Add the root CA to the installation host's trust store:

```bash
sudo cp /opt/quay/quay-rootCA/rootCA.pem /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

Verify access:

```bash
podman login {{ mirror_host }}:8443
```

!!! warning
    You will need the contents of `rootCA.pem` later for the `additionalTrustBundle` field in `install-config.yaml`. Without it, cluster nodes will not trust the mirror registry and image pulls will fail.

## Configure Authentication

`oc-mirror` needs credentials for both the source (Red Hat) and destination (mirror) registries. Create a combined pull secret:

```bash
cp ~/pull-secret.txt ~/merged-pull-secret.json

podman login {{ mirror_host }}:8443 --authfile ~/merged-pull-secret.json
```

## Create the ImageSetConfiguration

The `ImageSetConfiguration` defines what content to mirror. Create `imageset-config.yaml`:

```yaml
apiVersion: mirror.openshift.io/v2alpha1
kind: ImageSetConfiguration
storageConfig:
  local:
    path: /tmp/oc-mirror-metadata
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
        - name: openshift-gitops-operator
        - name: cluster-logging
        - name: loki-operator
  additionalImages:
    - name: registry.redhat.io/ubi9/ubi:latest
```

!!! tip
    Only mirror the operators you plan to install. Mirroring the entire catalog is very large (hundreds of GBs) and takes a long time. You can always re-run `oc-mirror` later to add more operators.

## Mirror the Content

=== "Direct (bastion has access to both networks)"

    ```bash
    oc-mirror --config imageset-config.yaml \
      docker://{{ mirror_host }}:8443/openshift \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

=== "Air-Gapped (two-step with portable media)"

    On the internet-connected host, mirror to disk:

    ```bash
    oc-mirror --config imageset-config.yaml \
      file:///mnt/mirror-data \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

    Transfer `/mnt/mirror-data` to the disconnected network, then load into the registry:

    ```bash
    oc-mirror --from file:///mnt/mirror-data \
      docker://{{ mirror_host }}:8443/openshift \
      --authfile ~/merged-pull-secret.json \
      --v2
    ```

`oc-mirror` generates output files in the `oc-mirror-workspace/results-*` directory:

| File                              | Purpose                                         |
| --------------------------------- | ----------------------------------------------- |
| `imageDigestMirrorSet.yaml`     | Tells the cluster where to find mirrored images |
| `catalogSource.yaml`            | Points OLM to the mirrored operator catalog     |
| `updateService.yaml`            | Points the update service to the mirror         |

## Extract the openshift-install Binary

The `openshift-install` binary is embedded inside the release image. Extract it from the mirrored payload:

```bash
oc adm release extract \
  -a ~/merged-pull-secret.json \
  --command=openshift-install \
  {{ mirror_host }}:8443/openshift/release-images:{{ ocp_release }}-x86_64
```

!!! tip
    You can also download the `openshift-install` tarball from the [Red Hat mirror site](https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/) on your connected workstation and transfer it across the airgap. However, using `oc adm release extract` guarantees version alignment with the mirrored payload.

---

## Create install-config.yaml

Create a working directory:

```bash
mkdir -p ocp && cd ocp
```

Create `install-config.yaml` with the full cluster configuration. The `imageDigestSources`, `additionalTrustBundle`, and `pullSecret` fields are required for disconnected operation.

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
  < contents of /opt/quay/quay-rootCA/rootCA.pem >
  -----END CERTIFICATE-----
imageDigestSources:
  - mirrors:
      - {{ mirror_host }}:8443/openshift/release-images
    source: quay.io/openshift-release-dev/ocp-release
  - mirrors:
      - {{ mirror_host }}:8443/openshift/release
    source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
```

!!! warning
    The `imageDigestSources` values must match the repository paths used by `oc-mirror`. Check the generated `imageDigestMirrorSet.yaml` in the `oc-mirror-workspace/results-*` directory for the exact values.

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

For hosts with a single network interface:

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
  {{ mirror_host }}:8443/openshift/release/ubi9/httpd-24:latest
```

!!! note
    In a disconnected environment, you cannot pull from `registry.redhat.io` directly. Use an image already mirrored, or pre-pull `httpd-24` before going offline. Alternatively, use `python3 -m http.server 8080` from the directory containing the ISO.

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

### Apply the Catalog Source

After the cluster is running, apply the generated catalog source so operators can be installed from the mirror:

```bash
export KUBECONFIG=~/ocp/install/auth/kubeconfig
oc apply -f oc-mirror-workspace/results-*/catalogSource.yaml
```

### Disable Default Catalog Sources

The default OperatorHub sources are unreachable in an air-gapped environment:

```bash
oc patch OperatorHub cluster --type json \
  -p '[{"op": "add", "path": "/spec/disableAllDefaultSources", "value": true}]'
```

---

## Verification

### Check Image Mirroring Configuration

```bash
oc get imagedigestmirrorset -o yaml
```

### Verify Node-Level Image Pulls

```bash
oc debug node/{{ worker_node_name }} -- chroot /host \
  podman pull {{ mirror_host }}:8443/openshift/release/ubi9/ubi:latest
```

### Check MachineConfigPool Health

A degraded MCP is a common symptom of mirror misconfiguration:

```bash
oc get mcp
```

All pools should show `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`.

### Verify Pods Are Using Mirrored Images

```bash
oc get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | sort -u | head -20
```

Image references should show your mirror host, not public registries.

### Verify Operator Catalog

```bash
oc get catalogsource -n openshift-marketplace
oc get packagemanifest | head -10
```

---

## Ongoing Maintenance

### Adding New Operators

Re-run `oc-mirror` with an updated `ImageSetConfiguration` to add new operators. The tool handles incremental updates:

```bash
oc-mirror --config imageset-config.yaml \
  docker://{{ mirror_host }}:8443/openshift \
  --authfile ~/merged-pull-secret.json \
  --v2
```

Apply the updated `CatalogSource` if it changed:

```bash
oc apply -f oc-mirror-workspace/results-*/catalogSource.yaml
```

### Upgrading the Cluster

Mirror the new release version before starting the upgrade:

```bash
# Update imageset-config.yaml with the new version range, then:
oc-mirror --config imageset-config.yaml \
  docker://{{ mirror_host }}:8443/openshift \
  --authfile ~/merged-pull-secret.json \
  --v2
```

Apply the updated `ImageDigestMirrorSet` if it changed, then initiate the upgrade:

```bash
oc apply -f oc-mirror-workspace/results-*/imageDigestMirrorSet.yaml
oc adm upgrade
```

---

## Troubleshooting

For common installation issues, see [Troubleshooting](troubleshooting.md).

| Symptom | Likely Cause | Fix |
| ------- | ------------ | --- |
| `ImagePullBackOff` on any pod | Mirror credentials missing from pull secret | Update `pullSecret` in install-config or global pull secret |
| `x509: certificate signed by unknown authority` | CA not in `additionalTrustBundle` | Add the mirror registry CA to the trust bundle |
| CatalogSource pod not starting | Catalog image not mirrored | Re-run `oc-mirror` with the catalog in `ImageSetConfiguration` |
| MachineConfigPool degraded | `imageDigestSources` mismatch | Verify paths match `oc-mirror` output |
| Nodes stuck in `NotReady` | Images not resolvable | Check `imageDigestMirrorSet` and mirror registry availability |

## Documentation

- [About disconnected installation mirroring](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/about-disconnected-installation-mirroring)
- [oc-mirror plugin v2](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2)
- [Mirror registry for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/mirroring-in-disconnected-environments-using-the-oc-mirror-plugin-v2#mirror-registry-for-red-hat-openshift)
- [Updating a cluster in a disconnected environment](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/disconnected_environments/updating-a-cluster-in-a-disconnected-environment)
