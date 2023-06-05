#!/bin/bash

pushd haxall-3.1.7

rm -rf test1
bin/hx init -headless -suUser asdf -suPass asdf test1
echo 'Run cd ../../data/converted-models && python3 -m http.server'
echo 'Run ioReadJson(`http://localhost:8000/g36-vav-a2.json`).map(r=>diff(null, r, {add}).commit)'
bin/hx run test1
