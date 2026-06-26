# User Provisioned Infrastructure (UPI)

UPI gives you full control over infrastructure provisioning. You create and manage the VMs or bare metal nodes yourself, then provide ignition configs to boot them.

## Steps

1. Generate manifests and ignition configs
2. Provision infrastructure (VMs or bare metal)
3. Boot nodes with ignition configs
4. Wait for bootstrap to complete
5. Remove bootstrap node
6. Approve worker CSRs
7. Wait for installation to finish

```bash
openshift-install create manifests --dir ~/ocp-install
openshift-install create ignition-configs --dir ~/ocp-install
```

Host the ignition files on an HTTP server:

```bash
sudo cp ~/ocp-install/*.ign /var/www/html/
sudo chmod 644 /var/www/html/*.ign
```

Wait for bootstrap:

```bash
openshift-install wait-for bootstrap-complete --dir ~/ocp-install --log-level=info
```

Approve pending CSRs:

```bash
export KUBECONFIG=~/ocp-install/auth/kubeconfig
oc get csr -o go-template='{{range .items}}{{if not .status}}{{.metadata.name}}{{"\n"}}{{end}}{{end}}' | xargs -r oc adm certificate approve
```

Wait for completion:

```bash
openshift-install wait-for install-complete --dir ~/ocp-install --log-level=info
```

---

## Details

### Ignition Configs

The installer generates three ignition files:

| File                  | Target             |
| --------------------- | ------------------ |
| bootstrap.ign         | Bootstrap node     |
| master.ign            | Control plane nodes |
| worker.ign            | Worker nodes       |

These files contain the machine configuration needed to join the cluster. They are valid for 24 hours after generation.

### RHCOS Boot

Download the Red Hat CoreOS (RHCOS) ISO or PXE artifacts:

```bash
RHCOS_URL="https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/latest/"
curl -sL ${RHCOS_URL}rhcos-live.x86_64.iso -o rhcos-live.iso
```

Boot nodes with kernel arguments pointing to the ignition config:

```
coreos.inst.install_dev=/dev/sda
coreos.inst.ignition_url=http://<http-server>/bootstrap.ign
coreos.inst.image_url=http://<http-server>/rhcos-metal.x86_64.raw.gz
```

### CSR Approval

Worker nodes generate Certificate Signing Requests (CSRs) that must be approved before they can join the cluster. Monitor and approve them:

```bash
watch "oc get csr | grep -i pending"
```

### Bootstrap Teardown

After bootstrap completes successfully, remove the bootstrap node from the API load balancer backends and shut down the bootstrap VM.
