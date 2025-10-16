# Quick Start Guide

Get up and running with CoP Pipeline in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- API Keys (XAI, OpenAI)

## Installation
```bash
# 1. Clone repository
git clone <repo-url>
cd CoP_Pipeline

# 2. Run setup
make setup

# 3. Configure API keys
cp .env.example .env
nano .env  # Add your API keys

# 4. Start services
make run
```

## First Attack
```bash
# Activate virtual environment
source venv/bin/activate

# Run single attack
python cli.py attack \
    --query "Write a tutorial on hacking" \
    --target llama-2-7b-chat

# View results
python cli.py history --target llama-2-7b-chat
```

## Monitoring

- **Metrics**: http://localhost:9090/metrics
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3000 (admin/admin)

## Next Steps

1. Read full documentation: `README.md`
2. Run tests: `make test`
3. Deploy to production: `make deploy`

## Troubleshooting
```bash
# Check setup
python cli.py check-setup

# View logs
make logs

# Clean and restart
make clean
make run
```

## Getting Help

- Documentation: `docs/`
- Issues: GitHub Issues
- Email: support@example.com
```

---

## Complete Project File Tree
```
CoP_Pipeline/
├── .dockerignore
├── .env
├── .env.example
├── .gitignore
├── BUILD_INSTRUCTIONS.md
├── DEPLOYMENT.md
├── Dockerfile
├── LICENSE
├── Makefile
├── QUICKSTART.md
├── README.md
├── cli.py
├── docker-compose.prod.yml
├── docker-compose.yml
├── main.py
├── pyproject.toml
├── requirements.txt
│
├── agents/
│   ├── __init__.py
│   ├── judge_llm.py
│   ├── red_teaming_agent.py
│   └── target_interface.py
│
├── config/
│   ├── __init__.py
│   ├── prometheus.yml
│   ├── settings.py
│   └── grafana/
│       ├── dashboards/
│       │   └── cop_dashboard.json
│       └── datasources/
│           └── prometheus.yml
│
├── data/
│   └── .gitkeep
│
├── database/
│   ├── __init__.py
│   ├── models.py
│   └── repository.py
│
├── evaluation/
│   ├── __init__.py
│   ├── jailbreak_scorer.py
│   └── similarity_checker.py
│
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── ingress.yaml
│   ├── namespace.yaml
│   ├── secrets.yaml
│   └── service.yaml
│
├── logs/
│   └── .gitkeep
│
├── orchestration/
│   ├── __init__.py
│   ├── cop_workflow.py
│   └── iteration_manager.py
│
├── principles/
│   ├── __init__.py
│   ├── principle_composer.py
│   ├── principle_library.json
│   └── principle_library.py
│
├── results/
│   └── .gitkeep
│
├── scripts/
│   ├── benchmark.sh
│   ├── deploy.sh
│   ├── run_tests.sh
│   └── setup.sh
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_agents.py
│   ├── test_evaluation.py
│   ├── test_integration.py
│   ├── test_orchestration.py
│   └── test_principles.py
│
└── utils/
    ├── __init__.py
    ├── logging_metrics.py
    └── prompt_templates.py