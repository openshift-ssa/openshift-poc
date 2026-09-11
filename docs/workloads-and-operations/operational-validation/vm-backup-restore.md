# VM Backup and Restore

This guide demonstrates using OADP to back up a virtual machine, make a destructive change, and then restore the VM to its previous state. This assumes [OADP](../../configure-the-cluster/oadp.md) is installed and configured with the `kubevirt` plugin and a valid BackupStorageLocation.

## Prerequisites

- OADP operator installed with BackupStorageLocation showing `Available`
- OpenShift Virtualization installed
- RWX-capable StorageClass available
- A `VolumeSnapshotClass` for your CSI driver (`oc get volumesnapshotclass`) — required for CSI snapshot-based VM backups

## Create a Test Virtual Machine

1. Create a namespace for the test:

  ```bash
  oc new-project vm-backup-test
  ```

2. Go to Virtualization -> VirtualMachines -> ensure you are in the `vm-backup-test` project -> click "Create VirtualMachine"
3. Select "From template" and choose "Red Hat Enterprise Linux 9"
4. Name the VM `backup-test-vm`
5. Click "Customize VirtualMachine"

### Set Login Credentials

6. Open the **Scripts** tab
7. Under **Cloud-init**, set a password for the guest user (RHEL cloud images have no usable default password):

  ```yaml
  #cloud-config
  user: cloud-user
  password: Pass123!
  chpasswd:
    expire: false
  ```

### Add a Data Disk

8. Click on the "Disks" tab
9. Click "Add disk"
10. Configure the data disk:

  - Name: `data-disk`
  - Source: Blank
  - Size: 5 GiB
  - Type: Disk
  - StorageClass: your default StorageClass
  - Access Mode: ReadWriteMany (RWX)
11. Click Add

### Start the VM

12. Click "Create VirtualMachine"
13. Wait for the VM status to show "Running"

## Write Test Data

14. Open the VM console from the WebUI:

  - Virtualization -> VirtualMachines -> click `backup-test-vm` -> Console tab
15. Log in as `cloud-user` / `Pass123!`
16. Format and mount the data disk, then write test data:

  ```bash
  sudo mkfs.xfs /dev/vdb
  sudo mkdir -p /mnt/data
  sudo mount /dev/vdb /mnt/data
  echo "OADP backup test - original data" | sudo tee /mnt/data/testfile.txt
  cat /mnt/data/testfile.txt
  ```

  You should see: `OADP backup test - original data`

17. Confirm the data is written:

  ```bash
  ls -la /mnt/data/
  ```

## Take a Backup

18. Create a Backup CR to capture the running VM and its disks:

  ```yaml
  apiVersion: velero.io/v1
  kind: Backup
  metadata:
    name: backup-test-vm-backup-1
    namespace: openshift-adp
  spec:
    includedNamespaces:
      - vm-backup-test
    snapshotMoveData: true
    ttl: 720h0m0s
  ```

!!! note "Backup Storage Location"
    The `storageLocation` field is omitted because the DPA's `backupLocations` entry is set as `default: true`. Velero automatically uses the default BackupStorageLocation. Verify with: `oc get backupstoragelocations -n openshift-adp`

!!! note
    This backs up **all** resources in the `vm-backup-test` namespace. Namespace-scoped backup ensures the VirtualMachine, its DataVolumes, PVCs, and associated secrets are all captured together.

!!! info "Crash-Consistent Backups"
    OADP with the `kubevirt` and `csi` plugins can back up running VMs using CSI volume snapshots. The resulting backup is crash-consistent — equivalent to an unexpected power loss. This is sufficient for most workloads. If you need application-consistent backups (e.g., databases), either stop the VM first or use the QEMU guest agent for filesystem freeze/thaw.

19. Apply the backup:

  ```bash
  oc apply -f backup.yaml
  ```

20. Watch the backup progress:

  ```bash
  oc get backup backup-test-vm-backup-1 -n openshift-adp -w
  ```

  Wait for the `PHASE` to show `Completed`.

