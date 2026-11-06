import { downloadCsv } from "./export-csv";
import type { UploadResponse } from "./types";

export default function ExportCsv({ result }: { result: UploadResponse }) {
  return (
    <button type="button" onClick={() => downloadCsv(result)}>
      Export all findings (CSV)
    </button>
  );
}
