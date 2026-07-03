# SmartHR360 platform — common commands
.PHONY: keys up down logs migrate seed e2e test-all

keys:
	./scripts/generate_rsa_keys.sh

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

migrate:
	for s in auth core-hr career-sim workload policy-gen retention; do \
		docker compose exec -T $$s python manage.py migrate --noinput; done

seed:
	python3 scripts/seed_demo.py

e2e:
	python3 scripts/e2e_smoke.py

test-all:
	pytest packages/smarthr360-jwt-auth/tests/ -q
	for s in services/*/; do \
		echo "== $$s =="; \
		(cd $$s && SECRET_KEY=ci python3 manage.py test -v 0) || exit 1; done
