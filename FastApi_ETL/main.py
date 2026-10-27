import json
import uvicorn
from typing import List, AsyncGenerator
from fastapi import FastAPI , HTTPException
from fastapi.responses import StreamingResponse


# Initiating FAST api

app= FastAPI (title:"Pandas-Powered Streaming ETL", description="Architecture for streamlining millions of data")


etl_engine = PandaListETLEnigne(chunk_size=50000)

async def stream_formatter(data_generator: AsyncGenerator[dict, None]) -> AsyncGenerator[str, None]:
    """
    Formats individual dictionaries flowing from the ETL engine into a valid 
    HTTP chunk-encoded JSON array wrapper.
    """
    yield "["
    first = True
    async for record in data_generator:
        if not first:
            yield ","
        else:
            first = False
        yield json.dumps(record)
    yield "]"

@app.get("/etl/process-csv")
async def run_panda_etl(file_name:str ="massive_dataset.csv"):
    try:
        transformed_stream=etl_engine.extract_and_transform(file_name)

        # Format it to JSON
        http_response_stream= stream_formatter(transformed_stream)
        return StreamingResponse(
            http_response_stream, 
            media_type="application/json",
            headers={"X-Accel-Buffering": "no"} # Prevents reverse proxies like Nginx from blocking the stream
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL pipeline failure: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
