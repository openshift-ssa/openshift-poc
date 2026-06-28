# Configure Registry

The OpenShift internal image registry is deployed by default with ephemeral storage. Images stored in the registry are lost if the registry pod is rescheduled. Configure it to use a Persistent Volume Claim (PVC).

## Configure the Registry with Block Storage

1. Go to the WebUI, click the circle plus, select Import YAML
2. Paste the following to create the PVC for the storage

  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: openshift-image-registry-storage
    namespace: openshift-image-registry
  spec:
    accessModes:
      - ReadWriteMany
    resources:
      requests:
        storage: 100Gi
    storageClassName: ocs-storagecluster-cephfs
    volumeMode: Filesystem
  ```

  !!! warning "HA Filesystem Storage"
      Your backing storage class requires ReadWriteMany (RWX) on file storage for the resgistry to run with multiple instances. If you are just using ReadWriteOnce (RWO) filesystem storage, change the `replicas` value in the `Config` to `1` instead.

3. From the WebUI, go to Home -> API Explorer
4. Filter for "Config", make sure to clock on the one in Group of "imageregistry.operator.openshift.io"
5. Click on Instances tab at the top and then click on the 3 dots to the right of the cluster instance and click Edit Config

  ```yaml
  apiVersion: imageregistry.operator.openshift.io/v1
  kind: Config
  metadata:
    name: cluster
  spec:
    managementState: Managed
    replicas: 2
    rolloutStrategy: Recreate
    storage:
      pvc:
        claim: openshift-image-registry-storage
  ```

6. Watch it roll out

  ```bash
  oc get config.imageregistry/cluster -o jsonpath='{.status.conditions}' | jq
  oc get pods -n openshift-image-registry -w
  ```

## Configure the Registry with Object Storage

1. Go to the WebUI and go to Storage -> Object storage
2. Using the MultiCloud Object Gateway (MCG), click Create Bucket
3. Change namespace to `openshift-image-registry`, ObjectBucketClaim Name is `registry`, keep the classes the same. 
4. Click Create
5. Copy the values for Endpoint, Bucket Name, Access Key and Secret Key. 
6. Go to the WebUI and in the top right hand corner, click on the circle plus icon
7. Select Import YAML
8. Paste the YAML below for the secret. **The image registry looks for the specific name so don't change it**. 

  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: image-registry-private-configuration-user
    namespace: openshift-image-registry
  type: Opaque
  stringData:
    REGISTRY_STORAGE_S3_ACCESSKEY: {{ access_key }}
    REGISTRY_STORAGE_S3_SECRETKEY: {{ secret_key }}
  ```

9. You have to extract the MCG endpoint CA. Extract it and add it to a configmap. 

  ```shell
  oc extract configmap/openshift-service-ca.crt \
    -n openshift-config --keys=service-ca.crt --to=- > service-ca.crt

  oc create configmap image-registry-s3-bundle \
    --from-file=ca-bundle.crt=service-ca.crt \
    -n openshift-config
  ```

10. From the WebUI, go to Home -> API Explorer
11. Filter for "Config", make sure to clock on the one in Group of "imageregistry.operator.openshift.io"
12. Click on Instances tab at the top and then click on the 3 dots to the right of the cluster instance and click Edit Config
13. Update the yaml 

  ```yaml
  apiVersion: imageregistry.operator.openshift.io/v1
  kind: Config
  metadata:
    name: cluster
  spec:
    managementState: Managed
    replicas: 2
    storage:
      s3:
        bucket: {{ bucket_name }}
        region: noobaa
        regionEndpoint: https://s3.openshift-storage.svc:443
        virtualHostedStyle: false
        trustedCA:
          name: image-registry-s3-bundle
  ```

14. Watch it roll out

  ```bash
  oc get config.imageregistry/cluster -o jsonpath='{.status.conditions}' | jq
  oc get pods -n openshift-image-registry -w
  ```