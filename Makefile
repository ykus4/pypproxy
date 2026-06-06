.PHONY: build build-all web-install web-build web-dev test run clean

build:
	go build -o bin/paxy ./cmd/paxy

build-all: build web-build
	go build -o bin/paxy ./cmd/paxy

web-install:
	cd web && npm install

web-build:
	cd web && npm run build

web-dev:
	cd web && npm run dev

test:
	go test ./...

run:
	go run ./cmd/paxy

clean:
	rm -rf bin/ web/dist/
