@echo OFF
echo ===========================================
echo CORTEX DAILY PIPELINE BATCH JOB
echo Starting...
echo ===========================================
echo:

REM --- 1. Navegar al directorio del proyecto ---
cd C:\Users\gigab\Desktop\Cortex

echo Activando el entorno virtual...
REM --- 2. Activar el entorno virtual ---
call .\.venv\Scripts\activate.bat

echo:
echo ===========================================
echo PASO 1: Ejecutando Ingestor (src\ingestor.py)
echo ===========================================
call python src\ingestor.py

echo:
echo ===========================================
echo PASO 2: Ejecutando Pipeline (run_pipeline.py)
echo ===========================================
call python run_pipeline.py

echo:
echo ===========================================
echo CORTEX BATCH JOB COMPLETADO
echo ===========================================

REM --- 3. Desactivar el entorno ---
call .\.venv\Scripts\deactivate.bat

@echo ON