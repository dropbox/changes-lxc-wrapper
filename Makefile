PKG_NAME = changes-lxc-wrapper
VERSION = 0.0.5
REV=`git rev-list HEAD --count`

deb:
	fpm -s python -t deb -n $(PKG_NAME) -v "$(VERSION)-$(REV)" -a all -d "python3-lxc" -d "python-raven" setup.py

.PHONY: deb
