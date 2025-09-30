//go:build debug
// +build debug

package main

// Also defined in prod.go to test build tags
func TagInfo() string {
	return "DEBUG"
}
