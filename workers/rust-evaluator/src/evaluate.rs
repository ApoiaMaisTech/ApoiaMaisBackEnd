//! Regras de correção. Puras e determinísticas: a mesma entrada sempre dá o mesmo
//! resultado (reprocessar é seguro).
//!
//! | kind     | correto quando                                   | nota (0..1)                         |
//! |----------|--------------------------------------------------|-------------------------------------|
//! | `text`   | distância de edição <= erros permitidos          | 1 - distância / tamanho do gabarito |
//! | `choice` | conjunto marcado == conjunto correto             | Jaccard (acertos / união)           |
//! | `number` | |resposta - gabarito| <= `tolerance`             | 1 ou 0                              |
//!
//! Texto: espaços nas pontas removidos e internos colapsados, Unicode NFC;
//! `ignore_case` (padrão sim) e `ignore_accents` (padrão não: em alfabetização
//! "avó" e "avô" são palavras diferentes). Contra cada gabarito aceito vale o melhor.
//!
//! Erros permitidos = min(`max_typos`, tamanho do gabarito / 4): palavras curtas não
//! ganham tolerância (com 1 erro em "a", qualquer letra seria aceita).

use unicode_normalization::UnicodeNormalization;
use unicode_normalization::char::is_combining_mark;

use crate::events::{
    ENGINE, ENGINE_VERSION, EvaluationCompletedV1, EvaluationItemResultV1, EvaluationItemV1,
    EvaluationRequestedV1, ItemKind,
};

pub fn normalize(text: &str, ignore_case: bool, ignore_accents: bool) -> Vec<char> {
    let collapsed = text.split_whitespace().collect::<Vec<_>>().join(" ");
    let composed: String = if ignore_accents {
        collapsed.nfd().filter(|c| !is_combining_mark(*c)).collect()
    } else {
        collapsed.nfc().collect()
    };
    if ignore_case {
        composed.chars().flat_map(char::to_lowercase).collect()
    } else {
        composed.chars().collect()
    }
}

/// Distância de Levenshtein por caractere (inserção, remoção, troca).
pub fn levenshtein(a: &[char], b: &[char]) -> usize {
    if a.is_empty() {
        return b.len();
    }
    if b.is_empty() {
        return a.len();
    }
    let mut previous: Vec<usize> = (0..=b.len()).collect();
    let mut current = vec![0; b.len() + 1];
    for (i, ca) in a.iter().enumerate() {
        current[0] = i + 1;
        for (j, cb) in b.iter().enumerate() {
            let cost = usize::from(ca != cb);
            current[j + 1] = (previous[j + 1] + 1)
                .min(current[j] + 1)
                .min(previous[j] + cost);
        }
        std::mem::swap(&mut previous, &mut current);
    }
    previous[b.len()]
}

/// Aceita "3", "-2", "3.5" e "3,5" (vírgula decimal). Nada de notação científica,
/// separador de milhar ou texto ("três" é resposta errada, não pedido inválido).
pub fn parse_number(text: &str) -> Option<f64> {
    let trimmed = text.trim();
    if trimmed.is_empty() || trimmed.len() > 40 {
        return None;
    }
    let normalized = trimmed.replace(',', ".");
    let unsigned = normalized.strip_prefix(['-', '+']).unwrap_or(&normalized);
    let valid = !unsigned.is_empty()
        && unsigned.chars().all(|c| c.is_ascii_digit() || c == '.')
        && unsigned.matches('.').count() <= 1
        && !unsigned.starts_with('.')
        && !unsigned.ends_with('.');
    if !valid {
        return None;
    }
    normalized.parse::<f64>().ok().filter(|n| n.is_finite())
}

fn round4(value: f64) -> f64 {
    (value * 10_000.0).round() / 10_000.0
}

fn evaluate_text(item: &EvaluationItemV1) -> (bool, f64) {
    let answer = normalize(&item.answer[0], item.ignore_case, item.ignore_accents);
    item.expected
        .iter()
        .map(|expected| {
            let expected = normalize(expected, item.ignore_case, item.ignore_accents);
            let distance = levenshtein(&answer, &expected);
            let length = expected.len().max(1);
            let allowed = usize::from(item.max_typos).min(expected.len() / 4);
            let score = (1.0 - distance as f64 / length as f64).max(0.0);
            (distance <= allowed, score)
        })
        // melhor gabarito: primeiro o que acerta, depois a maior nota
        .max_by(|a, b| a.0.cmp(&b.0).then(a.1.total_cmp(&b.1)))
        .unwrap_or((false, 0.0))
}

