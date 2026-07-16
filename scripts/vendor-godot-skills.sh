#!/usr/bin/env bash
# Vendor third-party Godot AI skills into resources/skills/godot-developer/vendor/
# Sources (MIT):
#   - https://github.com/fetasty/godot-skills (godot + godot-csharp)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/resources/skills/godot-developer/vendor"
TMP="${TMPDIR:-/tmp}/gf-godot-skills-vendor"

rm -rf "$TMP"
git clone --depth 1 https://github.com/fetasty/godot-skills.git "$TMP/godot-skills"

mkdir -p "$VENDOR/fetasty-godot-skills"
for skill in godot godot-csharp; do
  rm -rf "$VENDOR/fetasty-godot-skills/$skill"
  cp -R "$TMP/godot-skills/$skill" "$VENDOR/fetasty-godot-skills/$skill"
done
cp "$TMP/godot-skills/LICENSE" "$VENDOR/fetasty-godot-skills/LICENSE"
cp "$TMP/godot-skills/README.md" "$VENDOR/fetasty-godot-skills/README.md"

cat > "$VENDOR/fetasty-godot-skills/VENDOR.md" <<EOF
# fetasty/godot-skills (vendored)

- Upstream: https://github.com/fetasty/godot-skills
- License: MIT (see LICENSE)
- Updated: $(date -u +%Y-%m-%d)
- Skills copied: \`godot\`, \`godot-csharp\`

Refresh: \`bash scripts/vendor-godot-skills.sh\` from repo root.
EOF

rm -rf "$TMP"
echo "Vendored into $VENDOR/fetasty-godot-skills"
