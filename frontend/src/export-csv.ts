import type { UploadResponse } from "./types";

const HEADERS = ["severity", "address code", "message", "issue type"];

function cell(value: string): string {
  // Spreadsheet programs may ignore whitespace or control characters before a formula.
  const unsafe =
    /^[\s\u0000-\u001f\u007f-\u009f]*[=+\-@]/u.test(value) ||
    /^[\u0000-\u001f\u007f-\u009f]/u.test(value);
  const safe = unsafe ? `'${value}` : value;
  return `"${safe.replace(/"/g, '""')}"`;
}

export function serializeCsv(result: UploadResponse): string {
  const rows = result.validations.map((validation) => [
    validation.severity,
    validation.code ?? "",
    validation.message,
    validation.validator,
  ]);
  return (
    [HEADERS, ...rows].map((row) => row.map(cell).join(",")).join("\r\n") +
    "\r\n"
  );
}

export function downloadCsv(result: UploadResponse): void {
  const blob = new Blob(["\ufeff", serializeCsv(result)], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = "validation-findings.csv";
    link.click();
  } finally {
    // Allow the browser to start the download before releasing the URL.
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
