#!/bin/bash
KLIPPER_PATH="${HOME}/klipper"

# Find the absolute path of the directory where this master script lives
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/ && pwd )"
DST_DIR="${KLIPPER_PATH}/klippy/plugins"

ACTION=""

# Display how to use the script
usage() {
    echo "Usage: $0 [-i] [-u] [-k <klipper_path>]"
    echo "  -i    Install all .py plugins found in subfolders"
    echo "  -u    Uninstall all .py plugins found in subfolders"
    echo "  -k    Specify custom Klipper path (default: ~/klipper)"
    exit 1
}

# Parse command line arguments
while getopts "iuk:" arg; do
    case $arg in
        i) ACTION="install" ;;
        u) ACTION="uninstall" ;;
        k) KLIPPER_PATH=$OPTARG ;;
        *) usage ;;
    esac
done

# Re-calculate destination directory in case -k changed the KLIPPER_PATH
DST_DIR="${KLIPPER_PATH}/klippy/plugins"

# Ensure the user specified an action
if [ -z "$ACTION" ]; then
    echo "Error: You must specify either -i (install) or -u (uninstall)."
    usage
fi

# Force script to exit if a critical command fails
set -e

echo "Searching for plugin files (.py) in subfolders..."
echo "------------------------------------------------"

# Track if we actually processed any files
FILES_FOUND=0

# Process substitution '< <(find...)' keeps variables inside the main shell context
while read -r src_file; do
    # Guard against empty find outputs
    [ -z "$src_file" ] && continue
    
    file_name=$(basename "$src_file")
    dst_file="${DST_DIR}/${file_name}"
    FILES_FOUND=$((FILES_FOUND + 1))

    if [ "$ACTION" = "install" ]; then
        echo "Linking ${file_name} to Klipper..."
        mkdir -p "$DST_DIR"
        ln -sf "$src_file" "$dst_file"
    elif [ "$ACTION" = "uninstall" ]; then
        if [[ -e "$dst_file" || -L "$dst_file" ]]; then
            echo "Removing ${file_name} from Klipper..."
            rm -f "$dst_file"
        else
            echo "${file_name} is not installed (skipping)."
        fi
    fi
done < <(find "$BASE_DIR" -mindepth 2 -maxdepth 2 -name "*.py" -type f)

echo "------------------------------------------------"
if [ "$FILES_FOUND" -eq 0 ]; then
    echo "No plugin files found."
else
    echo "Plugin operations complete. Total files processed: $FILES_FOUND"
fi

# Perform a single global restart at the end
echo "Restarting Klipper..."
sudo systemctl restart klipper

echo "All tasks completed successfully."