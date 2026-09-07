# Multi-stage Dockerfile: build Go binary in a Golang builder and copy into the
# Python runtime image used by the FastMCP platform. This avoids installing
# the Go toolchain in the runtime image (smaller images) and ensures the
# adapter can exec a prebuilt binary instead of trying to `go build` inside
# the Python base image.

FROM golang:1.25.13-bullseye AS builder
WORKDIR /src

# Cache module download if go.mod/go.sum didn't change
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the source and build the tutor-mcp binary
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -o tutor-mcp .

# Runtime image: the FastMCP Python 3.12 base image used by the platform
FROM 342547628772.dkr.ecr.us-east-1.amazonaws.com/fastmcp-prd-base-images:mcp-base-python3.12
WORKDIR /app

# Copy prebuilt binary and adapter script into the runtime image
COPY --from=builder /src/tutor-mcp /app/tutor-mcp
COPY tutor_mcp_adapter.py /app/tutor_mcp_adapter.py
COPY requirements.txt /app/requirements.txt

# Make executables and install Python dependencies
RUN chmod +x /app/tutor-mcp /app/tutor_mcp_adapter.py \
    && pip install --no-cache-dir -r /app/requirements.txt || true

# Ensure fastmcp knows the entrypoint explicitly (fastmcp.json is also present)
ENV FASTMCP_USER_ENTRYPOINT=tutor_mcp_adapter.py:mcp

ENTRYPOINT ["/usr/bin/env", "python3", "/app/tutor_mcp_adapter.py"]
