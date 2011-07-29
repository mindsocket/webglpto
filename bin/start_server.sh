#!/bin/bash

cd $(dirname $(dirname $0))/static/
python -m SimpleHTTPServer
cd -

