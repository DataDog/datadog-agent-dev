# Installation

-----

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

## pip

`dda` is available on PyPI and can be installed with [pip](https://github.com/pypa/pip).

```
pip install dda
```

!!! warning
    - This method modifies the Python environment in which you choose to install.
    - Python 3.12.x is required.
