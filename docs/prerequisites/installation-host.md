# Building the Installation Host

The installation host serves multiple purposes. All install work is done here. It is used to validate the environment prior to installation and provides tools for generating the ISO images.

The installation host can be a bare metal or virtualized host and only requires what is needed for a normal Red Hat Enterprise Linux install. We recommend at least 4 CPU, 16 GB memory, and 100 GB disk. It should be on the same network as the targeted hosts for the OpenShift cluster install so it can be used to validate the firewall is open prior to installation.

## Install the OS

1. Download [Red Hat Enterprise Linux 9.x Binary DVD](https://developers.redhat.com/products/rhel/download)
2. Boot host from ISO and perform install as Server with GUI
3. Enable SSH for the newly created user and make them an administrator
4. Reboot and SSH into the installation host

## Register the Host

```bash
sudo subscription-manager register
sudo subscription-manager repos --enable=rhel-9-for-x86_64-baseos-rpms
sudo subscription-manager repos --enable=rhel-9-for-x86_64-appstream-rpms
sudo dnf update -y
sudo reboot
```

## Download Required Tools

```bash
OCP_VERSION=4.21
wget "https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable-${OCP_VERSION}/openshift-install-linux.tar.gz" -P /tmp
sudo tar -xvzf /tmp/openshift-install-linux.tar.gz -C /usr/local/bin
wget "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable-${OCP_VERSION}/openshift-client-linux.tar.gz" -P /tmp
sudo tar -xvzf /tmp/openshift-client-linux.tar.gz -C /usr/local/bin
rm -f /tmp/openshift-install-linux.tar.gz /tmp/openshift-client-linux.tar.gz
sudo dnf install -y nmstate git podman
```

Verify the tools are installed:

```bash
openshift-install version
oc version
nmstatectl -V
git -v
podman --version
```

## Download the Pull Secret

Download the pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret) and save it:

```bash
# Save the pull secret file to your home directory
chmod 600 ~/pull-secret.txt
```

## Create an SSH Key

An SSH key is required to access the OpenShift hosts for debugging and is required as part of the install.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/ocp
```

## Open Port 8080 for ISO Hosting

The web interfaces for BMCs can sometimes be flaky when uploading ISOs for boot. Serve the ISO from an HTTP host using Podman.

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## Firewall Checks

### Inter-Node Firewall Ports

The following ports must be open between cluster nodes:

| Port        | Protocol | Source        | Destination   | Purpose                 |
| ----------- | -------- | ------------- | ------------- | ----------------------- |
| 6443        | TCP      | All           | Control Plane | Kubernetes API          |
| 22623       | TCP      | Nodes         | Control Plane | Machine Config Server   |
| 2379-2380   | TCP      | Control Plane | Control Plane | etcd                    |
| 10250       | TCP      | All nodes     | All nodes     | Kubelet                 |
| 4789        | UDP      | All nodes     | All nodes     | VXLAN (OVN-Kubernetes)  |
| 6081        | UDP      | All nodes     | All nodes     | Geneve (OVN-Kubernetes) |
| 9000-9999   | TCP      | All nodes     | All nodes     | Node services           |
| 500         | UDP      | All nodes     | All nodes     | IPsec IKE              |
| 4500        | UDP      | All nodes     | All nodes     | IPsec NAT-T            |
| 30000-32767 | TCP/UDP  | All nodes     | All nodes     | NodePort services       |

To verify ports are not blocked between hosts, start a temporary listener on the target host and connect from the source host:

```bash
# On the target host - start a listener on port 6443
nc -l 6443
```

```bash
# On the source host - test connectivity to the target
nc -zv {{ target_ip }} 6443
```

If the connection succeeds, no firewall is blocking that port between the two hosts. Repeat for critical ports (6443, 22623, 2379, 10250) across all node pairs.

### Outbound Access

You will need outbound access to the following for pulling OpenShift container images and tools.

**Container Registries**

```
registry.redhat.io
access.redhat.com
quay.io
cdn.quay.io
cdn01.quay.io
cdn02.quay.io
cdn03.quay.io
cdn04.quay.io
cdn05.quay.io
cdn06.quay.io
sso.redhat.com
```

**Cluster Access, Authentication, and Updates**

```
api.openshift.com
console.redhat.com
sso.redhat.com
```

**Installation and Release Artifacts**

```
mirror.openshift.com
quayio-production-s3.s3.amazonaws.com
rhcos.mirror.openshift.com
storage.googleapis.com/openshift-release
```

**Telemetry (if not disabled)**

```
cert-api.access.redhat.com
api.access.redhat.com
infogw.api.openshift.com
```

**Optional**

```
registry.connect.redhat.com
```

### Connectivity Checks

```bash
for domain in registry.redhat.io access.redhat.com quay.io cdn.quay.io cdn01.quay.io cdn02.quay.io cdn03.quay.io cdn04.quay.io cdn05.quay.io cdn06.quay.io sso.redhat.com api.openshift.com console.redhat.com mirror.openshift.com quayio-production-s3.s3.amazonaws.com rhcos.mirror.openshift.com cert-api.access.redhat.com api.access.redhat.com infogw.api.openshift.com; do
  nc -zv -w 2 $domain 443 2>&1 | grep -iqE "connected|succeeded|open" && echo "$domain: SUCCESS" || echo "$domain: FAILED"
done
```

You can also login with your Red Hat account using podman:

```bash
podman login registry.redhat.io
```

---

## Details

### Environment Validation Tools

Make sure you can validate connectivity:

```bash
curl -vk https://registry.redhat.io/v2/
dig registry.redhat.io +short
nslookup registry.redhat.io
podman login registry.redhat.io
```

### Company Image Considerations

If using a company RHEL image, ensure any processes that may interfere with web hosting or the other install processes are turned off.
