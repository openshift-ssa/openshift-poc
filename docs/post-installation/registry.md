# Configure Registry

The OpenShift internal image registry is deployed by default with ephemeral storage. Images stored in the registry are lost if the registry pod is rescheduled. Configure it to use a Persistent Volume Claim (PVC).

```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: registry-storage-pvc
  namespace: openshift-image-registry
spec:
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: <storage_class>
EOF
```

Patch the image registry to use the PVC:

```bash
oc patch config.image/cluster -p '{"spec":{"managementState":"Managed","replicas":2,"storage":{"managementState":"Unmanaged","pvc":{"claim":"registry-storage-pvc"}}}}' --type=merge
```
