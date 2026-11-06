from fastapi import FastAPI, UploadFile, HTTPException
from datetime import datetime, timezone
from uuid import uuid4
from .history import get_snapshot, list_snapshots, save_snapshot
from .parser import parse_torque_xml
from .validators.registry import run_all_validators

app = FastAPI(title="Torque Spec Validator")


@app.post("/api/upload")
async def upload_file(file: UploadFile):
    if not file.filename or not file.filename.endswith(".xml"):
        raise HTTPException(400, "Only XML files are accepted")

    content = await file.read()
    try:
        document = parse_torque_xml(content, file.filename)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse XML: {e}")

    validations = run_all_validators(document)

    snapshot = {
        "id": str(uuid4()),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "filename": file.filename,
        "document_date": document.document_date,
        "notes": document.notes,
        "manufacturer": document.manufacturer,
        "series": document.series,
        "main_group": document.main_group,
        "sub_group": document.sub_group,
        "addresses": [
            {
                "code": a.code,
                "torque": a.torque,
                "notes": a.notes,
                "start_date": a.start_date,
                "end_date": a.end_date,
            }
            for a in document.addresses
        ],
        "validations": [v.model_dump() for v in validations],
    }
    save_snapshot(snapshot)
    return snapshot


@app.get("/api/uploads")
def list_uploads():
    return list_snapshots()


@app.get("/api/uploads/{upload_id}")
def get_upload(upload_id: str):
    snapshot = get_snapshot(upload_id)
    if snapshot is None:
        raise HTTPException(404, "Upload not found")
    return snapshot
