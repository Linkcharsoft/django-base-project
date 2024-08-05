#!/bin/bash

echo "Instalando hooks..."

# Ruta del directorio donde están los hooks en el repositorio
HOOKS_DIR="hooks"

# Ruta del directorio de hooks de git
GIT_HOOKS_DIR=".git/hooks"

# Copia los hooks
cp -r $HOOKS_DIR/* $GIT_HOOKS_DIR/

# Cambia los permisos de los hooks
chmod +x $GIT_HOOKS_DIR/*