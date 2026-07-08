# VMware vSphere IPI Installation

[Installing on VMware vSphere Official Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/installing_on_vmware_vsphere/installer-provisioned-infrastructure)

This guide covers installing a standalone OpenShift cluster on VMware vSphere using Installer-Provisioned Infrastructure (IPI). With IPI, the installer provisions VMs, disks, and networking directly in vSphere — no manual VM creation is required.

You should have completed the [prerequisites](../prerequisites/index.md) and have that information handy.

## Prerequisites

- VMware vSphere 8.0 Update 1 or later, VMware vSphere Foundation 9, or VMware Cloud Foundation 5.0 or later
- vCenter access on port 443 from the installation host
- A vCenter account with [required privileges](#vcenter-account-privileges)
- DNS records configured for API and Ingress VIPs
- Static IP addresses planned for all cluster nodes (bootstrap, control plane, workers)
- Pull secret saved to `~/pull-secret.txt`
- SSH key generated at `~/.ssh/ocp`

## vCenter Account Privileges

The vCenter account used by the installer requires a broad set of privileges. Red Hat recommends using the full privilege set rather than a minimal custom role.

!!! warning
    Red Hat does not support custom roles with restricted privilege sets. The full list below is tested and required both during and after installation. Reducing privileges after installation can cause unexpected cluster behavior.

### vSphere vCenter

Required always:

```
Cns.Searchable
InventoryService.Tagging.AttachTag
InventoryService.Tagging.CreateCategory
InventoryService.Tagging.CreateTag
InventoryService.Tagging.DeleteCategory
InventoryService.Tagging.DeleteTag
InventoryService.Tagging.EditCategory
InventoryService.Tagging.EditTag
Sessions.ValidateSession
StorageProfile.Update
StorageProfile.View
```

### vSphere vCenter Cluster

Required always:

```
Host.Config.Storage
Resource.AssignVMToPool
VApp.AssignResourcePool
VApp.Import
VirtualMachine.Config.AddNewDisk
```

### vSphere vCenter Resource Pool

Required if providing an existing resource pool:

```
Resource.AssignVMToPool
VApp.AssignResourcePool
VApp.Import
VirtualMachine.Config.AddNewDisk
```

### vSphere Datastore

Required always:

```
Datastore.AllocateSpace
Datastore.Browse
Datastore.FileManagement
InventoryService.Tagging.ObjectAttachable
```

### vSphere Port Group

Required always:

```
Network.Assign
```

### Virtual Machine Folder

Required always:

```
InventoryService.Tagging.ObjectAttachable
Resource.AssignVMToPool
VApp.Import
VirtualMachine.Config.AddExistingDisk
VirtualMachine.Config.AddNewDisk
VirtualMachine.Config.AddRemoveDevice
VirtualMachine.Config.AdvancedConfig
VirtualMachine.Config.Annotation
VirtualMachine.Config.CPUCount
VirtualMachine.Config.DiskExtend
VirtualMachine.Config.DiskLease
VirtualMachine.Config.EditDevice
VirtualMachine.Config.Memory
VirtualMachine.Config.RemoveDisk
VirtualMachine.Config.Rename
VirtualMachine.Config.ResetGuestInfo
VirtualMachine.Config.Resource
VirtualMachine.Config.Settings
VirtualMachine.Config.UpgradeVirtualHardware
VirtualMachine.Interact.GuestControl
VirtualMachine.Interact.PowerOff
VirtualMachine.Interact.PowerOn
VirtualMachine.Interact.Reset
VirtualMachine.Inventory.Create
VirtualMachine.Inventory.CreateFromExisting
VirtualMachine.Inventory.Delete
VirtualMachine.Provisioning.Clone
VirtualMachine.Provisioning.MarkAsTemplate
VirtualMachine.Provisioning.DeployTemplate
Host.Config.Storage
```

### vSphere vCenter Datacenter

Required when the installation program creates the virtual machine folder (default behavior). Includes all privileges from [Virtual Machine Folder](#virtual-machine-folder) above, plus:

```
Folder.Create
Folder.Delete
```

### Propagation Settings

| vSphere Object          | When Required                       | Propagate to Children |
| ----------------------- | ----------------------------------- | --------------------- |
| vSphere vCenter         | Always                              | No                    |
| vCenter Datacenter      | Existing folder                     | No (ReadOnly)         |
| vCenter Datacenter      | Installation program creates folder | Yes                   |
| vCenter Cluster         | Always                              | Yes                   |
| vSphere Datastore       | Always                              | No                    |
| vSphere Switch          | Always                              | No (ReadOnly)         |
| vSphere Port Group      | Always                              | No                    |
| vCenter VM Folder       | Existing folder                     | Yes                   |
| vCenter Resource Pool   | Existing resource pool              | Yes                   |

!!! tip
    Create a dedicated vCenter service account for OpenShift rather than using an admin account. This makes auditing and credential rotation easier.

For the complete privilege reference, see the [official documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/installing_on_vmware_vsphere/installer-provisioned-infrastructure#installation-vsphere-installer-infra-requirements_ipi-vsphere-ipi).

## Add vCenter Root CA Certificates to System Trust

The installer needs to communicate with the vCenter API over TLS. You must add the vCenter CA certificates to the installation host's trust store.

1. Download the root CA certificates from vCenter:

    Navigate to `https://{{ vcenter_fqdn }}` and click **Download trusted root CA certificates** in the vSphere Web Services SDK section. This downloads a `download.zip` file.

2. Extract the certificates:

    ```bash
    unzip download.zip -d vcenter-certs
    ```

3. Copy the Linux certificates to the system trust:

    ```bash
    sudo cp vcenter-certs/certs/lin/* /etc/pki/ca-trust/source/anchors/
    ```

4. Update the system trust:

    ```bash
    sudo update-ca-trust extract
    ```

5. Verify connectivity:

    ```bash
    curl -s https://{{ vcenter_fqdn }} > /dev/null && echo "TLS OK" || echo "TLS FAILED"
    ```

## Download the Installer

6. Download `openshift-install` from the [Red Hat Console](https://console.redhat.com/openshift/downloads):

    ```bash
    tar xvf openshift-install-linux.tar.gz
    chmod +x openshift-install
    sudo mv openshift-install /usr/local/bin/
    ```

7. Verify:

    ```bash
    openshift-install version
    ```

## Create the Installation Directory

8. Create a working directory for the installation artifacts:

    ```bash
    mkdir ~/ocp-vsphere && cd ~/ocp-vsphere
    ```

## Generate install-config.yaml

You can generate the `install-config.yaml` interactively or create it manually.

### Interactive Method

9. Run the installer and follow the prompts:

    ```bash
    openshift-install create install-config --dir ~/ocp-vsphere
    ```

    The installer will prompt for:
    - SSH public key
    - Platform (`vsphere`)
    - vCenter server, username, and password
    - Datacenter, cluster, datastore, and network
    - API and Ingress VIPs
    - Base domain and cluster name
    - Pull secret

### Manual Method

10. Create `~/ocp-vsphere/install-config.yaml` with the following content:

    ```yaml
    apiVersion: v1
    baseDomain: {{ base_domain }}
    metadata:
      name: {{ cluster_name }}
    sshKey: |
      {{ public_key }}
    pullSecret: '{{ pull_secret }}'
    compute:
      - name: worker
        platform:
          vsphere:
            cpus: 8
            coresPerSocket: 4
            memoryMB: 32768
            osDisk:
              diskSizeGB: 120
        replicas: 3
    controlPlane:
      name: master
      platform:
        vsphere:
          cpus: 8
          coresPerSocket: 4
          memoryMB: 32768
          osDisk:
            diskSizeGB: 120
      replicas: 3
    networking:
      clusterNetwork:
        - cidr: 10.128.0.0/14
          hostPrefix: 23
      serviceNetwork:
        - 172.30.0.0/16
      machineNetwork:
        - cidr: 10.0.0.0/28
    platform:
      vsphere:
        apiVIPs:
          - {{ api_vip }}
        ingressVIPs:
          - {{ ingress_vip }}
        vcenters:
          - server: {{ vcenter_fqdn }}
            user: {{ vcenter_username }}
            password: {{ vcenter_password }}
            datacenters:
              - {{ datacenter_name }}
        failureDomains:
          - name: {{ failure_domain_name }}
            region: {{ region_name }}
            zone: {{ zone_name }}
            server: {{ vcenter_fqdn }}
            topology:
              datacenter: {{ datacenter_name }}
              computeCluster: "/{{ datacenter_name }}/host/{{ cluster_name }}"
              datastore: "/{{ datacenter_name }}/datastore/{{ datastore_name }}"
              networks:
                - {{ vm_network_name }}
              resourcePool: "/{{ datacenter_name }}/host/{{ cluster_name }}/Resources"
    ```

!!! warning "Back up install-config.yaml"
    The installation process consumes and deletes `install-config.yaml`. Always make a backup before running the installer:

    ```bash
    cp ~/ocp-vsphere/install-config.yaml ~/ocp-vsphere/install-config.yaml.bak
    ```

## Configure Static IP Addresses

For environments without DHCP (which is our assumption), configure static IPs using the `platform.vsphere.hosts` parameter.

11. Add the `hosts` section under `platform.vsphere` in your `install-config.yaml`:

    ```yaml
    platform:
      vsphere:
        # ... (vcenters, failureDomains, VIPs from above)
        hosts:
          - role: bootstrap
            networkDevice:
              ipAddrs:
                - 10.0.0.5/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
          - role: control-plane
            networkDevice:
              ipAddrs:
                - 10.0.0.6/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
          - role: control-plane
            networkDevice:
              ipAddrs:
                - 10.0.0.7/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
          - role: control-plane
            networkDevice:
              ipAddrs:
                - 10.0.0.8/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
          - role: compute
            networkDevice:
              ipAddrs:
                - 10.0.0.9/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
          - role: compute
            networkDevice:
              ipAddrs:
                - 10.0.0.10/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
          - role: compute
            networkDevice:
              ipAddrs:
                - 10.0.0.11/28
              gateway: 10.0.0.1
              nameservers:
                - {{ nameserver_ip }}
    ```

    Valid `role` values are `bootstrap`, `control-plane`, and `compute`. The number of entries must match the total node count (1 bootstrap + 3 control plane + 3 workers = 7).

## Proxy Configuration (Optional)

If your environment uses a proxy, add the proxy settings to `install-config.yaml`:

12. Add the proxy and trust bundle:

    ```yaml
    proxy:
      httpProxy: http://{{ proxy_host }}:{{ proxy_port }}
      httpsProxy: http://{{ proxy_host }}:{{ proxy_port }}
      noProxy: "{{ base_domain }},{{ machine_network_cidr }},{{ vcenter_fqdn }},10.128.0.0/14,172.30.0.0/16"
    additionalTrustBundle: |
      -----BEGIN CERTIFICATE-----
      {{ ca_certificate }}
      -----END CERTIFICATE-----
    ```

    !!! note
        Always include the vCenter FQDN and machine network in `noProxy` to prevent the installer from trying to proxy vSphere API calls.

## Deploy the Cluster

13. Back up your `install-config.yaml`:

    ```bash
    cp ~/ocp-vsphere/install-config.yaml ~/ocp-vsphere/install-config.yaml.bak
    ```

14. Start the installation:

    ```bash
    openshift-install create cluster --dir ~/ocp-vsphere --log-level=info
    ```

    !!! info "What happens during installation"
        The installer:

        1. Creates a temporary bootstrap VM in vSphere
        2. Provisions 3 control plane VMs
        3. Provisions 3 worker VMs
        4. Configures networking and storage on each VM
        5. Bootstraps the cluster (etcd, API server, etc.)
        6. Destroys the bootstrap VM once the control plane is self-hosting
        7. Completes cluster operator installation

        The full process takes approximately 45-60 minutes.

15. If the installation times out, you can resume monitoring:

    ```bash
    openshift-install wait-for install-complete --dir ~/ocp-vsphere --log-level=info
    ```

## Access the Cluster

16. Upon successful completion, the installer outputs the `kubeadmin` credentials and the console URL:

    ```
    INFO Install complete!
    INFO To access the cluster as the system:admin user when using 'oc', run 'export KUBECONFIG=/home/user/ocp-vsphere/auth/kubeconfig'
    INFO Access the OpenShift web-console here: https://console-openshift-console.apps.{{ cluster_name }}.{{ base_domain }}
    INFO Login to the console with user: "kubeadmin", and password: "XXXXX-XXXXX-XXXXX-XXXXX"
    ```

17. Export the kubeconfig:

    ```bash
    export KUBECONFIG=~/ocp-vsphere/auth/kubeconfig
    ```

18. Verify cluster health:

    ```bash
    oc get nodes
    oc get clusterversion
    oc get co
    ```

    All nodes should show `Ready` and all cluster operators should show `Available=True`.

## Validate vSphere Integration

19. Confirm that the vSphere CSI driver is operational:

    ```bash
    oc get pods -n openshift-cluster-csi-drivers -l app=vsphere-csi-driver
    oc get storageclass
    ```

    You should see a `thin-csi` StorageClass provided by the vSphere CSI driver.

20. Test dynamic provisioning:

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: test-vsphere-pvc
      namespace: default
    spec:
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi
      storageClassName: thin-csi
    ```

    ```bash
    oc apply -f test-pvc.yaml
    oc get pvc test-vsphere-pvc -w
    ```

    The PVC should transition to `Bound` within a minute.

21. Clean up the test PVC:

    ```bash
    oc delete pvc test-vsphere-pvc
    ```

## Destroy the Cluster

To remove the cluster and all vSphere resources it created:

```bash
openshift-install destroy cluster --dir ~/ocp-vsphere --log-level=info
```

!!! warning
    This permanently deletes all VMs, disks, folders, and tags created by the installer. This action cannot be undone.
