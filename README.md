# OpenShift PoC Documentation

Prerequisites and installation instructions for Red Hat OpenShift Container Platform in on-premise environments.

## Getting Started

```bash
git clone git@github.com:openshift-ssa/openshift-poc.git
cd openshift-poc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local Development

```bash
source .venv/bin/activate
mkdocs serve --dev-addr 0.0.0.0:8000 --livereload
```

The site will be available at http://localhost:8000/openshift-poc/

## Building

```bash
source .venv/bin/activate
mkdocs build
```

The static site is output to the `site/` directory.

## Project Structure

```
docs/
├── home/                      # Landing page and architecture overview
├── prerequisites/             # Infrastructure, networking, DNS, storage, installation host
├── fleet-management/          # ACM hub install, storage, and spoke provisioning
├── installation/              # Assisted Installer, agent-based, vSphere IPI, disconnected
├── post-installation/         # Day 2 operators, storage, networking, virtualization
│   └── storage/               # ODF and vSphere CSI sub-pages
├── workloads/                 # Container and VM workload examples
├── operations/                # Failover tests, backup/restore, node management
└── assets/                    # Images and stylesheets
```

## Sitewide Variables

OpenShift version references are managed as sitewide variables in `mkdocs.yaml` under the `extra` key:

```yaml
extra:
  ocp_version: "4.21"
  ocp_release: "4.21.0"
```

| Variable | Example Value | Usage |
| --- | --- | --- |
| `ocp_version` | `4.21` | Channel names, operator index tags, CLI download URLs |
| `ocp_release` | `4.21.0` | Full release image tags |

Use these in any markdown page with `{{ ocp_version }}` or `{{ ocp_release }}`. The [mkdocs-macros-plugin](https://mkdocs-macros-plugin.readthedocs.io/) substitutes them at build time. To update the version across all pages, change the values in `mkdocs.yaml`.

Undefined `{{ placeholder }}` variables (e.g., `{{ mirror_host }}`, `{{ bmc_ip }}`) are intentionally left as-is for users to fill in. This is controlled by the `on_undefined: keep` setting in the macros plugin config.

## Contributing

1. Create a feature branch
2. Make changes in the `docs/` directory
3. Verify locally with `mkdocs serve`
4. Submit a pull request
