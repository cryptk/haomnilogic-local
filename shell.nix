{
  pkgs ? import <nixpkgs> { },
}:

let
  shellInit = pkgs.writeText "haomnilogic-shell-init" ''
    # Preserve the user's existing shell configuration
    if [ -f "$HOME/.bashrc" ]; then
      source "$HOME/.bashrc"
    fi

    mkdir -p dev_files

    echo "--- Updating Home Assistant Core ---"
    if [ ! -d "dev_files/home-assistant-core/.git" ]; then
      git clone --branch dev https://github.com/home-assistant/core.git dev_files/home-assistant-core
    else
      git -C dev_files/home-assistant-core pull origin dev
    fi

    if [ ! -d ".venv" ]; then
      echo "--- Initializing venv ---"
      uv venv --python python3.14
    fi


    echo "--- Activating Virtual Environment ---"
    source .venv/bin/activate

    if ! command -v hass &> /dev/null; then
      echo "--- Setting Up Home Assistant Core ---"
      ./dev_files/home-assistant-core/script/setup
    fi

    if [ ! -L "dev_files/home-assistant-core/config/custom_components/omnilogic_local" ]; then
      echo "--- Adding OmniLogic Local Custom Component ---"
      mkdir -p dev_files/home-assistant-core/config/custom_components
      ln -s ../../../../custom_components/omnilogic_local dev_files/home-assistant-core/config/custom_components/omnilogic_local
    fi

    echo "--- Syncing Project Dependencies ---"
    # --inexact leaves any dependencies installed by Home Assistant alone
    uv sync --all-extras --inexact

    if [ -d ../python-omnilogic-local ]; then
      echo "--- Installing Backend Library In Editable Mode---"
      uv pip install -e ../python-omnilogic-local
    fi

    alias run-core="hass -c dev_files/home-assistant-core/config" --skip-pip-packages python-omnilogic-local"
  '';
in
(pkgs.buildFHSEnv {
  name = "haomnilogic-fhs";
  targetPkgs =
    pkgs: with pkgs; [
      python314
      uv
      stdenv.cc.cc.lib
      zlib
      zlib.dev
      bashInteractive
      pkg-config
      libffi
      libffi.dev
      openssl
      openssl.dev
      ffmpeg
      gcc
      autoconf
      libjpeg_turbo
      libpcap
      jq
      yq-go
      zip
    ];

  runScript = "bash --rcfile ${shellInit}";
}).env
