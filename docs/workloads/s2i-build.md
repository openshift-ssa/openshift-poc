# Source-to-Image (S2I) Build

[Source-to-Image Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/builds_using_buildconfig/build-strategies#builds-strategy-s2i-build_build-strategies)

Source-to-Image (S2I) is an OpenShift build strategy that takes application source code from a Git repository and produces a runnable container image — no Containerfile required. The developer provides source code, OpenShift provides the builder image, and S2I handles the rest.

This is one of the key differentiators between OpenShift and vanilla Kubernetes. It enables developers to go from Git push to running application without needing to understand container image builds.

## How It Works

```
Git Repository ──> S2I Builder Image ──> Application Image ──> Deployment
  (source code)     (language runtime)    (built by OpenShift)   (running pods)
```

1. OpenShift clones the source repo
2. The builder image compiles/packages the application
3. The resulting image is pushed to the internal registry
4. A Deployment and Service are created automatically

## Deploy a Python Application

1. Create a namespace:

  ```bash
  oc new-project s2i-demo
  ```

2. Deploy from a Git repository using the Python builder image:

  ```bash
  oc new-app python~https://github.com/sclorg/django-ex.git --name=django-app
  ```

  The `python~` prefix tells OpenShift which builder image to use. OpenShift can also auto-detect the language from the repository contents.

3. Watch the build:

  ```bash
  oc logs -f buildconfig/django-app
  ```

  The build clones the repo, installs dependencies from `requirements.txt`, and assembles the image.

4. Expose the application:

  ```bash
  oc expose service django-app
  ```

5. Verify:

  ```bash
  oc get pods -n s2i-demo
  ROUTE=$(oc get route django-app -o jsonpath='{.spec.host}')
  echo "Application available at: http://$ROUTE"
  curl -s -o /dev/null -w "%{http_code}" http://$ROUTE
  ```

## Deploy a Node.js Application

1. Create a namespace:

  ```bash
  oc new-project s2i-node
  ```

2. Deploy using the Node.js builder:

  ```bash
  oc new-app nodejs~https://github.com/sclorg/nodejs-ex.git --name=node-app
  ```

3. Watch the build and expose:

  ```bash
  oc logs -f buildconfig/node-app
  oc expose service node-app
  ```

4. Verify:

  ```bash
  ROUTE=$(oc get route node-app -o jsonpath='{.spec.host}')
  curl http://$ROUTE
  ```

## Available Builder Images

List the builder images available in your cluster:

```bash
oc get imagestreams -n openshift | grep -E "NAME|python|nodejs|java|ruby|php|perl|dotnet|go"
```

Common builders include:

| Builder  | Language/Runtime            |
| -------- | --------------------------- |
| `python` | Python (Django, Flask)      |
| `nodejs` | Node.js (Express, Next.js)  |
| `java`   | Java (Spring Boot, Quarkus) |
| `ruby`   | Ruby (Rails, Sinatra)       |
| `php`    | PHP (Laravel, Symfony)      |
| `dotnet` | .NET (ASP.NET Core)         |
| `golang` | Go                          |

## Trigger a Rebuild

After pushing code changes to the Git repository, trigger a new build:

```bash
oc start-build django-app
oc logs -f buildconfig/django-app
```

OpenShift can also be configured with webhooks to trigger builds automatically on Git push.

## What to Show in a Demo

- **No Containerfile needed** — the developer only provides source code
- **Build logs** show the entire process (clone, dependency install, image assembly)
- **Internal registry** — the built image is stored in the OpenShift registry automatically
- **Instant rollout** — a new deployment rolls out as soon as the image build completes
- **Rebuild on code change** — `oc start-build` or webhook triggers

## Cleanup

```bash
oc delete project s2i-demo
oc delete project s2i-node
```
