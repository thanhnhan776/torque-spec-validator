import { useState } from "react";
import type { UploadResponse, Validation } from "./types";

const SEVERITY_ORDER: Record<Validation["severity"], number> = {
  error: 0,
  warning: 1,
  info: 2,
};

const ISSUE_GUIDANCE: Record<string, string> = {
  missing_document_date: "Check the source document and provide its date.",
  invalid_date_format:
    "Check the source value and use a valid date in YYYY-MM-DD format.",
  missing_code: "Check the source and provide the correct address code.",
  missing_torque:
    "Consult the authoritative specification and provide the torque value.",
  invalid_torque_format:
    "Check the source and provide a finite numeric torque value.",
  non_possitive_torque:
    "Verify the torque against the authoritative specification; it must be positive.",
  missing_start_date: "Check the source for the applicable start date.",
  missing_end_date: "Check the source for the applicable end date.",
  missing_notes:
    "Check whether notes are needed to identify the correct application.",
  start_date_after_document_date:
    "Verify the start date and document date against the source.",
  start_date_after_current_date:
    "Confirm that this future effective date is intended.",
  end_date_before_document_date:
    "Verify whether the specification was valid on the document date.",
  end_date_before_current_date:
    "Confirm whether this expired specification is still relevant.",
  invalid_date_range:
    "Verify both dates; the start date must not be after the end date.",
  duplicate_record:
    "Compare the matching records and confirm whether the duplicate is intended.",
  overlapping_torque_specifications:
    "Compare the overlapping records and verify their dates and torque values against the source.",
  implausible_torque:
    "Verify the torque against the authoritative specification and the configured range.",
  notes_date_mismatch:
    "Compare the dates in the notes with the record's date range.",
};

