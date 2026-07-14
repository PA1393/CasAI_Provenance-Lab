---
crop: rice
latin: Oryza sativa
techniques: [crispr, base-editing]
---

# Rice

## Genome resources

- Nipponbare reference (IRGSP-1.0) — the standard japonica assembly
- RAP-DB and Rice Genome Hub for annotation and locus IDs

## Target genes and loci

- **OsSWEET11 / OsSWEET13 / OsSWEET14** (sugar transporters) — promoter editing confers bacterial-blight resistance
- **OsBADH2** (betaine aldehyde dehydrogenase) — knockout produces fragrant (aromatic) rice
- **Wx** (*waxy*, GBSS) — base editing fine-tunes amylose content / eating quality
- **OsERF922**, **Gn1a**, **DEP1**, **GS3** — blast resistance and yield-component genes

## Example edits (DNA change)

- **Bacterial-blight resistance:** disrupt the **TAL-effector-binding element in the SWEET gene promoter** (e.g. OsSWEET14) so *Xanthomonas* can no longer induce the transporter — a small promoter edit, not a coding knockout.
- **Fragrant rice:** frameshift knockout of *OsBADH2* causes 2-acetyl-1-pyrroline to accumulate (the basmati/jasmine aroma).
- **Grain quality:** ABE/CBE base edits in *Wx* shift amylose content without a transgene.

## Guide / PAM notes

- Rice is diploid with an efficient transformation/regeneration system, so it is the usual first platform to validate a CRISPR-Cas9, Cas12a, or [[techniques/base-editing|base-editor]] design.
- Confirm NGG (SpCas9) or TTTV (Cas12a) PAM placement in Nipponbare and screen off-targets against the rice genome.

## Delivery

- Agrobacterium-mediated and biolistic transformation; protoplast/PEG for transient assays.

## Related

- [[techniques/crispr]] · [[techniques/base-editing]]
- [[resources/genome-databases]]
