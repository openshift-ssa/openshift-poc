# Networking

OpenShift requires specific network configurations and firewall rules between nodes and external services. All node networking uses static IP assignments — there is no DHCP in this environment.

## Network Requirements

| Network         | Purpose                        | CIDR Example  |
| --------------- | ------------------------------ | ------------- |
| Machine Network | Node-to-node communication     | 10.0.0.0/24   |
| Cluster Network | Pod-to-pod communication (SDN) | 10.128.0.0/14 |
| Service Network | Kubernetes service IPs         | 172.30.0.0/16 |

## Static IP Assignments

Since there is no DHCP, every node requires a pre-assigned static IP. Gather the following for each node before installation:

| Field          | Example        |
| -------------- | -------------- |
| IP Address     | 10.0.0.10      |
| Subnet Mask    | 255.255.255.0  |
| Gateway        | 10.0.0.1       |
| Primary DNS    | 10.0.0.2       |
| Secondary DNS  | 1.1.1.1        |
| NIC Interface  | eno1           |
| MAC Address    | aa:bb:cc:dd:ee:00 |

!!! tip
    Document all static IP assignments in a spreadsheet or table before starting installation. The Assisted Installer will require this information for each host.

## Required Firewall Ports

| Port        | Protocol | Source        | Destination   | Purpose                |
| ----------- | -------- | ------------- | ------------- | ---------------------- |
| 6443        | TCP      | All           | Control Plane | Kubernetes API         |
| 22623       | TCP      | Nodes         | Control Plane | Machine Config Server  |
| 2379-2380   | TCP      | Control Plane | Control Plane | etcd                   |
| 10250       | TCP      | All nodes     | All nodes     | Kubelet                |
| 4789        | UDP      | All nodes     | All nodes     | VXLAN (OVN-Kubernetes) |
| 6081        | UDP      | All nodes     | All nodes     | Geneve (OVN-Kubernetes)|
| 9000-9999   | TCP      | All nodes     | All nodes     | Node services          |
| 500         | UDP      | All nodes     | All nodes     | IPsec IKE             |
| 4500        | UDP      | All nodes     | All nodes     | IPsec NAT-T           |
| 30000-32767 | TCP/UDP  | All nodes     | All nodes     | NodePort services      |

## Outbound Access

The following external endpoints must be reachable from all cluster nodes:

| Destination                    | Port | Purpose                       |
| ------------------------------ | ---- | ----------------------------- |
| console.redhat.com             | 443  | Assisted Installer, telemetry |
| quay.io                        | 443  | Container images              |
| registry.redhat.io             | 443  | Red Hat container images      |
| mirror.openshift.com           | 443  | Release images                |
| sso.redhat.com                 | 443  | Authentication                |

```bash
# Verify connectivity from a node to required endpoints
curl -s -o /dev/null -w "%{http_code}" https://console.redhat.com
curl -s -o /dev/null -w "%{http_code}" https://quay.io
curl -s -o /dev/null -w "%{http_code}" https://registry.redhat.io
```

---

## Details

### Machine Network

All cluster nodes must reside on the same Layer 2 network or have Layer 3 routing between them. With static IPs, each node's network configuration is provided during the Assisted Installer setup.

### NTP

All nodes must have synchronized time. Since there is no DHCP to distribute NTP server addresses, ensure chrony is configured with a reachable NTP source:

```bash
sudo dnf install -y chrony
sudo systemctl enable --now chronyd
chronyc tracking
```

### Proxy Configuration

If your environment requires an HTTP proxy for outbound traffic, configure proxy settings in the Assisted Installer UI during cluster creation. Provide:

- HTTP Proxy URL
- HTTPS Proxy URL
- No Proxy list (include machine network, cluster network, service network, and internal domains)

### TLS-Intercepting (MITM) Proxy

Many enterprise environments use a TLS-intercepting proxy (also called a man-in-the-middle or MITM proxy) that terminates and re-encrypts outbound HTTPS traffic for inspection. If your organization does this, OpenShift nodes will receive certificates signed by your proxy's internal CA rather than the original public CA. Without the proxy's root or intermediate certificate in the trust bundle, TLS connections to external services will fail with certificate validation errors.

#### How to Determine if You Have a MITM Proxy

From a machine on the same network as the cluster nodes, inspect the certificate chain for an external endpoint:

```bash
openssl s_client -connect quay.io:443 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -issuer -subject
```

If the **issuer** shows your organization's internal CA (not a public CA like DigiCert, Let's Encrypt, etc.), your traffic is being intercepted by a MITM proxy.

You can also check with curl:

```bash
curl -vI https://registry.redhat.io 2>&1 | grep -i "issuer"
```

#### How to Obtain the Proxy CA Certificate

Contact your network security or infrastructure team and request the root CA certificate (and any intermediate certificates) used by the TLS-intercepting proxy. Common sources:

| Source                    | How to Obtain                                                |
| ------------------------- | ------------------------------------------------------------ |
| Security / Network team   | Request the CA cert directly                                 |
| Corporate PKI portal      | Download from your organization's certificate portal         |
| Browser export            | Visit an HTTPS site, inspect the cert chain, export the root |
| From the proxy itself     | Some proxies publish their CA at a known internal URL         |

You can also extract it directly from the connection:

```bash
openssl s_client -connect quay.io:443 -showcerts </dev/null 2>/dev/null | \
  awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/ {print}' > proxy-ca-chain.pem
```

The last certificate in the chain output is typically the root CA.

#### Required Certificate Format

The certificate must be in **PEM format** (Base64-encoded, with `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----` markers). If you receive the certificate in a different format, convert it:

```bash
# Convert DER to PEM
openssl x509 -in proxy-ca.der -inform DER -out proxy-ca.pem -outform PEM

# Convert PKCS7 to PEM
openssl pkcs7 -in proxy-ca.p7b -inform DER -print_certs -out proxy-ca.pem
```

If there are multiple certificates in the chain (root + intermediate), concatenate them into a single PEM file:

```bash
cat intermediate-ca.pem root-ca.pem > proxy-ca-bundle.pem
```

#### Verify the Certificate

```bash
# Confirm it is a valid CA certificate
openssl x509 -in proxy-ca.pem -noout -text | grep -A1 "Basic Constraints"

# Test that it resolves the trust issue
curl --cacert proxy-ca-bundle.pem https://quay.io
```

#### Providing the Certificate to the Assisted Installer

In the Assisted Installer UI, when configuring proxy settings, paste the contents of your PEM-formatted CA bundle into the **Additional Trust Bundle** field. This ensures all cluster nodes trust the proxy's CA during and after installation.

!!! warning
    If the additional trust bundle is not provided and your environment has a MITM proxy, the installation will fail when nodes attempt to pull container images from Red Hat registries.
