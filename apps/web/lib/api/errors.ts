export class ApiError extends Error {
  constructor(public readonly status: number | null, public readonly uncertainSubmission = false) {
    const messages: Record<number, string> = {
      400: "The input could not be accepted. Check its format and fields.",
      404: "This record or feature is unavailable. Refresh or check the backend version.",
      409: "The record is not ready or its confirmed source could not be verified. Check its status and workspace storage.",
      413: "This request exceeds the upload limit. Use a smaller input.",
      422: "Check the required fields and demo limits: runs accept up to 5,000 DNA bases.",
      429: "Too many requests. Wait before trying again.",
    };
    super(uncertainSubmission
      ? "The response was interrupted or the backend reported an error. Check Inputs and Runs before submitting again; the request may already have been recorded."
      : status === null
        ? "The backend could not be reached or returned an unreadable response. Check the connection and refresh."
        : messages[status] ?? "The backend could not complete this request. Check the connection and deployment.");
    this.name = "ApiError";
  }
}

export function submissionMayExist(error: unknown): boolean {
  return !(error instanceof ApiError) || error.uncertainSubmission;
}
