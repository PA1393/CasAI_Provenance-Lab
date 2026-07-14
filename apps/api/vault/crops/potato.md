---
crop: potato
latin: Solanum tuberosum
techniques: [crispr, base-editing]
---

# Potato

## Genome resources

- DM1-3 doubled-monoploid reference assembly
- Cultivated potato is autotetraploid (four alleles per locus) — edits often must hit all four

## Target genes and loci

- **StVInv** (vacuolar invertase) — knockout reduces cold-induced sweetening, lowering acrylamide in fried products
- **GBSS** (granule-bound starch synthase) — knockout yields waxy (amylopectin-only) starch for industry
- **S-RNase / self-incompatibility** — targets for diploid hybrid-potato breeding
- Late-blight **R genes** — disease resistance

## Example edits (DNA change)

- **Low-acrylamide potato:** knock out *StVInv* in **all four alleles**; less reducing sugar means less acrylamide (a processing-safety improvement) when the tubers are fried.
- **Waxy potato:** frameshift knockout of *GBSS* removes amylose for a pure-amylopectin industrial starch.

## Guide / PAM notes

- The key challenge is **autotetraploidy**: a phenotype usually needs the edit across all four allele copies, so target conserved regions and expect to screen for full knockouts.
- Confirm NGG PAM placement in the DM reference and screen off-targets against the potato genome.

## Delivery

- Agrobacterium-mediated transformation; protoplast/PEG transfection is common for DNA-free RNP editing.

## Related

- [[techniques/crispr]] · [[techniques/base-editing]]
- [[crops/tomato]]
