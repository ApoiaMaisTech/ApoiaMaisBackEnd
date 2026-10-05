package moderation

import "testing"

const template = "Ilustração infantil. Sem texto, sem violência, sem elementos assustadores e sem ambiente hospitalar. Tema: "

func TestTemplateDaAPINaoEhBloqueado(t *testing.T) {
	// o template tem "sem violência": só o tema pode ser checado
	if term := CheckPrompt(template + "Floresta das Letras - Vogais."); term != "" {
		t.Fatalf("bloqueou o template: %q", term)
	}
}

func TestTemasBloqueados(t *testing.T) {
	for _, theme := range []string{"Armas", "SANGUE na floresta", "Assassino", "cirurgia", "Violência"} {
		if CheckPrompt(template+theme) == "" {
			t.Errorf("deveria bloquear %q", theme)
		}
	}
}

func TestSemFalsosPositivos(t *testing.T) {
	// "arma" dentro de "farmácia", "sex" em "sexta", "gun" em "segunda"
	for _, theme := range []string{"Farmácia do bairro", "Sexta-feira", "Segunda letra", "Armário de brinquedos", "Nuvens"} {
		if term := CheckPrompt(template + theme); term != "" {
			t.Errorf("%q bloqueado por %q", theme, term)
		}
	}
}
