import json
from typing import AsyncGenerator, Dict, Any, List, Callable
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder


class StreamEncoder:
    """Helper class to handle proper encoding of streaming text responses."""
    
    @staticmethod
    def encode_to_json(text: str) -> str:
        """Encode text to JSON string ensuring all Unicode characters are preserved."""
        return json.dumps({"text": text}, ensure_ascii=False)
    
    @staticmethod
    def format_sse(data: Dict[str, Any]) -> str:
        """Format data as Server-Sent Events message."""
        json_str = json.dumps(data, ensure_ascii=False)
        return f"data: {json_str}\n\n"
    
    @staticmethod
    def debug_text(text: str) -> None:
        """Print text in various debug formats to identify encoding issues."""
        print(f"[DEBUG] Original text ({len(text)} chars): {text[:50]}...")
        print(f"[DEBUG] Unicode escape: {text.encode('unicode_escape')[:100]}")
        print(f"[DEBUG] UTF-8 bytes: {text.encode('utf-8')[:20].hex()}")


class StreamingHelper:
    """Helper class for streaming responses with proper encoding."""
    
    @staticmethod
    async def generate_sse_stream(text_generator: AsyncGenerator) -> AsyncGenerator[str, None]:
        """
        Convert a text generator into SSE format.
        
        Args:
            text_generator: An async generator that yields text chunks
            
        Yields:
            SSE formatted string chunks
        """
        try:
            async for text_chunk in text_generator:
                if text_chunk:
                    # Debug the text chunk
                    StreamEncoder.debug_text(text_chunk)
                    
                    # Format as SSE with JSON payload
                    yield f"data: {StreamEncoder.encode_to_json(text_chunk)}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            print(f"[STREAM] Error in stream generator: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    @staticmethod
    def create_streaming_response(generator: AsyncGenerator) -> StreamingResponse:
        """Create a FastAPI StreamingResponse with the proper configuration."""
        return StreamingResponse(
            StreamingHelper.generate_sse_stream(generator),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Encoding": "identity",
                "X-Content-Type-Options": "nosniff",
            }
        )


# Example usage:
# 
# async def some_text_generator():
#     for i in range(5):
#         yield f"Part {i} with Unicode: áéíóú"
#         await asyncio.sleep(0.5)
# 
# @app.get("/stream")
# async def stream_endpoint():
#     return StreamingHelper.create_streaming_response(some_text_generator())
