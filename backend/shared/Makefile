# SAM builds this layer via `BuildMethod: makefile` (see template.yaml). The target
# name must be build-<LayerLogicalId>. We copy the shared modules into python/shared/
# so they land at /opt/python/shared/ in the layer and import as `shared.*`.
build-SharedLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python/shared"
	cp *.py "$(ARTIFACTS_DIR)/python/shared/"
