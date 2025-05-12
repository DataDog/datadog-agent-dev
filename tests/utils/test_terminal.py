# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.utils.terminal import remove_ansi

COMPLEX_ANSI_SEQUENCE = """\
\x1b[?25l\x1b[2J\x1b[m\x1b[H\x1b]0;C:\\Users\\foo\\bin\\bat.EXE\x07\x1b[?25h\x1b[38;5;238m───────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────\x1b[m
       \x1b[38;5;238m│ \x1b[mFile: \x1b[1mmain.go\x1b[38;5;238m\x1b[22m
───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   1   │ \x1b[38;5;176mpackage \x1b[38;5;149mmain\x1b[38;5;238m
   2   │
   3   │ \x1b[38;5;176mimport \x1b[38;5;253m(\x1b[38;5;238m
   4   │     \x1b[38;5;194m"\x1b[38;5;222mfmt\x1b[38;5;194m"\x1b[38;5;238m
   5   │     \x1b[38;5;194m"\x1b[38;5;222mgithub.com/shirou/gopsutil/v4/host\x1b[38;5;194m"\x1b[38;5;238m
   6   │ \x1b[38;5;253m)\x1b[38;5;238m
   7   │
   8   │ \x1b[38;5;111mfunc main\x1b[38;5;253m() {\x1b[38;5;238m
   9   │     \x1b[38;5;149mhostInfo\x1b[38;5;253m, \x1b[38;5;149merr \x1b[38;5;116m:= \x1b[38;5;149mhost\x1b[38;5;176m.\x1b[38;5;149mInfo\x1b[38;5;253m()\x1b[38;5;238m
  10   │     \x1b[38;5;116mif \x1b[38;5;149merr \x1b[38;5;116m!= \x1b[38;5;111mnil \x1b[38;5;253m{\x1b[38;5;238m
  11   │\x1b[9X\x1b[38;5;149m\x1b[9Cfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;149merr\x1b[38;5;253m)\x1b[38;5;238m
  12   │     \x1b[38;5;253m}\x1b[38;5;238m
  13   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;149mhostInfo\x1b[38;5;253m)\x1b[38;5;238m
  14   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mos\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mOS\x1b[38;5;253m)\x1b[38;5;238m
  15   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mplatform\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mPlatform\x1b[38;5;253m)\x1b[38;5;238m
  16   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mos_version\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mPlatformVersion\x1b[38;5;253m)\x1b[38;5;238m
  17   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mkernel_version\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mKernelVersion\x1b[38;5;253m)\x1b[38;5;238m
  18   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222marchitecture\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mKernelArch\x1b[38;5;253m)\x1b[38;5;238m
  19   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mhostname\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mHostname\x1b[38;5;253m)\x1b[38;5;238m
  20   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222muptime\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mUptime\x1b[38;5;253m)\x1b[38;5;238m
  21   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mboot_time\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mBootTime\x1b[38;5;253m)\x1b[38;5;238m
  22   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mprocs\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mProcs\x1b[38;5;253m)\x1b[38;5;238m
  23   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mplatform_family\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mPlatformFamily\x1b[38;5;253m)\x1b[38;5;238m
  24   │     \x1b[38;5;149mfmt\x1b[38;5;176m.\x1b[38;5;149mPrintln\x1b[38;5;253m(\x1b[38;5;194m"\x1b[38;5;222mplatform_version\x1b[38;5;194m"\x1b[38;5;253m, \x1b[38;5;149mhostInfo\x1b[38;5;176m.\x1b[38;5;149mPlatformVersion\x1b[38;5;253m)\x1b[38;5;238m
  25   │ \x1b[38;5;253m}\x1b[38;5;238m
───────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────\x1b[m\x1b[K
"""


def test_remove_ansi(helpers):
    assert remove_ansi(COMPLEX_ANSI_SEQUENCE) == helpers.dedent(
        """
        ───────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
               │ File: main.go
        ───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
           1   │ package main
           2   │
           3   │ import (
           4   │     "fmt"
           5   │     "github.com/shirou/gopsutil/v4/host"
           6   │ )
           7   │
           8   │ func main() {
           9   │     hostInfo, err := host.Info()
          10   │     if err != nil {
          11   │         fmt.Println(err)
          12   │     }
          13   │     fmt.Println(hostInfo)
          14   │     fmt.Println("os", hostInfo.OS)
          15   │     fmt.Println("platform", hostInfo.Platform)
          16   │     fmt.Println("os_version", hostInfo.PlatformVersion)
          17   │     fmt.Println("kernel_version", hostInfo.KernelVersion)
          18   │     fmt.Println("architecture", hostInfo.KernelArch)
          19   │     fmt.Println("hostname", hostInfo.Hostname)
          20   │     fmt.Println("uptime", hostInfo.Uptime)
          21   │     fmt.Println("boot_time", hostInfo.BootTime)
          22   │     fmt.Println("procs", hostInfo.Procs)
          23   │     fmt.Println("platform_family", hostInfo.PlatformFamily)
          24   │     fmt.Println("platform_version", hostInfo.PlatformVersion)
          25   │ }
        ───────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
        """
    )
