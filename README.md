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
├── index.md                   # Home page
├── stylesheets/extra.css      # Red Hat brand colors
├── prerequisites/             # Infrastructure, networking, DNS, LB, storage
├── installation/              # IPI, UPI, agent-based install methods
└── post-installation/         # Day 2 operations
```

## Contributing

1. Create a feature branch
2. Make changes in the `docs/` directory
3. Verify locally with `mkdocs serve`
4. Submit a pull request
