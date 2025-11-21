from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Application",
    version="1.0.0",
    description="FastAPI 기본 애플리케이션",
)


@app.get("/")
def root() -> dict[str, str]:
    """루트 엔드포인트"""
    return {"message": "Welcome to FastAPI"}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """상태 확인 엔드포인트"""
    return {"status": "ok"}


# 직접 실행 가능하도록 설정
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
