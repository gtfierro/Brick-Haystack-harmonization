.PHONY: install-deps visualize-taxonomy check-taxonomy all clean convert-haystack-to-ttl demo
JSON_FILES := $(wildcard data/haystack-models/*.json)
TTL_FILES := $(JSON_FILES:.json=.ttl)
CONVERTED_TTL_FILES := $(wildcard data/converted-models/*.ttl)

all: files convert-haystack-to-ttl convert-brick-to-haystack demo

files: data/resolved-bh.json data/resolved-all.json data/bh.ttl data/xetolib data/bmotif/templates.yml

install-deps: pyproject.toml poetry.lock
	poetry install
	poetry run pip install -e ./buildingmotif[topquadrant,xlsx-ingress]
	poetry run pip install openpyxl

visualize-taxonomy:
	poetry run visualize-taxonomy unified_taxonomy.yaml

check-taxonomy:
	poetry run check-brick Brick.ttl unified_taxonomy.yaml

convert-haystack-to-ttl: $(TTL_FILES)
convert-brick-to-haystack: $(CONVERTED_TTL_FILES)

data/xetolib/bh.xeto: data/brick-haystack.csv brick_haystack_harmonization/bh_to_xeto.py
	poetry run bh-to-xeto data/brick-haystack.csv data/xetolib/bh.xeto

data/bmotif/templates.yml: data/brick-haystack.csv brick_haystack_harmonization/bh_to_xeto.py
	poetry run bh-to-xeto data/brick-haystack.csv data/xetolib/bh.xeto

data/resolved-bh.json: data/xetolib/bh.xeto
	rm -f data/resolved-bh.json
	rm -rf xeto/lib/data/xetolib
	cp -r data/xetolib xeto/lib/data/
	xeto/bin/xeto json-ast -out data/resolved-bh.json xetolib ashrae.g36

data/resolved-all.json: xeto/* data/xetolib/bh.xeto
	xeto/bin/xeto json-ast -out data/resolved-all.json all

data/all.json: xeto/* data/xetolib/bh.xeto
	xeto/bin/xeto json-ast -own -out data/all.json all

data/haystack-models/%.ttl: data/haystack-models/%.json brick_haystack_harmonization/ph_to_ttl.py haystack-ontology/haystack.ttl data/bh.ttl brick_haystack_harmonization/ph2ttl2.py
	-poetry run ph-to-ttl $< $@

data/converted-models/%.ttl: data/brick-models/%.ttl brick_haystack_harmonization/brick_to_haystack.py data/bh.ttl haystack-ontology/haystack.ttl
	-poetry run brick-to-haystack $< $@

data/converted-models/%.json: data/brick-models/%.ttl brick_haystack_harmonization/brick_to_haystack.py data/bh.ttl haystack-ontology/haystack.ttl
	poetry run brick-to-haystack $< $@

data/bh.ttl: data/resolved-bh.json brick_haystack_harmonization/xeto_to_shacl.py brick_haystack_harmonization/xeto2shacl2.py
	poetry run xeto-to-shacl data/resolved-bh.json data/bh.ttl

demo/bmotif.db:
	cd demo && poetry run python 1_load_libraries.py

demo/vav_reheat.xlsx: demo/bmotif.db
	cd demo && poetry run python 2_generate_sheet_model.py 

demo: demo/bmotif.db demo/vav_reheat.xlsx
	cd demo && poetry run python 3_generate_model_from_spreadsheet.py
	cd demo && ./4_generate_haystack_model.sh
	cd demo && ./5_generate_brick_223p.sh

clean:
	rm data/haystack-models/*.ttl data/bh.ttl data/xetolib/bh.xeto data/*.json
