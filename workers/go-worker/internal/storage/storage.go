// Package storage grava as imagens geradas. Interface única para volume local
// (desenvolvimento) e S3/compatível (produção). O worker só escreve em chaves
// no formato ai-images/<uuid>.png definidas pela API.
package storage

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"

	"github.com/ApoiaMaisTech/ApoiaMaisBackEnd/workers/go-worker/internal/events"
)

type Storage interface {
	// Exists informa se o objeto já existe (e o tamanho), para não pagar o provedor de novo.
	Exists(ctx context.Context, key string) (bool, int64, error)
	Put(ctx context.Context, key string, data []byte, contentType string) error
}

var ErrInvalidKey = errors.New("storage key inválida")

func validateKey(key string) error {
	if !events.StorageKeyRe.MatchString(key) {
		return ErrInvalidKey
	}
	return nil
}

type Local struct {
	base string
}

func NewLocal(base string) (*Local, error) {
	abs, err := filepath.Abs(base)
	if err != nil {
		return nil, err
	}
	return &Local{base: abs}, nil
}

func (l *Local) path(key string) (string, error) {
	if err := validateKey(key); err != nil {
		return "", err
	}
	p := filepath.Join(l.base, filepath.FromSlash(key))
	if !strings.HasPrefix(p, l.base+string(os.PathSeparator)) {
		return "", ErrInvalidKey
	}
	return p, nil
}

func (l *Local) Exists(_ context.Context, key string) (bool, int64, error) {
	p, err := l.path(key)
	if err != nil {
		return false, 0, err
	}
	info, err := os.Stat(p)
	if errors.Is(err, fs.ErrNotExist) {
		return false, 0, nil
	}
	if err != nil {
		return false, 0, err
	}
	return true, info.Size(), nil
}

// Put grava em arquivo temporário e renomeia: quem lê nunca vê imagem pela metade.
func (l *Local) Put(_ context.Context, key string, data []byte, _ string) error {
	p, err := l.path(key)
	if err != nil {
		return err
	}
	dir := filepath.Dir(p)
	if err := os.MkdirAll(dir, 0o750); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(dir, ".upload-*")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name()) // no-op depois do rename
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Chmod(0o640); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	return os.Rename(tmp.Name(), p)
}

type S3 struct {
	client *minio.Client
	bucket string
}

func NewS3(endpoint, region, bucket, accessKey, secretKey string, useSSL bool) (*S3, error) {
	client, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: useSSL,
		Region: region,
	})
	if err != nil {
		return nil, fmt.Errorf("cliente S3: %w", err)
	}
	return &S3{client: client, bucket: bucket}, nil
}

func (s *S3) Exists(ctx context.Context, key string) (bool, int64, error) {
	if err := validateKey(key); err != nil {
		return false, 0, err
	}
	info, err := s.client.StatObject(ctx, s.bucket, key, minio.StatObjectOptions{})
	if err != nil {
		if minio.ToErrorResponse(err).Code == "NoSuchKey" {
			return false, 0, nil
		}
		return false, 0, err
	}
	return true, info.Size, nil
}

func (s *S3) Put(ctx context.Context, key string, data []byte, contentType string) error {
	if err := validateKey(key); err != nil {
		return err
	}
	_, err := s.client.PutObject(ctx, s.bucket, key, bytes.NewReader(data), int64(len(data)),
		minio.PutObjectOptions{ContentType: contentType})
	return err
}
