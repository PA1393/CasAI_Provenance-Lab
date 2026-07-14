---
crop: tomato
latin: Solanum lycopersicum
techniques: [crispr, base-editing]
---

# Tomato

## Genome resources

- Heinz 1706 reference (SL4.0 assembly / ITAG4.0 annotation)
- Sol Genomics Network (SGN) for loci and annotation

## Target genes and loci

- **SlGAD2 / SlGAD3** (glutamate decarboxylase) — removing the C-terminal autoinhibitory domain raises GABA content
- **SlMLO1** (mildew resistance locus O) — knockout gives powdery-mildew resistance
- **SlIAA9** — knockout produces parthenocarpic (seedless) fruit
- **SP / SELF-PRUNING** — controls determinacy and plant architecture

## Example edits (DNA change)

- **High-GABA tomato:** CRISPR-Cas9 truncates the autoinhibitory domain of *SlGAD* so the enzyme stays active and GABA accumulates. This was the first CRISPR-edited food sold commercially (Japan, 2021).
- **Powdery-mildew resistance:** frameshift knockout of *SlMLO1*.
- **Seedless fruit:** knockout of *SlIAA9* triggers fruit set without fertilization.

## Guide / PAM notes

- Tomato is diploid with efficient transformation, so a single well-placed guide per locus usually suffices.
- Confirm NGG PAM placement in the Heinz 1706 assembly and screen off-targets against the tomato genome.

## Delivery

- Agrobacterium-mediated transformation with efficient shoot regeneration.

## Related

- [[techniques/crispr]] · [[techniques/base-editing]]
- [[topics/field-trials]]
