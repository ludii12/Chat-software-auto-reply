@echo off
setlocal
cd /d "%~dp0"

set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
set NO_PROXY=*

echo ===== 安装依赖 =====
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo ===== 清理旧构建 =====
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo ===== 开始打包 =====
pyinstaller WeChatAutoReply.spec --noconfirm

if exist "dist\WeChatAutoReply.exe" (
    echo.
    echo ===== 打包成功 =====
    echo 输出文件：%~dp0dist\WeChatAutoReply.exe
) else (
    echo.
    echo ===== 打包失败，请检查上方日志 =====
)

pause
