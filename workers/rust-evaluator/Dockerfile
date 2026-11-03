# Build em Debian bookworm (glibc 2.36) para rodar no distroless debian12 (mesma glibc).
FROM rust:1.97-slim-bookworm AS build
WORKDIR /src
# dependências em camada própria: só recompila quando Cargo.toml/Cargo.lock mudam
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && touch src/lib.rs \
    && cargo build --release --locked \
    && rm -rf src target/release/deps/rust_evaluator* target/release/deps/librust_evaluator* \
       target/release/rust-evaluator* target/release/.fingerprint/rust-evaluator-*
COPY src ./src
RUN cargo build --release --locked

# Sem shell nem gerenciador de pacotes; usuário sem privilégios (65532).
FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=build /src/target/release/rust-evaluator /rust-evaluator
USER nonroot:nonroot
EXPOSE 8082
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["/rust-evaluator", "healthcheck"]
ENTRYPOINT ["/rust-evaluator"]
