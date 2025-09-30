//go:build !debug
// +build !debug

package main

// Also defined in debug.go to test build tags
func TagInfo() string {
	return "PRODUCTION"
}
