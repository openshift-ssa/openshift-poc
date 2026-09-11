# RHEL VM with Apache httpd

Deploy a Red Hat Enterprise Linux 9 virtual machine on OpenShift Virtualization, install Apache httpd, and serve a webpage accessible via an OpenShift Route.

## Prerequisites

- OpenShift Virtualization installed and healthy
- A default virtualization StorageClass with RWX support
- RHEL 9 boot source available (`oc get datasources -n openshift-virtualization-os-images | grep rhel9`)
- `oc` and `virtctl` installed locally

## Create the Project

```bash
oc new-project rhel-httpd
```

## Create the Virtual Machine

Choose one of the two options below.

=== "Option A: Full YAML (Recommended)"

    Apply a `VirtualMachine` manifest with cloud-init that sets credentials, installs httpd, and creates a landing page:

    ```yaml
    apiVersion: kubevirt.io/v1
    kind: VirtualMachine
    metadata:
      name: rhel-httpd
      namespace: rhel-httpd
    spec:
      runStrategy: Always
      template:
        spec:
          domain:
            resources:
              requests:
                memory: 2Gi
            devices:
              disks:
                - name: rootdisk
                  disk:
                    bus: virtio
                - name: cloudinit
                  disk:
                    bus: virtio
          volumes:
            - name: rootdisk
              dataVolume:
                name: rhel-httpd-rootdisk
            - name: cloudinit
              cloudInitNoCloud:
                userData: |
                  #cloud-config
                  user: cloud-user
                  password: Pass123!
                  chpasswd:
                    expire: false
                  packages:
                    - httpd
                  runcmd:
                    - systemctl enable httpd --now
                    - echo '<html><body><h1>Hello from OpenShift Virtualization</h1><p>Served by Apache httpd on RHEL 9</p></body></html>' > /var/www/html/index.html
                    - restorecon -Rv /var/www/html
      dataVolumeTemplates:
        - metadata:
            name: rhel-httpd-rootdisk
          spec:
            sourceRef:
              kind: DataSource
              name: rhel9
              namespace: openshift-virtualization-os-images
            storage:
              accessModes:
                - ReadWriteMany
              volumeMode: Block
              resources:
                requests:
                  storage: 30Gi
    ```

    ```bash
    oc apply -f rhel-httpd-vm.yaml
    ```

=== "Option B: Quick CLI"

    Create the VM using `virtctl` with cloud-init credentials. This does **not** install httpd automatically — install and start it manually after the VM boots (see step 3).

    ```bash
    echo 'Pass123!' > /tmp/vm-password
    virtctl create vm \
      --name rhel-httpd \
      --instancetype u1.medium \
      --preference rhel.9 \
      --volume-import type:ds,src:openshift-virtualization-os-images/rhel9 \
      --user cloud-user \
      --password-file /tmp/vm-password \
      | oc apply -n rhel-httpd -f -
    ```

1. Wait for the VM to reach Running:

```bash
oc get vmi rhel-httpd -n rhel-httpd -w
```

## Verify httpd is Running Inside the VM

2. Once the VM is running, open a console session:

```bash
virtctl console rhel-httpd -n rhel-httpd
```

3. Log in as `cloud-user` / `Pass123!`. If you used Option A, verify httpd:

```bash
systemctl status httpd
curl localhost
```

If you used Option B, install and start httpd first:

```bash
sudo dnf install -y httpd
sudo systemctl enable httpd --now
echo '<html><body><h1>Hello from OpenShift Virtualization</h1><p>Served by Apache httpd on RHEL 9</p></body></html>' | sudo tee /var/www/html/index.html
sudo restorecon -Rv /var/www/html
curl localhost
```

You should see the HTML page content. Press `Ctrl+]` to exit the console.

## Expose httpd via a Service and Route

4. Create a Service targeting port 80 on the VM:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rhel-httpd
  namespace: rhel-httpd
spec:
  selector:
    vm.kubevirt.io/name: rhel-httpd
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
```

```bash
oc apply -f rhel-httpd-svc.yaml
```

5. Create a Route to expose the service externally:

```bash
oc expose service rhel-httpd -n rhel-httpd
```

6. Verify the page is accessible:

```bash
ROUTE=$(oc get route rhel-httpd -n rhel-httpd -o jsonpath='{.spec.host}')
curl http://$ROUTE
```

You should see:

```
<html><body><h1>Hello from OpenShift Virtualization</h1><p>Served by Apache httpd on RHEL 9</p></body></html>
```

## Cleanup

```bash
oc delete vm rhel-httpd -n rhel-httpd
oc delete project rhel-httpd
```
