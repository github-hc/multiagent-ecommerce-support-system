from fastapi import FastAPI

app = FastAPI(title="Ecommerce Multiagent Support")

@app.get("/health")
def health_check():
    return {"status": "ok"}