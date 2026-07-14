---
crop: cotton
latin: Gossypium hirsutum
techniques: [crispr, base-editing]
---

# Cotton

## Genome resources

- TM-1 reference (upland cotton)
- Allotetraploid genome (AD; A and D subgenomes) — like wheat, homoeologs complicate guide design

## Target genes and loci

- **δ-cadinene synthase (GhCDNC)** — knockout lowers gossypol for edible (ultra-low-gossypol) cottonseed
- **GhMYB25-like** — fiber initiation and development
- **Gh14-3-3d** — Verticillium / disease resistance
- Fiber-length and fiber-quality loci

## Example edits (DNA change)

- **Low-gossypol seed:** knock out *δ-cadinene synthase* so cottonseed becomes a safer protein source; doing it seed-specifically (while keeping gossypol defenses elsewhere in the plant) is the harder goal.
- **Fiber traits:** edit *GhMYB25-like* and related loci to tune fiber initiation and quality.

## Guide / PAM notes

- Like wheat, cotton is **allotetraploid**, so a guide often must target both the A- and D-subgenome homoeologs (or a subgenome-specific SNP to hit just one).
- Confirm NGG PAM placement in the TM-1 assembly and account for A/D homoeolog sequence when screening off-targets.

## Delivery

- Agrobacterium-mediated transformation; cotton regeneration is slow and highly genotype-dependent.

## Related

- [[techniques/crispr]] · [[crops/wheat]]
