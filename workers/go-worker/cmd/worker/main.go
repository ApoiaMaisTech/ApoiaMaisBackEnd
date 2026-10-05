// go-worker: consome ai.image.requested, gera a imagem e publica o resultado.
//
//	go-worker              executa
//	go-worker healthcheck  usado pelo HEALTHCHECK do container (imagem sem shell)
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/broker"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/config"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/guard"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/imagejob"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/provider"
	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/storage"
)

func main() {
	if len(os.Args) > 1 && os.Args[1] == "healthcheck" {
		os.Exit(healthcheck())
	}

	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	if err := run(logger); err != nil {
		logger.Error("worker encerrado com erro", "error", err)
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}

	redisOpts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		return err
	}
	rdb := redis.NewClient(redisOpts)
	defer rdb.Close()
	g := guard.New(rdb)

	var store storage.Storage
	if cfg.StorageBackend == "s3" {
		store, err = storage.NewS3(cfg.S3Endpoint, cfg.S3Region, cfg.S3Bucket, cfg.S3AccessKeyID, cfg.S3SecretAccessKey, cfg.S3UseSSL)
	} else {
		store, err = storage.NewLocal(cfg.StorageLocalDir)
	}
	if err != nil {
		return err
	}

	var prov provider.Provider = provider.Fake{}
	if cfg.AIProvider == "openai" {
		prov = provider.NewOpenAI(cfg.OpenAIAPIKey, cfg.OpenAIBaseURL, cfg.AIImageModel, cfg.AIRequestTimeout)
	}

	b := &broker.Broker{
		URL:         cfg.AMQPURL,
		Queue:       cfg.QueueName,
		Bindings:    []string{events.AIImageRequested},
		Concurrency: cfg.Concurrency,
		MaxRetries:  cfg.MaxRetries,
		Logger:      logger,
	}
	handler := &imagejob.Handler{
		Provider:    prov,
		Storage:     store,
		Publisher:   b,
		Guard:       g,
		DailyBudget: cfg.DailyImageBudget,
		Logger:      logger,
	}
	b.Handler = handler.Handle

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	srv := healthServer(cfg.HealthAddr, b, g)
	go func() {
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("health server", "error", err)
		}
	}()
	defer func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdownCtx)
	}()

	logger.Info("go-worker iniciado", "provider", prov.Name(), "model", prov.Model(), "storage", cfg.StorageBackend)
	return b.Run(ctx)
}

// Porta só na rede interna do compose; nunca publicada.
func healthServer(addr string, b *broker.Broker, g *guard.Guard) *http.Server {
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	mux.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		if !b.Connected() || g.Ping(ctx) != nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
	})
	return &http.Server{Addr: addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
}

func healthcheck() int {
	addr := os.Getenv("HEALTH_ADDR")
	if addr == "" {
		addr = ":8081"
	}
	if addr[0] == ':' {
		addr = "127.0.0.1" + addr
	}
	client := http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get("http://" + addr + "/readyz")
	if err != nil {
		return 1
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return 1
	}
	return 0
}
