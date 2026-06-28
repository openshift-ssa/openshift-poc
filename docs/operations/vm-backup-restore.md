# VM Backup and Restore

This guide demonstrates using OADP to back up a virtual machine, make a destructive change, and then restore the VM to its previous state. This assumes [OADP](../post-installation/oadp.md) is installed and configured with the `kubevirt` plugin and a valid BackupStorageLocation.

## Prerequisites

- OADP operator installed with BackupStorageLocation showing `Available`
- OpenShift Virtualization installed
- RWX-capable StorageClass available

## Create a Test Virtual Machine

1. Create a namespace for the test:

  ```bash
  oc new-project vm-backup-test
  ```

2. Go to Virtualization -> VirtualMachines -> ensure you are in the `vm-backup-test` project -> click "Create VirtualMachine"
3. Select "From template" and choose "Red Hat Enterprise Linux 9"
4. Name the VM `backup-test-vm`
5. Click "Customize VirtualMachine"

### Add a Data Disk

6. Click on the "Disks" tab
7. Click "Add disk"
8. Configure the data disk:
    - Name: `data-disk`
    - Source: Blank
    - Size: 5 GiB
    - Type: Disk
    - StorageClass: your default StorageClass
    - Access Mode: ReadWriteMany (RWX)
9. Click Add

### Start the VM

10. Click "Create VirtualMachine"
11. Wait for the VM status to show "Running"

## Write Test Data

12. Open the VM console from the WebUI:
    - Virtualization -> VirtualMachines -> click `backup-test-vm` -> Console tab
13. Login to the guest OS (default credentials from the template)
14. Format and mount the data disk, then write test data:

  ```bash
  sudo mkfs.xfs /dev/vdb
  sudo mkdir -p /mnt/data
  sudo mount /dev/vdb /mnt/data
  echo "OADP backup test - original data" | sudo tee /mnt/data/testfile.txt
  cat /mnt/data/testfile.txt
  ```

  You should see: `OADP backup test - original data`

15. Confirm the data is written:

  ```bash
  ls -la /mnt/data/
  ```

## Take a Backup

16. Create a Backup CR to capture the running VM and its disks:

  ```yaml
  apiVersion: velero.io/v1
  kind: Backup
  metadata:
    name: backup-test-vm-backup-1
    namespace: openshift-adp
  spec:
    includedNamespaces:
      - vm-backup-test
    labelSelector:
      matchLabels:
        app: backup-test-vm
    storageLocation: dpa-1
    ttl: 720h0m0s
  ```

  !!! note
      The label `app: backup-test-vm` is automatically applied by OpenShift Virtualization when creating from a template.

  !!! info "Crash-Consistent Backups"
      OADP with the `kubevirt` and `csi` plugins can back up running VMs using CSI volume snapshots. The resulting backup is crash-consistent — equivalent to an unexpected power loss. This is sufficient for most workloads. If you need application-consistent backups (e.g., databases), either stop the VM first or use the QEMU guest agent for filesystem freeze/thaw.

  ```bash
  oc apply -f backup.yaml
  ```

17. Watch the backup progress:

  ```bash
  oc get backup backup-test-vm-backup-1 -n openshift-adp -w
  ```

  Wait for the `PHASE` to show `Completed`.

18. Verify the backup contents:

  ```bash
  oc get backup backup-test-vm-backup-1 -n openshift-adp -o jsonpath='{.status.phase}'
  ```

## Make a Destructive Change

19. Open the VM console and modify the data:

  ```bash
  sudo mount /dev/vdb /mnt/data
  echo "THIS DATA HAS BEEN MODIFIED" | sudo tee /mnt/data/testfile.txt
  echo "extra-file-that-shouldnt-exist" | sudo tee /mnt/data/extra.txt
  cat /mnt/data/testfile.txt
  ```

  You should see: `THIS DATA HAS BEEN MODIFIED`

20. Stop the VM:

  ```bash
  virtctl stop backup-test-vm -n vm-backup-test
  ```

## Delete the VM

21. Delete the VM and its PVCs to simulate a disaster:

  ```bash
  oc delete vm backup-test-vm -n vm-backup-test
  oc delete pvc -l app=backup-test-vm -n vm-backup-test
  ```

22. Confirm the VM is gone:

  ```bash
  oc get vm backup-test-vm -n vm-backup-test
  ```

  Should return `NotFound`.

## Restore from Backup

23. Create a Restore CR pointing to the backup:

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

24. Watch the restore progress:

  ```bash
  oc get restore backup-test-vm-restore-1 -n openshift-adp -w
  ```

  Wait for the `PHASE` to show `Completed`.

## Verify the Restore

25. Confirm the VM exists again:

  ```bash
  oc get vm backup-test-vm -n vm-backup-test
  ```

26. Start the restored VM:

  ```bash
  virtctl start backup-test-vm -n vm-backup-test
  ```

  Wait for it to be running:

  ```bash
  oc get vmi backup-test-vm -n vm-backup-test -w
  ```

27. Open the VM console and verify the original data is restored:

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

| Step                  | What Happened                                              |
| --------------------- | ---------------------------------------------------------- |
| Create VM             | RHEL 9 VM with a data disk, test data written              |
| Backup                | OADP captured the VM definition, disks, and PVC data       |
| Destructive change    | Modified data and added files to prove the change          |
| Delete VM             | Simulated a disaster by removing the VM entirely           |
| Restore               | OADP recreated the VM and restored disk contents           |
| Verify                | Original data is back, modifications are gone              |

## Cleanup

28. Delete the test resources:

  ```bash
  oc delete vm backup-test-vm -n vm-backup-test
  oc delete pvc -l app=backup-test-vm -n vm-backup-test
  oc delete backup backup-test-vm-backup-1 -n openshift-adp
  oc delete restore backup-test-vm-restore-1 -n openshift-adp
  oc delete project vm-backup-test
  ```
