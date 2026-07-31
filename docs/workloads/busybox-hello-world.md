# Hello World Web Server

A simple "Hello World" web server using the [Red Hat Hardened](https://www.redhat.com/en/products/hardened-images) Nginx image.

1. Create a namespace:

  ```bash
  oc new-project hello-world
  ```

2. Create a ConfigMap with the page content:

  ```bash
  oc create configmap hello-world-html \
    --from-literal=index.html='<html><body><h1>Hello World!</h1></body></html>' \
    -n hello-world
  ```

3. Create the Deployment:

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
          - name: nginx
            image: registry.access.redhat.com/hi/nginx:latest
            ports:
              - containerPort: 8080
            resources:
              requests:
                memory: "32Mi"
                cpu: "50m"
              limits:
                memory: "64Mi"
                cpu: "100m"
            volumeMounts:
              - name: html
                mountPath: /usr/share/nginx/html
                readOnly: true
        volumes:
          - name: html
            configMap:
              name: hello-world-html
  ```

  ```bash
  oc apply -f hello-world.yaml
  ```

4. Create a Service and Route:

  ```bash
  oc expose deployment hello-world --port=8080
  oc expose service hello-world
  ```

5. Verify it's running:

  ```bash
  oc get pods -n hello-world
  ROUTE=$(oc get route hello-world -o jsonpath='{.spec.host}')
  curl http://$ROUTE
  ```

  You should see: `Hello World!`
