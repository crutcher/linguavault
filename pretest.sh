#!/bin/bash

set -ex

isort .
black .
mypy .

vulture linguavault
