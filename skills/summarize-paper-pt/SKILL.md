---
name: summarize-paper-pt
description: Read an academic paper in PDF format and produce a concise, well-structured summary in Portuguese, saved as a markdown file. Use this skill whenever the user shares a paper, article, or PDF and asks for a summary, resumo, TL;DR, key points, or an explanation of what the paper is about — especially for papers on Natural Language Processing, AI, machine learning, or Data Engineering, and even if the user doesn't explicitly ask for the output in Portuguese or in markdown.
---

# Summarize Paper (PT)

Read a paper in PDF format and produce a clear, concise summary in **Portuguese (pt-BR)**, saved as a markdown file. The target reader is curious and intelligent but may not have deep technical background in the paper's subject — write so they can follow the ideas without needing to read the original.

## Workflow

1. **Extract the text.** Run `python scripts/extract_pdf.py <paper.pdf>` and read the resulting `.txt` file(s). The script handles two-column layouts (restoring correct reading order), detects scanned pages (applying OCR when tesseract is available, otherwise reporting which pages need it), and splits PDFs longer than 20 pages into part files. It requires `pdfplumber` (`pip install pdfplumber`); if that's not installable, fall back to the Read tool on the PDF directly, in page ranges (e.g. `1-10`, then `11-20`) for long papers. Cover the full paper, including appendices when they contain important results.
2. **Identify the essentials while reading:** the problem the paper addresses, the proposed method, the experimental setup, the main results (with numbers when they matter), and the conclusions/limitations.
3. **Write the summary in Portuguese** following the structure below.
4. **Save the file** as `<paper-title-slug>-summary.md` in the current working directory (or wherever the user asks). Build the slug from the paper's title in lowercase kebab-case, e.g. *"Attention Is All You Need"* → `attention-is-all-you-need-summary.md`. Truncate very long titles to a recognizable prefix (~6 words).

## Summary structure

Use this template. Keep the headings in Portuguese; adapt or drop a section only when the paper genuinely has nothing for it (e.g. a position paper with no experiments).

```markdown
# <Título original do artigo>

> **Autores:** <autores> · **Ano:** <ano> · **Publicado em:** <venue, se identificável>
> **Link/DOI:** <se disponível no PDF>

## Resumo em uma frase
Uma única frase que captura a contribuição central do artigo.

## Contexto e problema
- Qual problema o artigo ataca e por que ele importa.
- O que faltava nas abordagens anteriores.

## Metodologia
- Como a abordagem proposta funciona, em linguagem acessível.
- Componentes principais, dados utilizados, configuração experimental.

## Resultados principais
- Os achados mais importantes, com números concretos quando relevantes
  (métricas, comparações com baselines).

## Conclusões e limitações
- O que os autores concluem.
- Limitações reconhecidas ou evidentes.

## Por que este artigo importa
- Relevância prática ou impacto na área, em 2–3 bullets.
```

## Writing guidelines

- **Language:** the entire summary is in Portuguese, but keep established technical terms in English when that's how the field uses them (*embedding*, *transformer*, *fine-tuning*, *pipeline*) — translating them would confuse rather than help. Italicize these terms on first use.
- **Accessibility:** explain jargon briefly the first time it appears. Prefer "o modelo aprende a prever a próxima palavra" over "o modelo é treinado com objetivo autorregressivo" — or use both, with the plain version first.
- **Formulas:** when a formula is central to the paper's contribution, reproduce it in LaTeX (`$...$` inline, `$$...$$` for display) and explain each symbol in words right after. Don't transcribe formulas that aren't needed to understand the core idea. Extracted plain text usually mangles math notation — for the pages containing key formulas, use the Read tool on the PDF directly (it renders pages visually) and transcribe the LaTeX from there.
- **Figures and tables:** you can't embed the PDF's images, so when a figure or table is crucial, do one of these instead:
  - Rebuild small tables (e.g. results comparisons) as markdown tables.
  - Describe crucial figures in one or two sentences ("A Figura 2 mostra que o erro cai à medida que...").
- **Concision:** the summary should be readable in ~5 minutes. Prefer bullet points over long paragraphs. Include numbers only when they carry the argument (a 15-point improvement matters; the learning rate usually doesn't).
- **Fidelity:** summarize what the paper actually claims, including hedges and limitations. Don't inflate results or present the authors' hypotheses as established facts.

## Edge cases

- **Multiple PDFs:** produce one summary file per paper, each with its own slug.
- **PDF is a preprint/draft:** note that in the metadata line (e.g. "preprint, arXiv").
- **Paper outside NLP/AI/Data Engineering:** the skill still applies — same structure and language rules.
- **User asks for a different depth:** the structure is the default; if the user asks for "só 3 bullets" or a deep-dive, adapt while keeping the output in Portuguese markdown.
