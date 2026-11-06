import { useEffect, useRef, useState } from "react";
import type { UploadResponse, UploadSummary } from "./types";

interface UploadHistoryProps {
  onSelect(result: UploadResponse): void;
  refreshKey: number;
  disabled: boolean;
}

export default function UploadHistory({
  onSelect,
  refreshKey,
  disabled,
}: UploadHistoryProps) {
  const [uploads, setUploads] = useState<UploadSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detailRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    if (disabled) {
      detailRequest.current?.abort();
      setSelectedId(null);
    }
  }, [disabled]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setListError(null);
    setDetailError(null);
    setSelectedId(null);

    async function loadHistory() {
      try {
        const response = await fetch("/api/uploads", {
          signal: controller.signal,
        });
        if (!response.ok)
          throw new Error(
            `Could not load upload history (${response.status}).`,
          );
        const data: UploadSummary[] = await response.json();
        if (!controller.signal.aborted) setUploads(data);
      } catch {
        if (!controller.signal.aborted)
          setListError("Could not load upload history. Please try again.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadHistory();
    return () => {
      controller.abort();
      detailRequest.current?.abort();
    };
  }, [refreshKey]);

  async function selectUpload(id: string) {
    detailRequest.current?.abort();
    const controller = new AbortController();
    detailRequest.current = controller;
    setSelectedId(id);
    setDetailError(null);

    try {
      const response = await fetch(`/api/uploads/${encodeURIComponent(id)}`, {
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(`Could not load upload (${response.status}).`);
      const result: UploadResponse = await response.json();
      if (!controller.signal.aborted) onSelect(result);
    } catch {
      if (!controller.signal.aborted)
        setDetailError("Could not open this upload. Please try again.");
    } finally {
      if (!controller.signal.aborted) setSelectedId(null);
    }
  }

  return (
    <section aria-label="Upload history">
      <h2>Upload history</h2>
      {loading && <p role="status">Loading upload history…</p>}
      {listError && <p role="alert">{listError}</p>}
      {!loading && !listError && uploads.length === 0 && <p>No uploads yet.</p>}
      {!loading && !listError && uploads.length > 0 && (
        <ul>
          {uploads.map((upload) => (
            <li key={upload.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => void selectUpload(upload.id)}
              >
                {upload.filename}
              </button>{" "}
              <time dateTime={upload.uploaded_at}>
                {new Date(upload.uploaded_at).toLocaleString()}
              </time>
              {" — "}
              {upload.counts.error} errors, {upload.counts.warning} warnings,{" "}
              {upload.counts.info} info
            </li>
          ))}
        </ul>
      )}
      {selectedId && <p role="status">Opening upload…</p>}
      {detailError && <p role="alert">{detailError}</p>}
    </section>
  );
}
