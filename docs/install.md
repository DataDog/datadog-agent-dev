# Installation

-----

## Package managers

### Homebrew

Install the `dda` [cask](https://formulae.brew.sh/cask/dda) using [Homebrew](https://brew.sh).

```
brew install --cask dda
```

You can upgrade to the latest version by running the following command.

```
brew upgrade --cask dda
```

## Installers

/// tab | macOS
//// tab | GUI installer
1. In your browser, download the `.pkg` file: [dda-universal.pkg](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-universal.pkg)
2. Run your downloaded file and follow the on-screen instructions.
3. Restart your terminal.
4. To verify that the shell can find and run the `dda` command in your `PATH`, use the following command.
        ```
        $ dda --version
        <<<DDA_VERSION>>>
        ```
////

//// tab | Command line installer
1. Download the file using the `curl` command. The `-o` option specifies the file name that the downloaded package is written to. In this example, the file is written to `dda-universal.pkg` in the current directory.
        ```
        curl -Lo dda-universal.pkg https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-universal.pkg
        ```
2. Run the standard macOS [`installer`](https://ss64.com/osx/installer.html) program, specifying the downloaded `.pkg` file as the source. Use the `-pkg` parameter to specify the name of the package to install, and the `-target /` parameter for the drive in which to install the package. The files are installed to `/usr/local/dda`, and an entry is created at `/etc/paths.d/dda` that instructs shells to add the `/usr/local/dda` directory to. You must include sudo on the command to grant write permissions to those folders.
        ```
        sudo installer -pkg ./dda-universal.pkg -target /
        ```
3. Restart your terminal.
4. To verify that the shell can find and run the `dda` command in your `PATH`, use the following command.
        ```
        $ dda --version
        <<<DDA_VERSION>>>
        ```
////
///

/// tab | Windows
//// tab | GUI installer
1. In your browser, download one the `.msi` files:
      - [dda-x64.msi](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x64.msi)
2. Run your downloaded file and follow the on-screen instructions.
3. Restart your terminal.
4. To verify that the shell can find and run the `dda` command in your `PATH`, use the following command.
        ```
        $ dda --version
        <<<DDA_VERSION>>>
        ```
////

//// tab | Command line installer
1. Download and run the installer using the standard Windows [`msiexec`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec) program, specifying one of the `.msi` files as the source. Use the `/passive` and `/i` parameters to request an unattended, normal installation.

        ///// tab | x64
        ```
        msiexec /passive /i https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x64.msi
        ```
        /////

        ///// tab | x86
        ```
        msiexec /passive /i https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x86.msi
        ```
        /////
2. Restart your terminal.
3. To verify that the shell can find and run the `dda` command in your `PATH`, use the following command.
        ```
        $ dda --version
        <<<DDA_VERSION>>>
        ```
////
///

## Standalone binaries

After downloading the archive corresponding to your platform and architecture, extract the binary to a directory that is on your PATH and rename to `dda`.

/// tab | macOS
- [dda-aarch64-apple-darwin.tar.gz](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-aarch64-apple-darwin.tar.gz)
- [dda-x86_64-apple-darwin.tar.gz](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x86_64-apple-darwin.tar.gz)
///
/// tab | Windows
- [dda-x86_64-pc-windows-msvc.zip](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x86_64-pc-windows-msvc.zip)
- [dda-i686-pc-windows-msvc.zip](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-i686-pc-windows-msvc.zip)
///
/// tab | Linux
- [dda-aarch64-unknown-linux-gnu.tar.gz](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-aarch64-unknown-linux-gnu.tar.gz)
- [dda-x86_64-unknown-linux-gnu.tar.gz](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x86_64-unknown-linux-gnu.tar.gz)
- [dda-x86_64-unknown-linux-musl.tar.gz](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-x86_64-unknown-linux-musl.tar.gz)
- [dda-powerpc64le-unknown-linux-gnu.tar.gz](https://github.com/DataDog/datadog-agent-dev/releases/latest/download/dda-powerpc64le-unknown-linux-gnu.tar.gz)
///

## Upgrade

You can upgrade to the latest version by running the following command.

```
dda self update
```

If you installed `dda` using a [package manager](#package-managers), prefer its native upgrade mechanism.

/// warning
[Development](#development) and [manual](#manual) installations do not support this command and each have their own means of upgrading.
///

## Development

You can install `dda` directly from the source code, outside of release cycles. This is useful if you want to test the latest changes or contribute to the project.

1. Clone the `dda` repository and enter the directory.

      ```
      git clone https://github.com/DataDog/datadog-agent-dev.git
      cd datadog-agent-dev
      ```

2. [Install UV](https://docs.astral.sh/uv/getting-started/installation/).
3. Run the following command to install `dda` as a [tool](https://docs.astral.sh/uv/guides/tools/#installing-tools) in development mode:

      ```
      uv tool install -e .
      ```

4. *(optional)* If installation emitted a warning about a directory not being on your `PATH`, you can add it manually or run the following command to add it automatically.

      ```
      uv tool update-shell
      ```

This will ensure that `dda` always uses the version of the code checked out in the repository. However, this will not automatically reflect changes in dependencies. To synchronize those as well at any point after installation, run the following command.

```
uv tool upgrade dda
```

## Manual

/// warning
This method is not recommended.
///

`dda` is available on [PyPI](https://pypi.org/project/dda/) and can be installed with any Python package installer like [pip](https://github.com/pypa/pip) or [UV](https://github.com/astral-sh/uv).

The Python environment in which you choose to install must be at least version 3.12.
