import os
import uvicorn
from src.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.routes:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8001)),
        reload=settings.is_development
    )
