.PHONY: install-deps visualize-taxonomy check-taxonomy all clean convert-haystack-to-ttl

all: install-deps files convert-haystack-to-ttl convert-brick-to-haystack

files: data/resolved-bh.json data/resolved-all.json data/bh.ttl data/xetolib

install-deps: pyproject.toml poetry.lock
	poetry install

visualize-taxonomy:
	poetry run visualize-taxonomy unified_taxonomy.yaml

check-taxonomy:
	poetry run check-brick Brick.ttl unified_taxonomy.yaml

convert-haystack-to-ttl: data/haystack-models/alpha.ttl

convert-brick-to-haystack: data/converted-models/g36-vav-a2.ttl

data/xetolib/bh.xeto: data/brick-haystack.csv brick_haystack_harmonization/bh_to_xeto.py
	poetry run bh-to-xeto data/brick-haystack.csv data/xetolib/bh.xeto

data/bmotif_templates.yml: data/brick-haystack.csv brick_haystack_harmonization/bh_to_xeto.py
	poetry run bh-to-xeto data/brick-haystack.csv data/xetolib/bh.xeto

data/resolved-bh.json: data/xetolib/bh.xeto
	rm -f data/resolved-bh.json
	rm -rf xeto/lib/data/xetolib
	cp -r data/xetolib xeto/lib/data/
	xeto/bin/xeto json-ast -out data/resolved-bh.json xetolib

data/resolved-all.json: xeto/* data/xetolib/bh.xeto
	xeto/bin/xeto json-ast -out data/resolved-all.json all

data/all.json: xeto/* data/xetolib/bh.xeto
	xeto/bin/xeto json-ast -own -out data/resolved-all.json all

data/haystack-models/%.ttl: data/haystack-models/%.json brick_haystack_harmonization/ph_to_ttl.py haystack-ontology/haystack.ttl data/bh.ttl
	poetry run ph-to-ttl $< $@

data/converted-models/%.ttl: data/brick-models/%.ttl brick_haystack_harmonization/brick_to_haystack.py data/bh.ttl haystack-ontology/haystack.ttl
	poetry run brick-to-haystack $< $@

data/bh.ttl: data/resolved-bh.json brick_haystack_harmonization/xeto_to_shacl.py
	poetry run xeto-to-shacl data/resolved-bh.json data/bh.ttl

clean:
	rm data/haystack-models/*.ttl data/bh.ttl