export default function App() {
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [severity, setSeverity] = useState<"all" | Validation["severity"]>(
    "all",
  );
  const [highlighted, setHighlighted] = useState<string | null>(null);

  const goTo = (id: string) => {
    const target = document.getElementById(id);
    if (!target) return;
    setHighlighted(id);
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.focus({ preventScroll: true });
    window.setTimeout(
      () => setHighlighted((current) => (current === id ? null : current)),
      3000,
    );
  };

  const visibleValidations = (
    result?.validations.filter(
      (validation) => severity === "all" || validation.severity === severity,
    ) ?? []
  ).sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  const matchingCodes = new Set(
    visibleValidations
      .map((validation) => validation.code)
      .filter((code) => code !== null),
  );
  const visibleAddresses =
    result?.addresses.filter(
      (address) => severity === "all" || matchingCodes.has(address.code),
    ) ?? [];

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Upload failed (${res.status})`);
      }
      setResult(await res.json());
      setSeverity("all");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="page-header">
        <p className="eyebrow">Data quality workspace</p>
        <h1>Torque Specification Validator</h1>
        <p className="muted">
          Upload an XML file to review validation findings and extracted
          records.
        </p>
      </header>

      <div className="upload-panel">
        <label htmlFor="file-upload">XML file</label>
        <input
          id="file-upload"
          type="file"
          accept=".xml"
          onChange={handleUpload}
          disabled={loading}
        />
      </div>
      {loading && <p role="status">Processing…</p>}
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {result && (
        <>
          <section className="document-panel" aria-label="Document details">
            <p className="eyebrow">Current document</p>
            <h2>{result.filename}</h2>
            <p
              id="document-metadata"
              tabIndex={-1}
              className={
                highlighted === "document-metadata" ? "highlighted" : undefined
              }
            >
              <span className="muted">Document date:</span>{" "}
              {result.document_date ?? "—"}
            </p>
          </section>

          <section className="summary-section" aria-label="Validation summary">
            <h3>Summary</h3>
            <div className="summary-grid">
              <div className="summary-card summary-error">
                <strong>
                  {
                    result.validations.filter((v) => v.severity === "error")
                      .length
                  }
                </strong>
                <span>
                  <span aria-hidden="true">● </span>Errors
                </span>
              </div>
              <div className="summary-card summary-warning">
                <strong>
                  {
                    result.validations.filter((v) => v.severity === "warning")
                      .length
                  }
                </strong>
                <span>
                  <span aria-hidden="true">▲ </span>Warnings
                </span>
              </div>
              <div className="summary-card summary-info">
                <strong>
                  {
                    result.validations.filter((v) => v.severity === "info")
                      .length
                  }
                </strong>
                <span>
                  <span aria-hidden="true">● </span>Info
                </span>
              </div>
              <div className="summary-card">
                <strong>{result.addresses.length}</strong>
                <span>Records</span>
              </div>
            </div>
          </section>

          <div className="filter-bar">
            <label htmlFor="severity-filter">Filter by severity: </label>
            <select
              id="severity-filter"
              value={severity}
              onChange={(event) =>
                setSeverity(
                  event.target.value as "all" | Validation["severity"],
                )
              }
            >
              <option value="all">All</option>
              <option value="error">Errors</option>
              <option value="warning">Warnings</option>
              <option value="info">Info</option>
            </select>
          </div>
          {severity !== "all" && (
            <p className="helper-text">
              Showing possible record matches by address code; codes may appear
              more than once.
            </p>
          )}

          {/* ── Validation Results ── */}
          <h3>
            Validation Results ({visibleValidations.length} of{" "}
            {result.validations.length})
          </h3>
          {visibleValidations.length === 0 ? (
            <p>
              {result.validations.length === 0
                ? "No issues found."
                : "No issues match this severity."}
            </p>
          ) : (
            <div
              className="table-wrap"
              role="region"
              aria-label="Validation results table"
              tabIndex={0}
            >
              <table className="data-table findings-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Address code</th>
                    <th>Message</th>
                    <th>Issue type</th>
                    <th>Location</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleValidations.map((v) => {
                    const validationIndex = result.validations.indexOf(v);
                    const matchingAddresses =
                      v.code === null
                        ? []
                        : visibleAddresses.filter(
                            (address) => address.code === v.code,
                          );
                    const id = `validation-${validationIndex}`;
                    return (
                      <tr
                        key={validationIndex}
                        id={id}
                        tabIndex={-1}
                        className={
                          highlighted === id ? "highlighted" : undefined
                        }
                      >
                        <td>
                          <span
                            className={`severity-badge severity-${v.severity}`}
                          >
                            <span aria-hidden="true">
                              {v.severity === "warning" ? "▲" : "●"}
                            </span>{" "}
                            {v.severity}
                          </span>
                        </td>
                        <td>{v.code ?? "—"}</td>
                        <td>
                          {v.message}
                          <p className="helper-text">
                            <strong>Review:</strong>{" "}
                            {ISSUE_GUIDANCE[v.validator] ??
                              "Review this finding against the source specification."}
                          </p>
                        </td>
                        <td>
                          <code>{v.validator}</code>
                        </td>
                        <td>
                          {v.code === null ? (
                            <button
                              type="button"
                              onClick={() => goTo("document-metadata")}
                            >
                              Go to document <span aria-hidden="true">↗</span>
                            </button>
                          ) : matchingAddresses.length ? (
                            matchingAddresses.map((address, index) => (
                              <button
                                key={result.addresses.indexOf(address)}
                                type="button"
                                onClick={() =>
                                  goTo(
                                    `address-${result.addresses.indexOf(address)}`,
                                  )
                                }
                              >
                                {matchingAddresses.length > 1
                                  ? `Possible match ${index + 1}: ${address.start_date || "No start date"} – ${address.end_date || "No end date"}`
                                  : "Go to record"}{" "}
                                <span aria-hidden="true">↓</span>
                              </button>
                            ))
                          ) : (
                            "No matching record"
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Data Table ── */}
          <h3>
            Extracted Data ({visibleAddresses.length} of{" "}
            {result.addresses.length} entries)
          </h3>
          {severity !== "all" && (
            <p className="helper-text">
              Records without a matching finding are hidden. Document-level
              findings have no matching record.
            </p>
          )}
          <div
            className="table-wrap"
            role="region"
            aria-label="Extracted data table"
            tabIndex={0}
          >
            <table className="data-table records-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Torque (Nm)</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Notes</th>
                  <th>Issues</th>
                </tr>
              </thead>
              <tbody>
                {visibleAddresses.map((a) => {
                  const addressIndex = result.addresses.indexOf(a);
                  const id = `address-${addressIndex}`;
                  const matches = visibleValidations.filter(
                    (validation) =>
                      validation.code !== null && validation.code === a.code,
                  );
                  const ambiguous =
                    result.addresses.filter(
                      (address) => address.code === a.code,
                    ).length > 1;
                  return (
                    <tr
                      key={addressIndex}
                      id={id}
                      tabIndex={-1}
                      className={highlighted === id ? "highlighted" : undefined}
                    >
                      <td>{a.code}</td>
                      <td>{a.torque ?? "—"}</td>
                      <td>{a.start_date ?? "—"}</td>
                      <td>{a.end_date ?? "—"}</td>
                      <td>{a.notes ?? ""}</td>
                      <td>
                        {matches.length === 0 ? (
                          "—"
                        ) : (
                          <>
                            {ambiguous && (
                              <span className="match-label">
                                Possible matches:{" "}
                              </span>
                            )}
                            {matches.map((validation) => (
                              <button
                                className={`issue-button severity-${validation.severity}`}
                                key={result.validations.indexOf(validation)}
                                type="button"
                                onClick={() =>
                                  goTo(
                                    `validation-${result.validations.indexOf(validation)}`,
                                  )
                                }
                              >
                                <span aria-hidden="true">
                                  {validation.severity === "warning"
                                    ? "▲"
                                    : "●"}
                                </span>{" "}
                                {validation.severity}{" "}
                                <span aria-hidden="true">↑</span>
                              </button>
                            ))}
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
