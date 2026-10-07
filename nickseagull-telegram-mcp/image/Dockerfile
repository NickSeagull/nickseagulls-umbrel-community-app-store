# Built from upstream nguyenvanduocit/telegram-mcp at b57f47d93ed1d3e05fe615db5640a05740aea043.
FROM --platform=$BUILDPLATFORM golang:1.25.3-alpine3.22 AS build
ARG TARGETOS
ARG TARGETARCH
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -trimpath -ldflags='-s -w' -o /out/telegram-mcp-umbrel .

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build --chown=1000:1000 /out/telegram-mcp-umbrel /telegram-mcp-umbrel
USER 1000:1000
EXPOSE 8080
ENTRYPOINT ["/telegram-mcp-umbrel"]
