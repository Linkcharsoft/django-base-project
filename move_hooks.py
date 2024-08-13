import os
import shutil
import subprocess

print("Instalando hooks...")

# Ruta del directorio donde están los hooks en el repositorio
HOOKS_DIR = "hooks"

# Ruta del directorio de hooks de git
GIT_HOOKS_DIR = ".git/hooks"

# Copia los hooks
if os.path.exists(HOOKS_DIR):
    shutil.copytree(HOOKS_DIR, GIT_HOOKS_DIR, dirs_exist_ok=True)

# Cambia los permisos de los hooks
for root, dirs, files in os.walk(GIT_HOOKS_DIR):
    for filename in files:
        file_path = os.path.join(root, filename)
        os.chmod(file_path, 0o755)
