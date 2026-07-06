@echo off
setlocal
cd /d "%~dp0"
echo Installing RapidOCR CPU dependencies...
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.8+ or add it to PATH.
  pause
  exit /b 1
)
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "ALL_PROXY="
set "http_proxy="
set "https_proxy="
set "all_proxy="
set "NO_PROXY=*"
set "no_proxy=*"
python -m pip install --no-cache-dir rapidocr_onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if errorlevel 1 (
  echo.
  echo Tsinghua mirror failed, retrying official PyPI...
  python -m pip install --no-cache-dir rapidocr_onnxruntime -i https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org
)
if errorlevel 1 (
  echo.
  echo RapidOCR install failed. Please check network/proxy and run this file again.
  pause
  exit /b 1
)
python -c "from rapidocr_onnxruntime import RapidOCR; print('RapidOCR OK')"
echo.
echo Done. Reopen WeChatAutoReply.exe and click OCR test.
pause
