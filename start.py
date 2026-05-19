import webbrowser
import uvicorn
from threading import Timer

def open_browser():
    """延迟打开浏览器访问看板"""
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # 启动一个定时器，1.5 秒后自动打开浏览器（等待服务器就绪）
    Timer(1.5, open_browser).start()
    
    # 启动 FastAPI 应用（与 main.py 中的启动方式一致）
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)