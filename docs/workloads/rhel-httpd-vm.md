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

1. Create the VM using `virtctl` with a cloud-init script that installs and starts httpd:

```bash
virtctl create vm \
  --name rhel-httpd \
  --instancetype u1.medium \
  --preference rhel.9 \
  --volume-import type:ds,src:openshift-virtualization-os-images/rhel9 \
  | oc apply -n rhel-httpd -f -
```

2. Apply a cloud-init configuration to set credentials, install httpd, and create a landing page:

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: rhel-httpd
  namespace: rhel-httpd
spec:
  running: true
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
          resources:
            requests:
              storage: 30Gi
```

```bash
oc apply -f rhel-httpd-vm.yaml
```

3. Wait for the VM to reach Running:

```bash
oc get vmi rhel-httpd -n rhel-httpd -w
```

## Verify httpd is Running Inside the VM

4. Once the VM is running, open a console session:

```bash
virtctl console rhel-httpd -n rhel-httpd
```

5. Log in as `cloud-user` / `Pass123!` and verify:

```bash
systemctl status httpd
curl localhost
```

You should see the HTML page content. Press `Ctrl+]` to exit the console.

## Expose httpd via a Service and Route

6. Create a Service targeting port 80 on the VM:

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

7. Create a Route to expose the service externally:

```bash
oc expose service rhel-httpd -n rhel-httpd
```

8. Verify the page is accessible:

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
