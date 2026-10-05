// Package config lê a configuração das variáveis de ambiente.
// O worker não tem (e não deve ter) credenciais do MySQL.
package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	AMQPURL  string
	RedisURL string

	QueueName   string
	Concurrency int
	MaxRetries  int

	StorageBackend    string // local | s3
	StorageLocalDir   string
	S3Endpoint        string
	S3Bucket          string
	S3Region          string
	S3AccessKeyID     string
	S3SecretAccessKey string
	S3UseSSL          bool

	AIProvider       string // fake | openai
	OpenAIAPIKey     string
	OpenAIBaseURL    string
	AIImageModel     string
	AIRequestTimeout time.Duration
	DailyImageBudget int
	HealthAddr       string
}

func Load() (Config, error) {
	c := Config{
		AMQPURL:           os.Getenv("AMQP_URL"),
		RedisURL:          os.Getenv("REDIS_URL"),
		QueueName:         env("QUEUE_NAME", "go-worker.ai-image"),
		StorageBackend:    env("STORAGE_BACKEND", "local"),
		StorageLocalDir:   env("STORAGE_LOCAL_DIR", "/data/media"),
		S3Endpoint:        os.Getenv("S3_ENDPOINT"),
		S3Bucket:          os.Getenv("S3_BUCKET"),
		S3Region:          env("S3_REGION", "us-east-1"),
		S3AccessKeyID:     os.Getenv("S3_ACCESS_KEY_ID"),
		S3SecretAccessKey: os.Getenv("S3_SECRET_ACCESS_KEY"),
		AIProvider:        env("AI_PROVIDER", "fake"),
		OpenAIAPIKey:      os.Getenv("OPENAI_API_KEY"),
		OpenAIBaseURL:     env("OPENAI_BASE_URL", "https://api.openai.com"),
		AIImageModel:      env("AI_IMAGE_MODEL", "gpt-image-1"),
		HealthAddr:        env("HEALTH_ADDR", ":8081"),
	}

	var err error
	if c.Concurrency, err = envInt("WORKER_CONCURRENCY", 4); err != nil {
		return c, err
	}
	if c.MaxRetries, err = envInt("MAX_RETRIES", 3); err != nil {
		return c, err
	}
	if c.DailyImageBudget, err = envInt("AI_DAILY_IMAGE_BUDGET", 200); err != nil {
		return c, err
	}
	timeoutSeconds, err := envInt("AI_REQUEST_TIMEOUT_SECONDS", 120)
	if err != nil {
		return c, err
	}
	c.AIRequestTimeout = time.Duration(timeoutSeconds) * time.Second
	if c.S3UseSSL, err = strconv.ParseBool(env("S3_USE_SSL", "true")); err != nil {
		return c, fmt.Errorf("S3_USE_SSL inválido: %w", err)
	}
	return c, c.validate()
}

func (c Config) validate() error {
	switch {
	case c.AMQPURL == "":
		return fmt.Errorf("AMQP_URL é obrigatório")
	case c.RedisURL == "":
		return fmt.Errorf("REDIS_URL é obrigatório")
	case c.Concurrency < 1 || c.Concurrency > 64:
		return fmt.Errorf("WORKER_CONCURRENCY deve estar entre 1 e 64")
	case c.MaxRetries < 0:
		return fmt.Errorf("MAX_RETRIES não pode ser negativo")
	case c.DailyImageBudget < 0:
		return fmt.Errorf("AI_DAILY_IMAGE_BUDGET não pode ser negativo")
	case c.StorageBackend != "local" && c.StorageBackend != "s3":
		return fmt.Errorf("STORAGE_BACKEND deve ser local ou s3")
	case c.StorageBackend == "s3" && (c.S3Endpoint == "" || c.S3Bucket == ""):
		return fmt.Errorf("S3_ENDPOINT e S3_BUCKET são obrigatórios com STORAGE_BACKEND=s3")
	case c.AIProvider != "fake" && c.AIProvider != "openai":
		return fmt.Errorf("AI_PROVIDER deve ser fake ou openai")
	case c.AIProvider == "openai" && c.OpenAIAPIKey == "":
		return fmt.Errorf("OPENAI_API_KEY é obrigatório com AI_PROVIDER=openai")
	}
	return nil
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) (int, error) {
	v := os.Getenv(key)
	if v == "" {
		return fallback, nil
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return 0, fmt.Errorf("%s inválido: %w", key, err)
	}
	return n, nil
}
