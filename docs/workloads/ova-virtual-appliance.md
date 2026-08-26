# Deploying Virtual Appliances (OVA)

Many commercial and open-source products ship as **OVA (Open Virtual Appliance)** files — a single archive that bundles one or more virtual disks with an OVF descriptor. This guide shows how to import an OVA into OpenShift Virtualization so you can run virtual appliances alongside containers on OpenShift.

## How It Works

An `.ova` file is a TAR archive containing:

| File | Purpose |
|------|---------|
| `*.ovf` | XML descriptor with VM hardware settings (CPU, memory, NICs, disks) |
| `*.vmdk` / `*.vhd` | Virtual disk image(s) |
| `*.mf` | Optional manifest with checksums |

OpenShift Virtualization uses KubeVirt and the Containerized Data Importer (CDI). CDI can import **raw** and **qcow2** images directly, so the workflow is:

1. Extract the OVA and locate the virtual disk
2. Convert the disk to qcow2 (if it is VMDK or another format)
3. Upload the converted image into a PersistentVolumeClaim (PVC)
4. Create a VirtualMachine that references the PVC

## Prerequisites

- OpenShift Virtualization installed and healthy
- A default virtualization StorageClass with **RWX** support
- `oc` and `virtctl` installed locally
- `qemu-img` installed locally (provided by the `qemu-img` package on RHEL/Fedora)
- The OVA file downloaded to your workstation

Verify `qemu-img` is available:

```bash
qemu-img --version
```

## Create a Project

```bash
oc new-project ova-appliance
```

## Extract the OVA

An OVA is a standard TAR archive. Extract it into a working directory:

```bash
mkdir appliance && cd appliance
tar xf /path/to/appliance.ova
```

List the extracted files to identify the disk image and the OVF descriptor:

```bash
ls -lh *.ovf *.vmdk *.vhd 2>/dev/null
```

!!! tip
    Review the `.ovf` file for the recommended CPU count, memory, and network adapter type. You will use these values when creating the VirtualMachine.

## Convert the Disk Image

CDI requires a **raw** or **qcow2** image. Convert the VMDK (or VHD) to qcow2:

```bash
qemu-img convert -f vmdk -O qcow2 appliance-disk.vmdk appliance-disk.qcow2
```

Verify the output image:

```bash
qemu-img info appliance-disk.qcow2
```

!!! note
    If the OVA already contains a `.qcow2` or `.img` (raw) file, you can skip the conversion step and upload it directly.

## Upload the Disk Image

Use `virtctl image-upload` to push the qcow2 file into a new PVC managed by CDI:

```bash
virtctl image-upload dv appliance-rootdisk \
  --size=60Gi \
  --image-path=appliance-disk.qcow2 \
  --storage-class=<your-storage-class> \
  --access-mode=ReadWriteMany \
  --namespace=ova-appliance \
  --insecure
```

!!! warning
    Adjust `--size` to be at least as large as the **virtual size** reported by `qemu-img info`. The `--insecure` flag skips TLS verification for the CDI upload proxy — omit it if your cluster has a trusted certificate.

Monitor the upload and import:

```bash
oc get dv appliance-rootdisk -n ova-appliance -w
```

Wait until the DataVolume phase shows **Succeeded**.

## Create the VirtualMachine

Build a VirtualMachine manifest that references the uploaded PVC. Tailor the CPU, memory, and firmware settings to match the appliance's requirements from the OVF.

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: appliance
  namespace: ova-appliance
spec:
  running: true
  template:
    spec:
      domain:
        cpu:
          cores: 2
        resources:
          requests:
            memory: 4Gi
        devices:
          disks:
            - name: rootdisk
              disk:
                bus: virtio
          interfaces:
            - name: default
              masquerade: {}
        firmware:
          bootloader:
            bios: {}
      networks:
        - name: default
          pod: {}
      volumes:
        - name: rootdisk
          persistentVolumeClaim:
            claimName: appliance-rootdisk
```

```bash
oc apply -f appliance-vm.yaml
```

!!! tip "UEFI appliances"
    Some appliances require UEFI boot. Replace the `firmware` section with:

    ```yaml
    firmware:
      bootloader:
        efi:
          secureBoot: false
    ```

!!! tip "Non-virtio disk bus"
    Appliances that lack virtio drivers (e.g. Windows-based or older Linux images) may need `bus: sata` or `bus: scsi` instead of `bus: virtio`.

Wait for the VM to reach Running:

```bash
oc get vmi appliance -n ova-appliance -w
```

## Verify the Appliance

### Console Access

```bash
virtctl console appliance -n ova-appliance
```

Many appliances present a setup wizard or login prompt on the serial console. If the appliance uses a graphical interface, use VNC instead:

```bash
virtctl vnc appliance -n ova-appliance
```

### Guest Agent and IP Address

If the appliance has the QEMU guest agent installed, you can retrieve its IP:

```bash
oc get vmi appliance -n ova-appliance -o jsonpath='{.status.interfaces}' | jq
```

### Web Console

Navigate to **Virtualization** → **VirtualMachines** → select the `ova-appliance` project → click **appliance** to see the VM overview, console, and metrics.

## Expose the Appliance Network

### Expose a Single Port via Service and Route

If the appliance serves HTTP/HTTPS (e.g. a management UI on port 443):

```bash
oc create service clusterip appliance-ui \
  --tcp=443:443 \
  -n ova-appliance

oc annotate service appliance-ui \
  "kubevirt.io/domain=appliance" \
  -n ova-appliance
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: appliance-ui
  namespace: ova-appliance
spec:
  selector:
    vm.kubevirt.io/name: appliance
  ports:
    - protocol: TCP
      port: 443
      targetPort: 443
```

```bash
oc apply -f appliance-svc.yaml
oc create route passthrough appliance-ui --service=appliance-ui -n ova-appliance
```

```bash
ROUTE=$(oc get route appliance-ui -n ova-appliance -o jsonpath='{.spec.host}')
echo "https://$ROUTE"
```

### Attach to an External Network (NodePort or CUDN)

For appliances that need Layer-2 connectivity or a routable IP, attach the VM to a secondary network using a **Cluster User Defined Network (CUDN)** or a Linux bridge. See [Networking](../post-installation/networking.md) for details.

## Importing with the Web Console

You can also upload the converted qcow2 image through the OpenShift web console:

1. Go to **Storage** → **PersistentVolumeClaims** → **Create PersistentVolumeClaim** → **With Data upload form**
2. Select the qcow2 file, set the size, and choose your StorageClass
3. Wait for the upload to complete
4. Go to **Virtualization** → **VirtualMachines** → **Create** → **From YAML** and paste the VirtualMachine manifest above (updating `claimName` to match the PVC you created)

## Cleanup

```bash
oc delete vm appliance -n ova-appliance
oc delete pvc appliance-rootdisk -n ova-appliance
oc delete project ova-appliance
```

## Next Steps

- [Deploying Virtual Machines](workload-virtual-machines.md) — deploy VMs from RHEL boot sources
- [VM Failover Test](../operations/vm-failover.md) — validate node-loss recovery
- [VM Backup and Restore](../operations/vm-backup-restore.md) — exercise OADP with the kubevirt plugin
- [Migration Toolkit for Virtualization](../post-installation/mtv.md) — bulk-import VMs from vSphere or other hypervisors
