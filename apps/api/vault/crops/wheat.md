---
crop: wheat
latin: Triticum aestivum
techniques: [crispr, base-editing]
---

# Wheat

## Genome resources

- Chinese Spring reference (IWGSC RefSeq) — the community standard
- Allohexaploid genome (AABBDD): three homoeologous subgenomes complicate guide design

## Target genes and loci

- **TaMLO-A1 / -B1 / -D1** (mildew resistance locus O) — knockout of all three homoeologs gives powdery-mildew resistance
- **TaGW2-A1 / -B1 / -D1** (grain weight) — knockout increases grain size and weight
- **α-gliadin gene family** — multiplex knockout produces low-gluten (low-immunogenicity) wheat
- **TaALS** — point mutation for herbicide tolerance

## Example edits (DNA change)

- **Powdery-mildew resistance:** simultaneously knock out *TaMLO* in **all three subgenomes** (A, B, D); indels in each homoeolog are required because a single-copy edit is masked by the others.
- **Low-gluten wheat:** multiplexed CRISPR-Cas9 targets conserved sequences across many α-gliadin copies at once, deleting a large fraction of the immunogenic gene family.
- **Herbicide tolerance:** base-edit *TaALS* (a single C·G→T·A) with a CBE — no double-strand break.

## Guide / PAM notes

- The big difference from maize/rice: **hexaploidy**. A guide must hit the intended homoeolog(s) — design against conserved regions to edit all three at once, or subgenome-specific SNPs to edit just one.
- Verify NGG PAM placement in the IWGSC assembly and account for A/B/D homoeolog sequence when screening off-targets.

## Delivery

- Biolistic transformation of immature embryos; wheat regeneration is more difficult than rice.

## Related

- [[techniques/crispr]] · [[techniques/base-editing]]
- [[crops/rice]]
