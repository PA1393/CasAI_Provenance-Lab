export class ApiError extends Error {
  constructor(public readonly status: number | null, public readonly uncertainSubmission = false, public readonly code?: string) {
    const messages: Record<number, string> = {
      401: "Sign-in failed or your session expired. Sign in with your account email and password.",
      403: "This account does not have access to that resource.",
      400: "The input could not be accepted. Check its format and fields.",
      404: "This record or feature is unavailable. Refresh or check the backend version.",
      409: "The record is not ready or its confirmed source could not be verified. Check its status and workspace storage.",
      413: "This request exceeds the upload limit. Use a smaller input.",
      422: "Check the required fields and demo limits: runs accept up to 5,000 DNA bases.",
      429: "Too many requests. Wait before trying again.",
    };
    const setup: Record<string, string> = {
      workspace_setup_required: "Workspace setup is incomplete. Ask the maintainer to apply migration 009 and deploy the matching API.",
      database_not_configured: "The backend database is not configured. Ask the maintainer to configure the server connection.",
      database_unavailable: "The database could not complete the request. Check its connection and availability.",
    };
    super(code && setup[code] ? setup[code] + (uncertainSubmission ? " Inspect Inputs and Runs before retrying; earlier writes may have been recorded." : "") : uncertainSubmission
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
