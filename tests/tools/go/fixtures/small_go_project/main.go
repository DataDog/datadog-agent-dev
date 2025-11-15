package main

import (
	"fmt"
	"os"
	"runtime"
)

func main() {
	fmt.Printf("Hello from small go project!\n")
	fmt.Printf("Go version: %s\n", runtime.Version())
	fmt.Printf("OS/Arch: %s/%s\n", runtime.GOOS, runtime.GOARCH)

	// Test command line args
	if len(os.Args) > 1 {
		fmt.Printf("Arguments: %v\n", os.Args[1:])
	}

	// Call build-specific function to test build tags
	fmt.Printf("Tag: %s\n", TagInfo())
}
