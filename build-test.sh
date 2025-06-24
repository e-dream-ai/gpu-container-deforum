docker build -t deforum-entrypoint-test .
docker run --rm -v $(pwd)/output:/workspace/output deforum-entrypoint-test