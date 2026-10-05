# Build estático; imagem final "scratch": sem shell, sem gerenciador de pacotes.
FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/go-worker ./cmd/worker \
    && mkdir -p /out/data/media

FROM scratch
# certificados para HTTPS com o provedor de IA
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /out/go-worker /go-worker
# mesmo UID da API (10001): os dois leem/escrevem o volume de mídia
COPY --from=build --chown=10001:10001 /out/data /data
USER 10001:10001
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["/go-worker", "healthcheck"]
ENTRYPOINT ["/go-worker"]
