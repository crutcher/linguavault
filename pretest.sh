#!/bin/bash

set -ex

isort .
black .
mypy .

