# Web Terminal Operator

[Red Hat Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/web_console/index#installing-web-terminal)

The Web Terminal Operator provides an embedded command-line terminal in the OpenShift web console. It gives developers and administrators quick access to `oc`, `kubectl`, and other CLI tools directly from the browser without needing a local terminal or SSH session.

!!! info
    The Web Terminal Operator requires cluster administrator privileges to install, but once installed, any authenticated user can open a terminal session from the web console.

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Web Terminal" -> click the "Web Terminal" tile (provided by Red Hat)
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install

## Install the Operator via YAML

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: web-terminal
  namespace: openshift-operators
spec:
  channel: fast
  name: web-terminal
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
```

```bash
oc apply -f web-terminal-operator.yaml
```

Wait for the operator:

```bash
oc get csv -n openshift-operators -w
```

The `PHASE` should show `Succeeded`.

## Using the Web Terminal

1. Log in to the OpenShift web console
2. Click the command-line terminal icon ( **>_** ) in the upper-right corner of the console
3. Select the project where the terminal workspace will run (a `DevWorkspace` is created in that project)
4. The terminal session opens in a panel at the bottom of the console

The terminal comes pre-loaded with common CLI tools including `oc`, `kubectl`, `kn`, `tkn`, `helm`, `subctl`, and `odo`.

!!! tip
    The terminal session runs as a `DevWorkspace` pod in the selected project. Sessions have configurable idle timeouts — by default, inactive terminals are shut down after 15 minutes.

## Configure Idle Timeout

To change the default idle timeout, edit the `DevWorkspace` operator configuration:

```yaml
apiVersion: workspace.devfile.io/v1alpha1
kind: DevWorkspaceOperatorConfig
metadata:
  name: devworkspace-operator-config
  namespace: openshift-operators
spec:
  workspace:
    idleTimeout: 30m
```

```bash
oc apply -f devworkspace-config.yaml
```

## Configure Network Policies

If your cluster uses network policies that restrict pod communication, the web terminal workspace pods need to be able to reach the OpenShift API server. If terminals fail to connect, ensure the namespace where the terminal runs allows egress to the API server.

## Uninstall

To remove the Web Terminal Operator:

1. Go to Ecosystem -> Installed Operators -> Web Terminal
2. Click the Actions menu -> Uninstall Operator
3. Clean up any remaining `DevWorkspace` resources:

```bash
oc get devworkspaces --all-namespaces
oc delete devworkspaces --all -A
```

## Verify

```bash
oc get csv -n openshift-operators | grep web-terminal
oc get pods -n openshift-operators -l app.kubernetes.io/part-of=web-terminal-operator
```

The operator pod should be in `Running` state, and the web terminal icon should be visible in the console toolbar.
