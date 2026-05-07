import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

def read_csv_robustly(file_content: bytes, **kwargs) -> pd.DataFrame:
    """
    Attempts to read a CSV from bytes using multiple encodings.
    Default encodings tried: utf-8, utf-8-sig, latin-1.
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    
    for encoding in encodings:
        try:
            # We use io.BytesIO to avoid reading from disk
            df = pd.read_csv(
                io.BytesIO(file_content),
                encoding=encoding,
                **kwargs
            )
            logger.info(f"Successfully read CSV using encoding: {encoding}")
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # If it's not a decode error, it might be a format error (e.g. empty file)
            # which might not be fixed by changing encoding
            logger.debug(f"Failed to read CSV with {encoding}: {e}")
            
    # If all fail, try one last time with default behavior to raise the final exception
    return pd.read_csv(io.BytesIO(file_content), **kwargs)
