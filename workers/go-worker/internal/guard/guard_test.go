package guard

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

func newGuard(t *testing.T) (*Guard, *miniredis.Miniredis) {
	t.Helper()
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })
	return New(rdb), mr
}

func TestDone(t *testing.T) {
	g, _ := newGuard(t)
	ctx := context.Background()

	if done, _ := g.IsDone(ctx, "j1"); done {
		t.Fatal("não deveria estar concluído")
	}
	_ = g.MarkDone(ctx, "j1")
	if done, _ := g.IsDone(ctx, "j1"); !done {
		t.Fatal("deveria estar concluído")
	}
}

func TestLockExclusivoELiberacaoSegura(t *testing.T) {
	g, mr := newGuard(t)
	ctx := context.Background()

	release, ok, err := g.Lock(ctx, "j1", time.Minute)
	if err != nil || !ok {
		t.Fatal("deveria travar")
	}
	if _, ok, _ := g.Lock(ctx, "j1", time.Minute); ok {
		t.Fatal("segunda trava deveria falhar")
	}

	// a trava expirou e outra réplica pegou: a liberação antiga não pode apagar a nova
	mr.FastForward(2 * time.Minute)
	_, ok, _ = g.Lock(ctx, "j1", time.Minute)
	if !ok {
		t.Fatal("deveria travar após expirar")
	}
	release()
	if !mr.Exists("aiimg:lock:j1") {
		t.Fatal("liberação antiga apagou a trava de outra réplica")
	}
}

func TestOrcamentoDiario(t *testing.T) {
	g, mr := newGuard(t)
	g.now = func() time.Time { return time.Date(2026, 10, 5, 23, 0, 0, 0, time.UTC) }
	ctx := context.Background()

	for i := 0; i < 2; i++ {
		if ok, _ := g.ReserveBudget(ctx, 2); !ok {
			t.Fatalf("reserva %d deveria passar", i)
		}
	}
	if ok, _ := g.ReserveBudget(ctx, 2); ok {
		t.Fatal("terceira reserva deveria ser negada")
	}
	if ttl := mr.TTL("aiimg:budget:20261005"); ttl <= 0 {
		t.Fatal("chave do orçamento sem expiração")
	}

	g.now = func() time.Time { return time.Date(2026, 10, 6, 0, 1, 0, 0, time.UTC) }
	if ok, _ := g.ReserveBudget(ctx, 2); !ok {
		t.Fatal("novo dia deveria ter orçamento novo")
	}
}

func TestSemRedisFechaOOrcamento(t *testing.T) {
	g, mr := newGuard(t)
	mr.Close()

	if ok, err := g.ReserveBudget(context.Background(), 100); ok || err == nil {
		t.Fatal("sem Redis não pode liberar chamada paga")
	}
}
