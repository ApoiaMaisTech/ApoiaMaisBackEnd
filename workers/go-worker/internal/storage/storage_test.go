package storage

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const key = "ai-images/7d1e2f3a4b5c4d6e8f9a0b1c2d3e4f5a.png"

func TestLocalPutEExists(t *testing.T) {
	dir := t.TempDir()
	s, err := NewLocal(dir)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()

	if ok, _, err := s.Exists(ctx, key); err != nil || ok {
		t.Fatalf("não deveria existir: %v %v", ok, err)
	}
	if err := s.Put(ctx, key, []byte("png"), "image/png"); err != nil {
		t.Fatal(err)
	}
	ok, size, err := s.Exists(ctx, key)
	if err != nil || !ok || size != 3 {
		t.Fatalf("exists=%v size=%d err=%v", ok, size, err)
	}
	data, _ := os.ReadFile(filepath.Join(dir, key))
	if string(data) != "png" {
		t.Fatal("conteúdo errado")
	}
	leftovers, _ := filepath.Glob(filepath.Join(dir, "ai-images", ".upload-*"))
	if len(leftovers) != 0 {
		t.Fatal("arquivo temporário ficou para trás")
	}
}

func TestLocalRecusaChavesForaDoPadrao(t *testing.T) {
	s, _ := NewLocal(t.TempDir())
	for _, bad := range []string{"../x.png", "ai-images/../../etc/passwd", "/etc/passwd", "outro/abc.png", "ai-images/abc.png"} {
		if err := s.Put(context.Background(), bad, []byte("x"), "image/png"); !errors.Is(err, ErrInvalidKey) {
			t.Errorf("%q: esperado ErrInvalidKey, veio %v", bad, err)
		}
	}
}

// Integração com S3 compatível (MinIO, SeaweedFS, AWS). Ex.:
// S3_TEST_ENDPOINT=127.0.0.1:8333 S3_TEST_BUCKET=apoiamais-test go test ./internal/storage/
func TestS3PutEExists(t *testing.T) {
	endpoint, bucket := os.Getenv("S3_TEST_ENDPOINT"), os.Getenv("S3_TEST_BUCKET")
	if endpoint == "" || bucket == "" {
		t.Skip("S3_TEST_ENDPOINT/S3_TEST_BUCKET não definidos")
	}
	s, err := NewS3(endpoint, "us-east-1", bucket, os.Getenv("S3_TEST_ACCESS_KEY"), os.Getenv("S3_TEST_SECRET_KEY"), false)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	testKey := "ai-images/" + strings.Repeat("ab", 16) + ".png"

	if err := s.Put(ctx, testKey, []byte("png-s3"), "image/png"); err != nil {
		t.Fatal(err)
	}
	ok, size, err := s.Exists(ctx, testKey)
	if err != nil || !ok || size != 6 {
		t.Fatalf("exists=%v size=%d err=%v", ok, size, err)
	}
	missing := "ai-images/" + strings.Repeat("cd", 16) + ".png"
	if ok, _, err := s.Exists(ctx, missing); err != nil || ok {
		t.Fatalf("objeto inexistente: ok=%v err=%v", ok, err)
	}
}
