// Package moderation faz a checagem local do prompt antes de gastar com o provedor.
//
// O prompt já vem de um template fixo da API; o risco está no tema da fase
// (texto cadastrado por professores). A moderação da IMAGEM gerada é feita
// pelo provedor (OpenAI: moderation=auto); a imagem também é validada como
// PNG antes de ser gravada.
package moderation

import (
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// Palavras inteiras (sem acento): "arma" bloqueia "arma", mas não "farmacia".
var blockedWords = map[string]bool{
	"sangue": true, "morte": true, "morto": true, "morta": true, "cadaver": true,
	"arma": true, "armas": true, "faca": true, "pistola": true, "revolver": true,
	"violencia": true, "terror": true, "horror": true, "nudez": true, "nu": true, "nua": true,
	"sexo": true, "sexual": true, "droga": true, "drogas": true, "cocaina": true, "maconha": true,
	"tortura": true, "agulha": true, "agulhas": true, "cirurgia": true,
	"blood": true, "gore": true, "weapon": true, "gun": true, "guns": true, "knife": true,
	"kill": true, "nude": true, "naked": true, "sex": true, "drug": true, "drugs": true,
}

// Radicais: bloqueiam qualquer palavra que comece com eles.
var blockedPrefixes = []string{"assassin", "suicid", "mutil", "esquartej"}

func words(s string) []string {
	t := transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
	out, _, err := transform.String(t, strings.ToLower(s))
	if err != nil {
		out = strings.ToLower(s)
	}
	return strings.FieldsFunc(out, func(r rune) bool { return !unicode.IsLetter(r) })
}

// themeMarker separa o template fixo da API (que tem frases como "sem violência")
// do tema variável da fase, que é o que precisa ser checado.
const themeMarker = "Tema:"

// Theme devolve o trecho variável do prompt (depois do último "Tema:");
// sem o marcador, o prompt inteiro é tratado como variável.
func Theme(prompt string) string {
	if i := strings.LastIndex(prompt, themeMarker); i >= 0 {
		return prompt[i+len(themeMarker):]
	}
	return prompt
}

// CheckPrompt devolve o termo bloqueado encontrado no tema, ou "" se passou.
func CheckPrompt(prompt string) string {
	for _, w := range words(Theme(prompt)) {
		if blockedWords[w] {
			return w
		}
		for _, p := range blockedPrefixes {
			if strings.HasPrefix(w, p) {
				return p
			}
		}
	}
	return ""
}