fn evaluate_choice(item: &EvaluationItemV1) -> (bool, f64) {
    use std::collections::BTreeSet;
    let set = |values: &[String]| -> BTreeSet<String> {
        values
            .iter()
            .map(|v| {
                normalize(v, item.ignore_case, item.ignore_accents)
                    .into_iter()
                    .collect()
            })
            .filter(|v: &String| !v.is_empty())
            .collect()
    };
    let answer = set(&item.answer);
    let expected = set(&item.expected);
    let union = answer.union(&expected).count();
    if union == 0 {
        return (false, 0.0);
    }
    let hits = answer.intersection(&expected).count();
    (answer == expected, hits as f64 / union as f64)
}

fn evaluate_number(item: &EvaluationItemV1) -> (bool, f64) {
    let Some(answer) = parse_number(&item.answer[0]) else {
        return (false, 0.0);
    };
    // folga mínima para erro de ponto flutuante (0.1 + 0.2 == 0.3)
    let correct = item
        .expected
        .iter()
        .filter_map(|e| parse_number(e))
        .any(|e| (answer - e).abs() <= item.tolerance + 1e-9);
    (correct, if correct { 1.0 } else { 0.0 })
}

/// (correto, nota sem arredondar)
fn evaluate_raw(item: &EvaluationItemV1) -> (bool, f64) {
    match item.kind {
        ItemKind::Text => evaluate_text(item),
        ItemKind::Choice => evaluate_choice(item),
        ItemKind::Number => evaluate_number(item),
    }
}

pub fn evaluate_item(item: &EvaluationItemV1) -> EvaluationItemResultV1 {
    let (correct, score) = evaluate_raw(item);
    EvaluationItemResultV1 {
        item_id: item.item_id.clone(),
        correct,
        score: round4(score),
    }
}

