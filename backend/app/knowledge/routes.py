from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List
from .models import DocumentResponse, DocumentListResponse, DocumentDeleteResponse
from .vectordb import process_and_store_document, delete_document, get_document_list, document_metadata

router = APIRouter()

@router.post("/knowledge/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document to the knowledge base."""
    print(f"\n[KNOWLEDGE API] Document upload requested: {file.filename}")
    print(f"[KNOWLEDGE API] Content type: {file.content_type}")
    
    try:
        # Read file content
        file_content = await file.read()
        print(f"[KNOWLEDGE API] Read file content, size: {len(file_content)} bytes")
        
        # Process and store document
        print(f"[KNOWLEDGE API] Processing and storing document...")
        document_id = process_and_store_document(
            file=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # Return document info
        doc_info = document_metadata[document_id]
        print(f"[KNOWLEDGE API] Document processed successfully, ID: {document_id}")
        return DocumentResponse(
            document_id=doc_info["document_id"],
            name=doc_info["name"],
            size=doc_info["size"],
            created_at=doc_info["created_at"],
            content_type=doc_info["content_type"]
        )
    except Exception as e:
        print(f"[KNOWLEDGE API] Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.delete("/knowledge/delete/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document_endpoint(document_id: str):
    """Delete a document from the knowledge base."""
    print(f"\n[KNOWLEDGE API] Document deletion requested: {document_id}")
    
    success = delete_document(document_id)
    if success:
        print(f"[KNOWLEDGE API] Document deleted successfully: {document_id}")
        return DocumentDeleteResponse(
            status="success",
            message=f"Document {document_id} deleted successfully"
        )
    else:
        print(f"[KNOWLEDGE API] Document not found: {document_id}")
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

@router.get("/knowledge/documents", response_model=DocumentListResponse)
async def get_documents():
    """Get list of documents in the knowledge base."""
    print(f"\n[KNOWLEDGE API] Document list requested")
    
    documents = get_document_list()
    print(f"[KNOWLEDGE API] Returning {len(documents)} documents")
    return DocumentListResponse(documents=documents)
