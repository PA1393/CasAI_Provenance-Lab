# Returns fake hardcoded research objects for now — there's no database or file parsing yet.
# Eventually this will accept real gene sequence files, process them, and store the results.


def list_research_objects() -> list[dict]:
    return [
        {
            "research_object_id": "ro_001",
            "sequence_data": "ATGCGTACGTAGCTAGCTAGCTAGC",
            "metadata": {"organism": "H. sapiens", "source": "manual"},
            "structure_reference": None,
            "hash": "sha256:mock_hash_001",
        },
        {
            "research_object_id": "ro_002",
            "sequence_data": "GCTAGCTAGCTAGCATGCGTACGTA",
            "metadata": {"organism": "M. musculus", "source": "fasta-upload"},
            "structure_reference": "pdb:1ABC",
            "hash": "sha256:mock_hash_002",
        },
    ]