/// Avalia um pedido já validado (`events::validate_request`).
pub fn evaluate(request: &EvaluationRequestedV1) -> EvaluationCompletedV1 {
    let raw: Vec<(bool, f64)> = request.items.iter().map(evaluate_raw).collect();
    let items: Vec<EvaluationItemResultV1> = request
        .items
        .iter()
        .zip(&raw)
        .map(|(item, (correct, score))| EvaluationItemResultV1 {
            item_id: item.item_id.clone(),
            correct: *correct,
            score: round4(*score),
        })
        .collect();
    let total = items.len();
    let correct = raw.iter().filter(|(c, _)| *c).count();
    let raw_scores: f64 = raw.iter().map(|(_, s)| s).sum();
    EvaluationCompletedV1 {
        evaluation_id: request.evaluation_id.clone(),
        total_items: total,
        correct_items: correct,
        // média das notas sem arredondar (arredonda só no fim)
        score: round4(raw_scores / total.max(1) as f64),
        items,
        engine: ENGINE.to_string(),
        engine_version: ENGINE_VERSION.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn item(kind: ItemKind, answer: &[&str], expected: &[&str]) -> EvaluationItemV1 {
        EvaluationItemV1 {
            item_id: "i1".into(),
            kind,
            answer: answer.iter().map(|s| s.to_string()).collect(),
            expected: expected.iter().map(|s| s.to_string()).collect(),
            ignore_case: true,
            ignore_accents: false,
            max_typos: 0,
            tolerance: 0.0,
        }
    }

    #[test]
    fn normaliza_espacos_caixa_e_unicode() {
        assert_eq!(
            normalize("  Bola   de\tNeve ", true, false),
            "bola de neve".chars().collect::<Vec<_>>()
        );
        // "é" composto (U+00E9) e decomposto (e + U+0301) são iguais depois do NFC
        assert_eq!(
            normalize("caf\u{e9}", true, false),
            normalize("cafe\u{301}", true, false)
        );
        assert_eq!(
            normalize("Avó", true, true),
            "avo".chars().collect::<Vec<_>>()
        );
        assert_eq!(
            normalize("Avó", false, false),
            "Avó".chars().collect::<Vec<_>>()
        );
    }

    #[test]
    fn levenshtein_basico() {
        let c = |s: &str| s.chars().collect::<Vec<_>>();
        assert_eq!(levenshtein(&c("casa"), &c("casa")), 0);
        assert_eq!(levenshtein(&c("caza"), &c("casa")), 1);
        assert_eq!(levenshtein(&c("cas"), &c("casa")), 1);
        assert_eq!(levenshtein(&c(""), &c("casa")), 4);
        assert_eq!(levenshtein(&c("avó"), &c("avô")), 1);
    }

    #[test]
    fn texto_exato_e_com_caixa() {
        let r = evaluate_item(&item(ItemKind::Text, &["CASA "], &["casa"]));
        assert!(r.correct);
        assert_eq!(r.score, 1.0);

        let mut strict = item(ItemKind::Text, &["Casa"], &["casa"]);
        strict.ignore_case = false;
        assert!(!evaluate_item(&strict).correct);
    }

    #[test]
    fn acento_importa_por_padrao() {
        let r = evaluate_item(&item(ItemKind::Text, &["avo"], &["avó"]));
        assert!(!r.correct);
        assert_eq!(r.score, 0.6667);

        let mut lenient = item(ItemKind::Text, &["avo"], &["avó"]);
        lenient.ignore_accents = true;
        assert!(evaluate_item(&lenient).correct);
    }

    #[test]
    fn erros_de_digitacao_proporcionais_ao_tamanho() {
        let mut word = item(ItemKind::Text, &["caza"], &["casa"]);
        word.max_typos = 1;
        assert!(evaluate_item(&word).correct);

        // palavra curta: sem tolerância, mesmo pedindo
        let mut short = item(ItemKind::Text, &["e"], &["a"]);
        short.max_typos = 3;
        assert!(!evaluate_item(&short).correct);

        // 2 erros em palavra de 4 letras: só 1 permitido
        let mut two = item(ItemKind::Text, &["kaza"], &["casa"]);
        two.max_typos = 3;
        assert!(!evaluate_item(&two).correct);
    }

    #[test]
    fn melhor_entre_os_gabaritos_aceitos() {
        let r = evaluate_item(&item(ItemKind::Text, &["mãe"], &["mamãe", "mãe"]));
        assert!(r.correct);
        assert_eq!(r.score, 1.0);
    }

    #[test]
    fn escolha_multipla_com_credito_parcial() {
        let r = evaluate_item(&item(ItemKind::Choice, &["a", "e", "b"], &["a", "e", "i"]));
        assert!(!r.correct);
        assert_eq!(r.score, 0.5);

        let r = evaluate_item(&item(ItemKind::Choice, &["E", "a"], &["a", "e"]));
        assert!(r.correct);
        assert_eq!(r.score, 1.0);

        let r = evaluate_item(&item(ItemKind::Choice, &[], &["a"]));
        assert!(!r.correct);
        assert_eq!(r.score, 0.0);
    }

    #[test]
    fn numeros_com_virgula_e_tolerancia() {
        assert!(evaluate_item(&item(ItemKind::Number, &["3,0"], &["3"])).correct);
        assert!(evaluate_item(&item(ItemKind::Number, &[" -2 "], &["-2"])).correct);
        assert!(!evaluate_item(&item(ItemKind::Number, &["três"], &["3"])).correct);
        assert!(!evaluate_item(&item(ItemKind::Number, &["3.1"], &["3"])).correct);

        let mut tolerant = item(ItemKind::Number, &["0.3"], &["0.1"]);
        tolerant.tolerance = 0.2;
        assert!(evaluate_item(&tolerant).correct);
    }

    #[test]
    fn parse_number_recusa_formatos_ambiguos() {
        for bad in ["", "1e3", "1.000,5", ".5", "5.", "abc", "--1", "NaN", "inf"] {
            assert_eq!(parse_number(bad), None, "{bad}");
        }
        assert_eq!(parse_number("+4"), Some(4.0));
    }
}
