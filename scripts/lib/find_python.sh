# Print the preferred Python executable name (python3.11, python3, or empty).
find_python() {
  if command -v python3.11 &>/dev/null; then
    echo python3.11
  elif command -v python3 &>/dev/null; then
    echo python3
  else
    echo ""
  fi
}
