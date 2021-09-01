set -eu

PROJ_PATH=$(cd $(dirname $0); pwd)
VENV_PATH=${PROJ_PATH}/.ve/
VENV_PYTHON=${VENV_PATH}bin/python
VENV_PIP=${VENV_PATH}bin/pip

if [[ -f ${VENV_PYTHON} ]]; then
    echo "Re-using existing virtualenv at: ${VENV_PATH} and assuming it's up to date."
    echo "If you see errors try 'rm -rf ${VENV_PATH}' and re-run this script."
else
    echo "Virtualenv at: ${VENV_PATH} not found, creating..."
    python3 -m venv ${VENV_PATH}
    ${VENV_PIP} install -r requirements.txt
fi

export PYTHONPATH=${PROJ_PATH}
