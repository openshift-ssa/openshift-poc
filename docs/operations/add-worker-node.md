# Adding a Worker Node

[Official Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/nodes/working-with-nodes#adding-node-iso)

## Prerequisites

- OpenShift CLI (`oc`) installed
- Rsync utility installed
- Active connection to the target cluster with a kubeconfig file
- A valid pull secret (for fetching the release image matching the cluster version)
- MAC address of each new node's primary NIC
- Network configuration details (IP, gateway, DNS) for static IP deployments

## Create the Configuration File

Create a file named `nodes-config.yaml`. This is similar to the `agent-config.yaml` used during installation. You must provide a MAC address for each new node.

### Simple Example (Single NIC, Static IP)

```yaml
hosts:
  - hostname: extra-worker-1
    rootDeviceHints:
      deviceName: /dev/sda
    interfaces:
      - macAddress: 00:00:00:00:00:00
        name: eth0
    networkConfig:
      interfaces:
        - name: eth0
          type: ethernet
          state: up
          mac-address: 00:00:00:00:00:00
          ipv4:
            enabled: true
            address:
              - ip: 192.168.122.2
                prefix-length: 23
            dhcp: false
      dns-resolver:
        config:
          server:
            - 192.168.122.1
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 192.168.122.1
            next-hop-interface: eth0
            table-id: 254
```

### Bonded Example

```yaml
hosts:
  - hostname: extra-worker-1
    rootDeviceHints:
      deviceName: /dev/sda
    interfaces:
      - macAddress: A0:B1:C2:D3:E4:F1
        name: eno1
      - macAddress: A0:B1:C2:D3:E4:F2
        name: eno2
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          mac-address: A0:B1:C2:D3:E4:F1
          ipv4:
            enabled: false
          ipv6:
            enabled: false
        - name: eno2
          type: ethernet
          state: up
          mac-address: A0:B1:C2:D3:E4:F2
          ipv4:
            enabled: false
          ipv6:
            enabled: false
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
            enabled: true
            address:
              - ip: 10.0.0.10
                prefix-length: 28
            dhcp: false
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - dns1.basedomain.com
            - dns2.basedomain.com
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: bond0
            table-id: 254
```

### DHCP Example (Minimal)

When using DHCP, the network configuration can be omitted entirely — only the MAC address is required:

```yaml
hosts:
  - hostname: extra-worker-1
    rootDeviceHints:
      deviceName: /dev/sda
    interfaces:
      - macAddress: 00:00:00:00:00:00
        name: eth0
```

## Generate the ISO Image

Run the following command from the directory containing `nodes-config.yaml`:

```bash
oc adm node-image create --registry-config=~/pull-secret.txt
```

If `nodes-config.yaml` is in a different directory, use `--dir`:

```bash
oc adm node-image create --dir=/path/to/config --registry-config=~/pull-secret.txt
```

!!! note
    The pull secret is required for the `create` command to fetch a release image that matches the target cluster version. You can also set the `REGISTRY_AUTH_FILE` environment variable instead of using `--registry-config`.

Verify that a `node.<name>.iso` file was generated in the working directory (or the directory specified by `--dir`):

```bash
ls *.iso
```

## Boot the Node

Boot the node using the generated ISO image. Common methods:

- **BMC virtual media** — Mount the ISO via the server's BMC/iLO/iDRAC interface
- **Physical media** — Write the ISO to a USB drive
- **PXE** — Use `--pxe` flag during creation to generate PXE assets instead of an ISO

## Monitor Progress

Track the node joining the cluster:

```bash
oc adm node-image monitor --ip-addresses <ip_addresses>
```

Where `<ip_addresses>` is a comma-separated list of the new node IP addresses.

!!! note
    If reverse DNS entries are not available for your node, the monitor command skips checks for pending CSRs. In that case, check for CSRs manually.

## Approve Pending CSRs

New nodes require certificate signing request (CSR) approval. There are typically two rounds — one for the kubelet client certificate and one for the kubelet serving certificate.

Check for pending CSRs:

```bash
oc get csr | grep Pending
```

Approve all pending CSRs:

{% raw %}
```bash
oc get csr -o go-template='{{range .items}}{{if not .status}}{{.metadata.name}}{{"\n"}}{{end}}{{end}}' | xargs oc adm certificate approve
```
{% endraw %}

!!! warning
    Wait a minute and check again — the second CSR (serving certificate) appears only after the first one is approved.

```bash
oc get csr | grep Pending
```

Approve any additional pending CSRs with the same command.

## Verify

Confirm the node has joined the cluster and is Ready:

```bash
oc get nodes
```

The new node should appear with `STATUS=Ready` and `ROLES=worker`.

## Troubleshooting

### ISO Boot Fails or Node Does Not Appear

- Verify the MAC address in `nodes-config.yaml` matches the actual NIC
- Confirm the node can reach the API server (check gateway, DNS, and firewall rules)
- Check that `rootDeviceHints.deviceName` matches an actual disk on the node (`lsblk`)

### CSRs Never Appear

- The node may not have booted successfully — check console output via BMC
- Network misconfiguration may prevent the kubelet from reaching the API server
- Verify DNS resolution for the cluster's API endpoint from the new node's network

### Node Joins but Shows NotReady

- Check node conditions: `oc describe node <node_name>`
- Common causes: missing CNI plugin sync, clock skew, or resource pressure
