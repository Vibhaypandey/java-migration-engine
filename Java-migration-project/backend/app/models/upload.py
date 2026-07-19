from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    workspace_id: str             # use this as the ID for GET /assessment/{workspace_id}
    build_tool: str
    detected_java_version: int | None
    extracted_folder: str
    file_count: int


class DeleteResponse(BaseModel):
    message: str
    workspace_id: str
