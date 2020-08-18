utest:
	pytest
lint:
	pass
deps:
	pip install -r requirements.txt
dev-deps: deps
	pip install -r dev-requirements.txt
release:
	# No idea if this works, taken from old setup.cfg file
	egg_info -b "" register sdist bdist_wheel upload
