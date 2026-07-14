---
crop: maize
latin: Zea mays
techniques: [crispr, base-editing]
---

# Maize (corn)

## Genome resources

- MaizeGDB — https://www.maizegdb.org/
- B73 RefGen reference (check the current assembly version in Ensembl Plants before designing guides)

## Target genes and loci

- **Wx1** (chr 9, *waxy*, granule-bound starch synthase / GBSS) — knockout yields waxy (amylopectin-only) starch
- **ARGOS8** (negative regulator of ethylene response) — higher expression improves drought-stress yield
- **ZmGW2** (RING-type E3 ligase) — knockout increases kernel width and weight
- **ALS / AHAS** (acetolactate synthase) — point mutations confer sulfonylurea/imidazolinone tolerance

## Example edits (DNA change)

- **Waxy corn:** CRISPR-Cas9 knockout of *Wx1* — a frameshift indel at the first exon abolishes GBSS, eliminating amylose. A commercial waxy maize was made this way.
- **ARGOS8 drought:** the native GOS2 promoter is inserted upstream of (or swapped into) the ARGOS8 locus to raise expression — a promoter-swap edit, not a coding change.
- **Herbicide tolerance:** base-edit *ALS* (e.g. a Pro→Ser codon change) with a CBE — a single C·G→T·A with no double-strand break.

## Guide / PAM notes

- Maize is a diploid, so a single functional guide per locus is usually sufficient (unlike hexaploid wheat).
- Confirm the 20-nt protospacer sits next to an NGG PAM in the B73 assembly and screen off-targets against the maize genome, not a generic database.

## Delivery

- Immature-embryo Agrobacterium transformation is standard; protoplast/PEG for transient validation.

## Regulatory

- [[regulators/usda-aphis|USDA]] SECURE rule may exempt certain SDN-1 knockouts — verify product class.

## Related

- [[techniques/crispr]] · [[techniques/base-editing]]
- [[topics/herbicide-tolerance]]
