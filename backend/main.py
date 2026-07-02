from fastapi import FastAPI

app = FastAPI(title='prismlen.ai')

@app.get("/health")
def read_root():
    return {"message": "OK", "code": 0}