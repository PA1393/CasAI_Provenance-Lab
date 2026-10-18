# Declarative molecular scene manifest

The backend-owned `casai.scene-manifest.v1` contract describes what a molecular
viewer may render without embedding renderer commands or executable scripts.
Assets use content checksums and trusted local/database identifiers; HTTP, data,
file and script URLs are rejected.

The manifest keeps assets, selections, annotations, measurements, coordinate
transforms, camera states and visibility states explicit. Residue and nucleotide
coordinates are 1-based and inclusive. Annotations and measurements carry both
an evidence source and a matching scientific claim type. Structure assets are
separately labeled experimentally reported, predicted or explanatory.

Initial scenes are labeled explanatory or predicted. Explanatory scenes cannot
claim trajectory artifacts. This backend increment is renderer-independent and
does not implement the Person 2-owned Mol* frontend.

`POST /api/v1/scene-manifests` validates, content-addresses and immutably stores a
bounded manifest. `GET /api/v1/scene-manifests/{scene_id}` reloads it with integrity
checks. Workspace-backed molecular assets must already exist under their exact
checksum; client-provided paths and URLs are never resolved.
