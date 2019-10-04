.PHONY: build

build:
	docker build -t micro-infrastructure/adaptor-srm2local .

run: build
	docker run -dt --rm -P micro-infrastructure/adaptor-srm2local

push: build
	docker push micro-infrastructure/adaptor-srm2local

