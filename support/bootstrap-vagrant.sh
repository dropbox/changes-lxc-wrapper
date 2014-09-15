#!/bin/bash -eux

cd /vagrant/

support/bootstrap-ubuntu.sh

sudo pip3 install -e .
