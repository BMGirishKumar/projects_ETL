import os
import pandas as pd
import asyncio
from typing import AsyncGenerator

class PandasListETLEngine:
    def __init__(self, chunk_size: int = 50000):
        self.chunk_size = chunk_size

    async def extract_and_transform(self, file_path: str) -> AsyncGenerator[dict, None]:
        """
        Extracts data in chunks using Pandas, applies vectorised transformations,
        and yields records one by one to keep a tiny memory footprint.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file {file_path} not found.")

        # EXTRACT: Read the file in chunks instead of loading all 1M rows into RAM
        # text=True and chunksize creates a TextFileReader iterator
        chunks = pd.read_csv(file_path, chunksize=self.chunk_size)

        for chunk_idx, df_chunk in enumerate(chunks):
            
            # TRANSFORM: Apply high-performance vectorised operations via Pandas
            # 1. Clean strings (strip whitespace, lowercase emails)
            df_chunk['email'] = df_chunk['user_email'].str.strip().str.lower()
            
            # 2. Vectorised boolean classification
            df_chunk['is_active'] = df_chunk['status'].str.strip() == 'active'
            
            # 3. Mathematical transformations
            df_chunk['computed_value'] = df_chunk['score'] * 2.5
            
            # 4. Filter columns out (drop raw columns we no longer need)
            df_chunk_cleaned = df_chunk[['id', 'email', 'is_active', 'computed_value']]

            # Convert the processed chunk dataframe to a list of dicts
            records = df_chunk_cleaned.to_dict(orient="records")

            # Yield transformed records one by one to the API stream
            for record in records:
                yield record

            # Crucial: Yield control back to the event loop between chunks 
            # to keep the API responsive to other traffic
            await asyncio.sleep(0.001)