21. Verify the backup contents:

  ```bash
  oc get backup backup-test-vm-backup-1 -n openshift-adp -o jsonpath='{.status.phase}'
  ```

## Make a Destructive Change

22. Open the VM console and modify the data:

  ```bash
  sudo mount /dev/vdb /mnt/data
  echo "THIS DATA HAS BEEN MODIFIED" | sudo tee /mnt/data/testfile.txt
  echo "extra-file-that-shouldnt-exist" | sudo tee /mnt/data/extra.txt
  cat /mnt/data/testfile.txt
  ```

  You should see: `THIS DATA HAS BEEN MODIFIED`

23. Stop the VM:

  ```bash
  virtctl stop backup-test-vm -n vm-backup-test
  ```

## Delete the VM

24. Delete the VM and all PVCs in the namespace to simulate a disaster:

  ```bash
  oc delete vm backup-test-vm -n vm-backup-test
  oc delete pvc --all -n vm-backup-test
  ```

  Template/console VMs do not consistently label disks with `app=backup-test-vm`. Deleting all PVCs in the test namespace ensures root and data disks are removed so restore must recreate them.

25. Confirm the VM and PVCs are gone:

  ```bash
  oc get vm,pvc -n vm-backup-test
  ```

  Should return no VirtualMachine or PVC resources.

## Restore from Backup

26. Create a Restore CR pointing to the backup:

  ```yaml
  apiVersion: velero.io/v1
  kind: Restore
  metadata:
    name: backup-test-vm-restore-1
    namespace: openshift-adp
  spec:
    backupName: backup-test-vm-backup-1
    includedNamespaces:
      - vm-backup-test
    restorePVs: true
  ```

  ```bash
  oc apply -f restore.yaml
  ```

27. Watch the restore progress:

  ```bash
  oc get restore backup-test-vm-restore-1 -n openshift-adp -w
  ```

  Wait for the `PHASE` to show `Completed`.

## Verify the Restore

28. Confirm the VM exists again:

  ```bash
  oc get vm backup-test-vm -n vm-backup-test
  ```

29. Start the restored VM if needed:

  If the VM was backed up with `runStrategy: Always`, it will auto-start after restore. Wait for the VMI to become Ready:

  ```bash
  oc get vmi -n vm-backup-test -w
  ```

  Only use `virtctl start` if the restored VM is in a Stopped state:

  ```bash
  virtctl start backup-test-vm -n vm-backup-test
  ```

  Wait for it to be running:

  ```bash
  oc get vmi backup-test-vm -n vm-backup-test -w
  ```

30. Open the VM console and verify the original data is restored:

  ```bash
  sudo mount /dev/vdb /mnt/data
  cat /mnt/data/testfile.txt
  ls /mnt/data/
  ```

  You should see:
    - `testfile.txt` contains: `OADP backup test - original data` (the original content)
    - `extra.txt` does **not** exist (the modification is gone)

  The VM has been fully restored to the state captured in the backup.

## Summary

| Step               | What Happened                                        |
| ------------------ | ---------------------------------------------------- |
| Create VM          | RHEL 9 VM with a data disk, test data written        |
| Backup             | OADP captured the VM definition, disks, and PVC data |
| Destructive change | Modified data and added files to prove the change    |
| Delete VM          | Simulated a disaster by removing the VM entirely     |
| Restore            | OADP recreated the VM and restored disk contents     |
| Verify             | Original data is back, modifications are gone        |

## Cleanup

31. Delete the test resources:

  ```bash
  oc delete vm backup-test-vm -n vm-backup-test --ignore-not-found
  oc delete pvc --all -n vm-backup-test --ignore-not-found
  oc delete backup backup-test-vm-backup-1 -n openshift-adp
  oc delete restore backup-test-vm-restore-1 -n openshift-adp
  oc delete project vm-backup-test
  ```
