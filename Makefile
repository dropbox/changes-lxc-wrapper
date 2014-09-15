PKG_NAME = changes-lxc-wrapper
VERSION = 0.0.6
REV=`git rev-list HEAD --count`

deb:
	fpm -s python -t deb \
		-n $(PKG_NAME) \
		-v "$(VERSION)-$(REV)" \
		-a all \
		--python-bin python3 \
		--python-package-name-prefix python3 \
		-d "python3-setuptools" \
		-d "python3" \
		-d "python3-lxc" \
		setup.py

setup-test-env:
	virtualenv --python=`which python3` ./env --system-site-packages
	env/bin/pip3 install -e .
	env/bin/pip3 install "file://`pwd`#egg=changes-lxc-wrapper[tests]"

test:
	env/bin/py.test

.PHONY: deb
