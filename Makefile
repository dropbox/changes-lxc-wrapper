PKG_NAME = changes-lxc-wrapper
VERSION = 0.0.6
REV=`git rev-list HEAD --count`

deb:
	fpm -s python -t deb -n $(PKG_NAME) -v "$(VERSION)-$(REV)" -a all --python-package-name-prefix python3 -d "python3" -d "python3-lxc" setup.py

.PHONY: deb
