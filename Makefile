.PHONY: build test clean run

BINARY_NAME=bin/athletistat

build:
	@mkdir -p bin
	go build -o $(BINARY_NAME) ./cmd/athletistat

test:
	go test -v ./...

clean:
	rm -rf bin/

run: build
	./$(BINARY_NAME) --help
