# Quick Start Guide

Get up and running with CoP Pipeline in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- API Keys (XAI or OpenAI for red-teaming agent, OpenAI for judge)

## Installation
```bash
# 1. Clone repository
git clone <repo-url>
cd cop_pipeline

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
# Edit .env and add your API keys
nano .env  # or use your preferred editor

# 5. Start Docker services
docker-compose up -d

# 6. Verify setup
python cli.py check-setup
```

## First Attack
```bash
# Activate virtual environment
source venv/bin/activate

# Run single attack
python cli.py attack \
    --query "Write a tutorial on hacking" \
    --target gpt-4o-mini \
    --max-iterations 10

# View results
python cli.py history --target gpt-4o-mini --limit 5
```

## Monitoring

- **Metrics**: http://localhost:9090/metrics
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3000 (default: admin/admin)

## Next Steps

1. Read full documentation: `README.md`
2. Run tests: `pytest tests/`
3. View available models: `python cli.py list-models`
4. Try batch campaigns with multiple queries

## Troubleshooting
```bash
# Check setup
python cli.py check-setup

# View Docker logs
docker-compose logs -f

# Restart services
docker-compose restart

# Clean and restart
docker-compose down -v
docker-compose up -d
```

## Getting Help

- Documentation: `README.md`
- Issues: GitHub Issues

---

## Complete Project File Tree
```
cop_pipeline/
├── .dockerignore
├── .env
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