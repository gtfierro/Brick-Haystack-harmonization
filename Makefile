.PHONY: install-deps visualize-taxonomy check-taxonomy

install-deps:
	poetry install

visualize-taxonomy:
	poetry run python tools/visualize_taxonomy.py unified_taxonomy.yaml

check-taxonomy:
	poetry run python tools/check_brick.py Brick.ttl unified_taxonomy.yaml
