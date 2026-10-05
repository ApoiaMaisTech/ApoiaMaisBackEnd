// Package guard usa o Redis para idempotência entre réplicas e para o
// orçamento diário do provedor de IA. O Redis não é fonte de verdade (o estado
// do job fica no MySQL, só pela API): perder estas chaves custa no máximo uma
// geração repetida, nunca um dado errado.
package guard

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
)

const (
	doneTTL   = 7 * 24 * time.Hour
	budgetTTL = 48 * time.Hour
)

var unlockScript = redis.NewScript(`
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
end
return 0`)

type Guard struct {
	rdb *redis.Client
	now func() time.Time
}

func New(rdb *redis.Client) *Guard {
	return &Guard{rdb: rdb, now: time.Now}
}

func (g *Guard) Ping(ctx context.Context) error { return g.rdb.Ping(ctx).Err() }

func (g *Guard) IsDone(ctx context.Context, jobID string) (bool, error) {
	n, err := g.rdb.Exists(ctx, "aiimg:done:"+jobID).Result()
	return n > 0, err
}

func (g *Guard) MarkDone(ctx context.Context, jobID string) error {
	return g.rdb.Set(ctx, "aiimg:done:"+jobID, "1", doneTTL).Err()
}

// Lock impede duas réplicas de gerarem a mesma imagem ao mesmo tempo
// (mensagem reentregue enquanto a primeira ainda processa).
func (g *Guard) Lock(ctx context.Context, jobID string, ttl time.Duration) (func(), bool, error) {
	key := "aiimg:lock:" + jobID
	token := events.NewUUID()
	ok, err := g.rdb.SetNX(ctx, key, token, ttl).Result()
	if err != nil || !ok {
		return func() {}, false, err
	}
	release := func() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = unlockScript.Run(ctx, g.rdb, []string{key}, token).Err()
	}
	return release, true, nil
}

// ReserveBudget consome uma geração do orçamento do dia (UTC).
// Fecha em caso de erro: sem Redis, não chama o provedor pago.
func (g *Guard) ReserveBudget(ctx context.Context, limit int) (bool, error) {
	key := "aiimg:budget:" + g.now().UTC().Format("20060102")
	n, err := g.rdb.Incr(ctx, key).Result()
	if err != nil {
		return false, err
	}
	if n == 1 {
		if err := g.rdb.Expire(ctx, key, budgetTTL).Err(); err != nil {
			return false, err
		}
	}
	return n <= int64(limit), nil
}
