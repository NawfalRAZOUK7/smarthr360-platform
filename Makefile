# SmartHR360 platform — common commands
.PHONY: keys up down logs migrate seed e2e test-all lint-all observability

keys:
	./scripts/generate_rsa_keys.sh

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

migrate:
	for s in auth core-hr career-sim workload policy-gen retention future-skills; do \
		docker compose exec -T $$s python manage.py migrate --noinput; done

seed:
	python3 scripts/seed_demo.py
	@echo "== seeding future-skills demand (best-effort) =="
	-docker compose exec -T future-skills python manage.py seed_future_skills
	-docker compose exec -T future-skills python manage.py map_platform_codes --defaults

e2e:
	python3 scripts/e2e_smoke.py

test-all:
	pytest packages/smarthr360-jwt-auth/tests/ -q
	for s in services/*/; do \
		echo "== $$s =="; \
		(cd $$s && SECRET_KEY=ci python3 manage.py test -v 0) || exit 1; done

lint-all:
	for s in services/*/; do \
		echo "== $$s =="; \
		(cd $$s && python3 -m ruff check .) || exit 1; done

# Local observability stack: Prometheus scraping all services + Grafana
# (import deploy/observability/grafana-dashboard.json, datasource
# http://localhost:9090)
observability:
	# Prometheus + Grafana now run as part of the compose stack (`make up`),
	# on the smarthr360 network, scraping services by name with the dashboard
	# auto-provisioned. This target just brings them up and prints the URLs.
	docker compose up -d prometheus grafana
	@echo "Prometheus: http://localhost:9090 | Grafana: http://localhost:3000 (admin/admin)"
	@echo "Dashboard: SmartHR360 — Business & Integration Metrics (auto-provisioned)"
