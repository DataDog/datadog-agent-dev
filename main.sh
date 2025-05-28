#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

to_lowercase() {
  if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
    echo "${1,,}"
  else
    echo "${1}" | tr '[:upper:]' '[:lower:]'
  fi
}

PURPLE="\033[1;35m"
RESET="\033[0m"
TARGET_PLATFORM=$(to_lowercase "${DDA_INSTALL_PLATFORM:-${RUNNER_OS}}")
TARGET_ARCH=$(to_lowercase "${DDA_INSTALL_ARCH:-${RUNNER_ARCH}}")
FEATURES="${DDA_INSTALL_FEATURES:-}"

if [[ "${TARGET_PLATFORM}" == "windows" ]]; then
  SEP="\\"
else
  SEP="/"
fi
INSTALL_PATH="${DDA_INSTALL_PATH:-${RUNNER_TOOL_CACHE}${SEP}.dda}"

install_features() {
  if [[ -n "${FEATURES}" ]]; then
    echo -e "${PURPLE}Installing features: ${FEATURES}${RESET}"

    # Temporarily change IFS to space just for this loop
    IFS=' ' read -ra features <<< "$FEATURES"
    ARGS=()
    for feature in $features; do
      ARGS+=("-f" "$feature")
    done

    "${1}" -v self dep sync ${ARGS[@]}
  fi
}

install_dda() {
  mkdir -p "${INSTALL_PATH}"
  archive="${INSTALL_PATH}${SEP}$1"

  echo -e "${PURPLE}Downloading dda ${DDA_INSTALL_VERSION}${RESET}\n"
  if [[ "${DDA_INSTALL_VERSION}" == "latest" ]]; then
    curl -sSLo "${archive}" "https://github.com/DataDog/datadog-agent-dev/releases/latest/download/$1"
  else
    curl -sSLo "${archive}" "https://github.com/DataDog/datadog-agent-dev/releases/download/v${DDA_INSTALL_VERSION}/$1"
  fi

  if [[ "${archive}" =~ \.zip$ ]]; then
    if [[ "${TARGET_PLATFORM}" == "windows" ]]; then
      7z -bso0 -bsp0 x "${archive}" -o"${INSTALL_PATH}"
    else
      unzip "${archive}" -d "${INSTALL_PATH}"
    fi
  else
    tar -xzf "${archive}" -C "${INSTALL_PATH}"
  fi
  rm "${archive}"

  echo -e "${PURPLE}Installing dda ${DDA_INSTALL_VERSION}${RESET}"
  dda_path="${INSTALL_PATH}${SEP}dda"
  "$dda_path" --version
  "$dda_path" self cache dist --remove
  install_features "$dda_path"

  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "${INSTALL_PATH}" >> "${GITHUB_PATH}"
  fi
}

fallback_install_dda() {
  echo -e "${PURPLE}Installing dda ${DDA_INSTALL_VERSION}${RESET}"
  if [[ "${DDA_INSTALL_VERSION}" == "latest" ]]; then
    pipx install --pip-args=--upgrade dda
  else
    pipx install "dda==${DDA_INSTALL_VERSION}"
  fi

  dda --version
  install_features dda
}

if [[ "${TARGET_PLATFORM}" == "linux" ]]; then
  if [[ "${TARGET_ARCH}" == "x64" ]]; then
    install_dda "dda-x86_64-unknown-linux-gnu.tar.gz"
  elif [[ "${TARGET_ARCH}" == "arm64" ]]; then
    install_dda "dda-aarch64-unknown-linux-gnu.tar.gz"
  else
    fallback_install_dda
  fi
elif [[ "${TARGET_PLATFORM}" == "windows" ]]; then
  if [[ "${TARGET_ARCH}" == "x64" ]]; then
    install_dda "dda-x86_64-pc-windows-msvc.zip"
  else
    fallback_install_dda
  fi
elif [[ "${TARGET_PLATFORM}" == "macos" ]]; then
  if [[ "${TARGET_ARCH}" == "arm64" ]]; then
    install_dda "dda-aarch64-apple-darwin.tar.gz"
  elif [[ "${TARGET_ARCH}" == "x64" ]]; then
    install_dda "dda-x86_64-apple-darwin.tar.gz"
  else
    fallback_install_dda
  fi
else
  fallback_install_dda
fi
