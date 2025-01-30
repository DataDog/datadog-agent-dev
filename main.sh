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
TARGET_PLATFORM=$(to_lowercase "${DEVA_INSTALL_PLATFORM:-${RUNNER_OS}}")
TARGET_ARCH=$(to_lowercase "${DEVA_INSTALL_ARCH:-${RUNNER_ARCH}}")
FEATURES="${DEVA_INSTALL_FEATURES:-}"

if [[ "${TARGET_PLATFORM}" == "windows" ]]; then
  SEP="\\"
else
  SEP="/"
fi
INSTALL_PATH="${DEVA_INSTALL_PATH:-${RUNNER_TOOL_CACHE}${SEP}.deva}"

install_features() {
  if [[ -n "${FEATURES}" ]]; then
    echo -e "${PURPLE}Installing features: ${FEATURES}${RESET}"

    ARGS=()
    for feature in $FEATURES; do
      ARGS+=("-f" "$feature")
    done

    "${1}" self dep sync "${ARGS[@]}"
  fi
}

install_deva() {
  mkdir -p "${INSTALL_PATH}"
  archive="${INSTALL_PATH}${SEP}$1"

  echo -e "${PURPLE}Downloading deva ${DEVA_INSTALL_VERSION}${RESET}\n"
  if [[ "${DEVA_INSTALL_VERSION}" == "latest" ]]; then
    curl -sSLo "${archive}" "https://github.com/DataDog/datadog-agent-dev/releases/latest/download/$1"
  else
    curl -sSLo "${archive}" "https://github.com/DataDog/datadog-agent-dev/releases/download/deva-v${DEVA_INSTALL_VERSION}/$1"
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

  echo -e "${PURPLE}Installing deva ${DEVA_INSTALL_VERSION}${RESET}"
  deva_path="${INSTALL_PATH}${SEP}deva"
  "$deva_path" --version
  "$deva_path" self cache dist --remove
  install_features "$deva_path"

  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "${INSTALL_PATH}" >> "${GITHUB_PATH}"
  fi
}

fallback_install_deva() {
  echo -e "${PURPLE}Installing deva ${DEVA_INSTALL_VERSION}${RESET}"
  if [[ "${DEVA_INSTALL_VERSION}" == "latest" ]]; then
    pipx install --pip-args=--upgrade datadog-agent-dev
  else
    pipx install "datadog-agent-dev==${DEVA_INSTALL_VERSION}"
  fi

  deva --version
  install_features deva
}

if [[ "${TARGET_PLATFORM}" == "linux" ]]; then
  if [[ "${TARGET_ARCH}" == "x64" ]]; then
    install_deva "deva-x86_64-unknown-linux-gnu.tar.gz"
  elif [[ "${TARGET_ARCH}" == "ARM64" ]]; then
    install_deva "deva-aarch64-unknown-linux-gnu.tar.gz"
  else
    fallback_install_deva
  fi
elif [[ "${TARGET_PLATFORM}" == "windows" ]]; then
  if [[ "${TARGET_ARCH}" == "x64" ]]; then
    install_deva "deva-x86_64-pc-windows-msvc.zip"
  else
    fallback_install_deva
  fi
elif [[ "${TARGET_PLATFORM}" == "macos" ]]; then
  if [[ "${TARGET_ARCH}" == "arm64" ]]; then
    install_deva "deva-aarch64-apple-darwin.tar.gz"
  elif [[ "${TARGET_ARCH}" == "x64" ]]; then
    install_deva "deva-x86_64-apple-darwin.tar.gz"
  else
    fallback_install_deva
  fi
else
  fallback_install_deva
fi
