# Busybox Web Server

A simple "Hello World" web server using busybox httpd.

1. Create a namespace:

  ```bash
  oc new-project hello-world
  ```

2. Create the Deployment:

  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: hello-world
    namespace: hello-world
  spec:
    replicas: 2
    selector:
      matchLabels:
        app: hello-world
    template:
      metadata:
        labels:
          app: hello-world
      spec:
        containers:
          - name: httpd
            image: busybox:latest
            command:
              - "/bin/sh"
              - "-c"
              - |
                echo "Hello World!" > /var/www/index.html
                httpd -f -p 8080 -h /var/www
            ports:
              - containerPort: 8080
            resources:
              requests:
                memory: "32Mi"
                cpu: "50m"
              limits:
                memory: "64Mi"
                cpu: "100m"
  ```

  ```bash
  oc apply -f hello-world.yaml
  ```

3. Create a Service and Route:

  ```bash
  oc expose deployment hello-world --port=8080
  oc expose service hello-world
  ```

4. Verify it's running:

  ```bash
  oc get pods -n hello-world
  ROUTE=$(oc get route hello-world -o jsonpath='{.spec.host}')
  curl http://$ROUTE
  ```

  You should see: `Hello World!`
