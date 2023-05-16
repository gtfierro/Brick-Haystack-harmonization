# Brick/Haystack Harmonization

## Brick/Haystack conversion

![repository-overview](img/brick-haystack-harmonization-repo.png)

## Brick-to-Haystack

![brick-to-haystack](img/brick-to-haystack.png)

- put Brick model in `data/converted-models`
- run `make convert-brick-to-haytack`
- Only outputs TTL file; no JSON conversion yet

## Haystack-to-Brick

![haystack-to-brick](img/haystack-to-brick.png)
 
- put JSON export of Haystack model in `data/haystack-models`
- run `make convert-haystack-to-ttl`
- Adds Brick annotations to Haystack model

## Taxonomy Alignment

### Get Started

1. [Install Poetry for Python dep management](https://python-poetry.org/docs/master/#installing-with-the-official-installer)
2. Install dependencies by running `poetry install` or `make install-deps` in this repo
3. Visualize the current taxonomy file with `make visualize-taxonomy`; the graph will be in `unified_taxonomy.png`
4. Check congruency issues between the unified taxonomy and the different ontologies:
    - `make check-taxonomy` will run these for you
    
### Unified Taxonomy

![Unified taxonomy for Brick and Haystack](.github/images/unified_taxonomy.png)

### Ontology Reports

[Brick Report](brick_report.txt)
