@echo off
title FORTSERV - Sistema Admissional (V23)
color 0A
cls
echo ============================================================
echo   Iniciando FORTSERV - Sistema Admissional (V23)
echo ============================================================
echo.
echo  - Enquadramento Perfeito das 11 Etapas em Tela Unica
echo  - Rodape Oficial: Criado e desenvolvido por: Luciano Veras 2026
echo  - Desenvolvido por: Luciano Veras | www.fortserv.com.br
echo.

setlocal enabledelayedexpansion

set "PYFILE="

for %%F in (
    "%~dp0sistema-admissao-fortserv-v23.py"
    "%~dp0sistema-admissao-fortserv-v23*.py"
    "%~dp0sistema-admissao-fortserv-v23*.py.txt"
    "%USERPROFILE%\Downloads\sistema-admissao-fortserv-v23.py"
    "%USERPROFILE%\Downloads\sistema-admissao-fortserv-v23*.py"
    "%USERPROFILE%\Downloads\sistema-admissao-fortserv-v23*.py.txt"
) do (
    if exist "%%~fF" (
        if not defined PYFILE set "PYFILE=%%~fF"
    )
)

if not defined PYFILE (
    echo ============================================================
    echo ATENCAO: O arquivo 'sistema-admissao-fortserv-v23.py' nao foi encontrado!
    echo.
    echo Certifique-se de baixar AMBOS os arquivos do painel Studio:
    echo  1. iniciar-sistema-fortserv-v23.bat
    echo  2. sistema-admissao-fortserv-v23.py
    echo.
    echo E salve-os juntos na mesma pasta (ex: Downloads).
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo Localizado arquivo Python em: "!PYFILE!"
echo.
echo Executando o servidor do sistema no seu navegador...
echo.

python -m streamlit run "!PYFILE!"
if %ERRORLEVEL% NEQ 0 (
    py -m streamlit run "!PYFILE!"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo ERRO AO EXECUTAR: Verifique se os pacotes estao instalados.
    echo.
    echo Para instalar os pacotes necessarios, abra o CMD e digite:
    echo pip install streamlit pandas openpyxl
    echo ============================================================
    echo.
)

pause
