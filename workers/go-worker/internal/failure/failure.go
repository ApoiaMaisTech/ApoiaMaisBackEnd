// Package failure classifica erros em permanentes (não adianta tentar de novo)
// e temporários (retry com backoff). Erro sem classificação é tratado como
// temporário: na dúvida, tenta de novo e o limite de tentativas protege.
package failure

import (
	"errors"
	"fmt"
)

type Error struct {
	Code      string // snake_case, vai no evento ai.image.failed
	Message   string
	Retryable bool
	Err       error
}

func (e *Error) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.Err)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *Error) Unwrap() error { return e.Err }

func Permanent(code, message string, err error) *Error {
	return &Error{Code: code, Message: message, Err: err}
}

func Transient(code, message string, err error) *Error {
	return &Error{Code: code, Message: message, Retryable: true, Err: err}
}

func IsRetryable(err error) bool {
	var fe *Error
	if errors.As(err, &fe) {
		return fe.Retryable
	}
	return true
}

// CodeOf devolve o código do erro classificado ou o fallback.
func CodeOf(err error, fallback string) string {
	var fe *Error
	if errors.As(err, &fe) && fe.Code != "" {
		return fe.Code
	}
	return fallback
}
