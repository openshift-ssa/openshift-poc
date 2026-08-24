# PVC Read-Back Test

A minimal workload that writes a file to a PersistentVolumeClaim, then spins up a second pod that mounts the same PVC and reads the file back. This validates end-to-end that the CSI driver, StorageClass, and persistent storage are functioning correctly.

## Prerequisites

- [Storage](../post-installation/storage/index.md) configured with a default StorageClass

## Deploy

1. Create a namespace:

  ```bash
  oc new-project pvc-readback
  ```

2. Create the PersistentVolumeClaim:

  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: readback-pvc
    namespace: pvc-readback
  spec:
    accessModes:
      - ReadWriteOnce
    resources:
      requests:
        storage: 1Gi
  ```

  ```bash
  oc apply -f readback-pvc.yaml
  ```

3. Run a pod that writes a file to the PVC:

  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: pvc-writer
    namespace: pvc-readback
  spec:
    restartPolicy: Never
    containers:
      - name: writer
        image: registry.redhat.io/ubi9/ubi-minimal
        command:
          - sh
          - -c
          - |
            echo "Hello from OpenShift PVC test - written at $(date)" > /data/testfile.txt
            echo "File written successfully."
        volumeMounts:
          - name: data
            mountPath: /data
    volumes:
      - name: data
        persistentVolumeClaim:
          claimName: readback-pvc
  ```

  ```bash
  oc apply -f pvc-writer.yaml
  ```

4. Wait for the writer pod to complete:

  ```bash
  oc get pod pvc-writer -n pvc-readback -w
  ```

  The pod should reach `Completed` status. Confirm the write succeeded:

  ```bash
  oc logs pvc-writer -n pvc-readback
  ```

5. Run a second pod that reads the file back from the same PVC:

  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: pvc-reader
    namespace: pvc-readback
  spec:
    restartPolicy: Never
    containers:
      - name: reader
        image: registry.redhat.io/ubi9/ubi-minimal
        command:
          - sh
          - -c
          - |
            echo "Reading file from PVC:"
            cat /data/testfile.txt
        volumeMounts:
          - name: data
            mountPath: /data
            readOnly: true
    volumes:
      - name: data
        persistentVolumeClaim:
          claimName: readback-pvc
  ```

  ```bash
  oc apply -f pvc-reader.yaml
  ```

6. Verify the reader pod can see the data:

  ```bash
  oc logs pvc-reader -n pvc-readback
  ```

  You should see:

  ```
  Reading file from PVC:
  Hello from OpenShift PVC test - written at <timestamp>
  ```

## What This Validates

- **PVC provisioning** — the StorageClass dynamically provisions a volume
- **Data persistence** — data written by one pod is available to another pod mounting the same PVC
- **CSI driver functionality** — the full attach/mount/read/write path works end-to-end

## Cleanup

```bash
oc delete project pvc-readback
```
