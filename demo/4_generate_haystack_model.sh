#!/bin/bash
pushd ..
poetry run brick-to-haystack demo/from-spreadsheet.ttl demo/from-spreadsheet-haystack.ttl
poetry run brick-to-haystack demo/223p-brick-model.ttl demo/223p-brick-haystack.ttl
popd
