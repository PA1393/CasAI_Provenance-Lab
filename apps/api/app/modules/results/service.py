# Returns a fake hardcoded result for a given run — there's no real simulation output yet.
# Eventually this will read the actual outputs produced when a run completes.


def list_results(run_id: str) -> list[dict]:
    return [
        {
            "result_id": "res_001",
            "run_id": run_id,
            "summary": "Mock result: edit efficiency estimated at 72%.",
            "status": "complete",
        },
    ]
