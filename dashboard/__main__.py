import uvicorn

from .settings import HOST, PORT

if __name__ == "__main__":
    print(f"Dashboard: http://{HOST}:{PORT}")
    uvicorn.run("dashboard.app:app", host=HOST, port=PORT, reload=False)
