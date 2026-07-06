Set-Location $PSScriptRoot
Write-Host "Installing RapidOCR CPU dependencies..."
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""
$env:http_proxy = ""
$env:https_proxy = ""
$env:all_proxy = ""
$env:NO_PROXY = "*"
$env:no_proxy = "*"
python -m pip install --no-cache-dir rapidocr_onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tsinghua mirror failed, retrying official PyPI..."
    python -m pip install --no-cache-dir rapidocr_onnxruntime -i https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "RapidOCR install failed. Please check network/proxy and run this script again."
    Read-Host "Press Enter to exit"
    exit 1
}
python -c "from rapidocr_onnxruntime import RapidOCR; print('RapidOCR OK')"
Write-Host "Done. Reopen WeChatAutoReply.exe and click OCR test."
Read-Host "Press Enter to exit"