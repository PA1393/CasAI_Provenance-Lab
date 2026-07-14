---
crop: soybean
latin: Glycine max
techniques: [crispr, base-editing]
---

# Soybean

## Genome resources

- SoyBase — https://www.soybase.org/
- Williams 82 reference assembly (Wm82; check the current version in Phytozome)

## Target genes and loci

- **GmFAD2-1A / GmFAD2-1B** (fatty acid desaturase 2) — knockout of both homoeologs raises oleic acid, giving high-oleic oil
- **GmF3H / disease-resistance loci** — pathogen resistance targets
- **GmALS** (acetolactate synthase) — point mutation for herbicide tolerance
- **E1 / maturity genes** — tune flowering time and adaptation

## Example edits (DNA change)

- **High-oleic oil:** knock out **both** *FAD2-1A* and *FAD2-1B* (soybean is paleopolyploid, so the two copies are redundant); frameshift indels in each stop desaturation of oleic to linoleic acid. This trait was first commercialized with TALENs and is reproducible with CRISPR-Cas9.
- **Herbicide tolerance:** base-edit *ALS* (a single C·G→T·A recreating a tolerant allele) with a CBE — no double-strand break, no transgene.

## Guide / PAM notes

- Because key traits sit on duplicated homoeologs (e.g. FAD2-1A/1B), design guides that hit **both** copies, or one guide per copy, or the phenotype will be incomplete.
- Verify NGG PAM placement in Wm82 and screen off-targets against the soybean genome.

## Delivery

- Agrobacterium-mediated cotyledonary-node transformation; hairy-root and protoplast systems for validation.

## Regulatory

- Many SDN-1 edits may fall outside [[regulators/usda-aphis|USDA APHIS]] regulation — confirm product class.

## Related

- [[techniques/crispr]] · [[techniques/base-editing]]
- [[topics/herbicide-tolerance]]
