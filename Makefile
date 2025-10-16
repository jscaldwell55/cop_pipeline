.PHONY: help setup test run clean deploy

help:
	@echo "CoP Pipeline - Available commands:"
	@echo "  make setup     - Initial setup and installation"
	@echo "  make test      - Run test suite"
	@echo "  make run       - Start services"
	@echo "  make clean     - Clean up resources"
	@echo "  make deploy    - Deploy to production"
	@echo "  make logs      - View logs"
	@echo "  make backup    - Backup database"

setup:
	@chmod +x scripts/*.sh
	@./scripts/setup.sh

test:
	@./scripts/run_tests.sh

run:
	@docker-compose up -d
	@echo "Services started. View logs with: make logs"

clean:
	@docker-compose down -v
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage .pytest_cache/

deploy:
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh

logs:
	@docker-compose logs -f

backup:
	@mkdir -p backups
	@docker exec cop-postgres pg_dump -U cop_user cop_pipeline > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/"