#!/bin/bash

set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Add artifacts folder
mkdir -p ./test-results

# Install dependencies
apt-get update && apt-get install -y libgtk2.0-0 libgtk-3-0 libgbm-dev libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb


# Run tests
yarn run cypress run --record --parallel || (mv cypress/screenshots/* cypress/videos/* ./test-results/; exit 1)
